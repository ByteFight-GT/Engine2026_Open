import logging
import random
import zipfile
import os
import shutil
import sys
import threading
import requests
from pathlib import Path


"""
Server file used to validate submissions and simulate online matches. 
Receives matches to play via RabbitMQ. This is the script that is run in our
server deployment via docker.
"""

def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description='Starts the bytefight server')

    parser.add_argument('--unlimit_resources', '-u',
        action='store_true',
        help='Runs in unconstrained mode')
    
    parser.add_argument('--use_gpu', '-g',
        action='store_true',
        help='Runs with gpu constraints')
    
    parser.add_argument('--testing', '-t',
        action='store_false',
        help='Runs with gpu constraints')
    
    load_dotenv()
    
    args = parser.parse_args(sys.argv[1:])

    # logging.basicConfig(filename='app.log', 
    #                 level=logging.DEBUG, 
    #                 format='%(asctime)s - %(levelname)s - %(message)s')

    logging.basicConfig(
        stream=sys.stdout, 
        level=logging.DEBUG, 
        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting server...")


    game_callback = generateCallback(
        os.getenv('AUTH_TOKEN'), 
        os.getenv("WEBSERVER_URL"),
        '/api/v1/submission/download/',
        os.getenv('UPDATE_QUEUE'),
        os.getenv('RESULT_QUEUE'),
        temp_dir = "temp" if args.testing else None,
        limit_resources=not args.unlimit_resources,
        use_gpu=args.use_gpu,
    )

    start_rmq_listener(game_callback) 
 
def start_rmq_listener(game_callback):
    import pika
    import signal
    params = pika.URLParameters(os.getenv('PIKA_URL'))
    MATCH_ROUTING_KEYS = os.getenv('MATCH_ROUTING_KEY').split(",")
    EXCHANGE_NAME = os.getenv('EXCHANGE_NAME')
    RESULT_QUEUE = os.getenv('RESULT_QUEUE')
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    # Enable publisher confirms on result channel so we know publishes succeeded
    channel.confirm_delivery()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )


    # handle connection shutdowns
    def request_shutdown(sig, frame):
        channel.stop_consuming()
        print("Shutdown requested, waiting for game to finish...")

    def shutdown(sig, frame):
        print("Server did not terminate within time limits, escalated to sigterm...")
        connection.close()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    channel.queue_declare(queue="gameMatchQueue", durable =True, arguments={'x-max-priority': 10})
    for match_key in MATCH_ROUTING_KEYS:
        channel.queue_bind(
            queue="gameMatchQueue",
            exchange=EXCHANGE_NAME,
            routing_key=match_key,
        )

    channel.basic_qos(prefetch_count=1)
    
    channel.basic_consume(queue="gameMatchQueue",
                     auto_ack=False,
                     on_message_callback=game_callback
                     )

    channel.queue_declare(queue=RESULT_QUEUE, durable =True)
    channel.start_consuming()
    print("Consuming stopped, closing connection...")
    connection.close()

    sys.exit(0)

    
    
"""
SERVER UTILS
Downloads and file finding
"""



def upload_game_match_file(
    base_url: str,
    *,
    game_match_uuid: str,
    slug: str,
    visibility: str,
    file_path: str,
    team_uuid: str | None = None,
    token: str | None = None,
):
    """Upload a game match file to the API.
    
    Args:
        base_url: The API base URL.
        game_match_uuid: The game match UUID.
        slug: The file slug identifier.
        visibility: The file visibility ("public", "private", "team", "everyone").
        file_path: Path to the file to upload.
        team_uuid: Optional team UUID for team-visible files.
        token: Optional API token for authentication.
        
    Returns:
        The API response JSON.
    """
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = {
        "gameMatchUuid": game_match_uuid,
        "slug": slug,
        "visibility": visibility,
    }
    if team_uuid:
        data["teamUuid"] = team_uuid

    logging.info(data)

    file_path_obj = Path(file_path)
    try:
        with open(file_path_obj, "rb") as f:
            files = {"file": (file_path_obj.name, f)}
            response = requests.post(
                f"{base_url}/api/v1/game-match-file",
                headers=headers,
                data=data,
                files=files,
                timeout=60,
            )

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"--- SERVER ERROR DETAILS ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}") # <--- This will show the Spring Boot error JSON
        print(f"----------------------------")
        raise e

    
    return response.json()

def exists_or_make(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def copy_files(src, dest):
    # Ensure the destination folder exists
    exists_or_make(dest)

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dest, item)
        
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
        
    
    
    return None

def delete_directory_contents(directory):
    if(os.path.isdir(directory)):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

def set_permissions(val):
    logging.debug(f"Setting permissions for game env to {val}")
    for dirpath, dirnames, filenames in os.walk(os.path.join(os.getcwd(), "game_env")):
        os.chmod(dirpath, val)
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            os.chmod(file_path, val)

"""
SERVER CALLBACKS
Validation and game playing
"""
def generateCallback(auth_token, server_url, download_endpoint, UPDATE_QUEUE, RESULT_QUEUE, temp_dir = None,
                     download_folder = "downloads", game_folder = "gameplay", limit_resources=True, use_gpu = False):
    import json
    import time

    # TRY CATCH NEEDS TO GO BACK IN BEFORE PROD
    import os
    from game_runner.gameplay import play_game, validate_submission
    from game_runner.game_controller import GameController

    from game.outcome import Result
    import logging
    import traceback
    import requests

    from multiprocessing import set_start_method
    #set_start_method('spawn')

    game_sub_dir = os.path.join(os.getcwd(),"game_env", "game_subs")

    dl_directory = os.path.join(game_sub_dir, download_folder)
    exists_or_make(dl_directory)
    game_directory = os.path.join(game_sub_dir, game_folder)
    exists_or_make(game_directory)

    testing = not temp_dir is None
    play_directory = game_directory if testing else os.path.join(game_sub_dir, temp_dir)

    def download_submission(uuid, local_name): 
        zip_dir = os.path.join(dl_directory, local_name+".zip")

        headers = {"Authorization": f"Bearer {auth_token}"}
        logging.debug(f"Download {uuid} submission to {local_name}")
        url = server_url + download_endpoint + f"{uuid}"
        print("DEBUG: url = ", url)
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logging.debug(f"Failed to get download link: {response.status_code} - {response.text}")
            return False

        download_link = (response.json())["uri"]
        logging.debug(f"Download {download_link}")
        response = requests.get(download_link, headers=headers)

        if response.status_code == 200:
            # Write the binary content to a .zip file
            with open(zip_dir, "wb") as f:
                f.write(response.content)
            logging.debug(f"File saved as {zip_dir}")
        else:
            logging.debug(f"Failed to download: {response.status_code}")
            return False

        player_dl_extracted =  os.path.join(dl_directory, local_name)
        logging.debug("extracting")
        with zipfile.ZipFile(zip_dir, 'r') as zip_ref:
            zip_ref.extractall(player_dl_extracted)
        
        agent_path = find("controller.py", player_dl_extracted)

        if(agent_path is None):
            logging.debug("Finding controller failed")
            return False

        control_folder = os.path.dirname(agent_path)
        logging.debug(f"Control folder found as {control_folder}")            
        
        player_directory = os.path.join(game_directory, local_name)
        copy_files(control_folder, player_directory)
        return True
    
    def publish_result_with_confirm(ch, result_dict, timeout=5):
        """Publish result message with publisher confirms. 
        Returns True if confirmed, False if failed/timeout."""
        try:
            logging.debug(f"Publishing result with confirms: {result_dict['uuid']}")
            ch.basic_publish(
                exchange='',
                routing_key=RESULT_QUEUE,
                body=json.dumps(result_dict)
            )
            logging.debug("Result publish confirmed")
            return True
        except Exception as e:
            logging.error(f"Failed to publish result: {e}")
            logging.error(traceback.format_exc())
            return False
    
    def callback(ch, method, properties, body):
        match_dict = json.loads(body)        
        logging.info(f"Processing game {match_dict}")
        match_reason = match_dict["ladder"]
        matchID = match_dict["uuid"]

        logging.debug(f"Deleting from {dl_directory}")
        delete_directory_contents(dl_directory)

        logging.debug(f"Deleting from {game_directory}")
        delete_directory_contents(game_directory)
        
        def get_map_string(map_name):
            logging.debug(f"Getting map_string for {map_name}")
            

            map_json_dir = os.path.join(os.getcwd(), "engine","config", "maps.json")
            map_string = ""
            with open(map_json_dir) as json_file:
                map_dict = json.load(json_file)
                if map_name == "random":
                    random_key = random.choice(list(map_dict.keys()))
                    map_string = map_dict[random_key]
                else:
                    map_string = map_dict[map_name]
            return map_string
        

        winner = "FAILED"
        publish_success = False
        
        if (match_reason == "validation"):
            logging.info(f"Running Validation")
            try:
                player_a_uuid = match_dict["submissionAUuid"]
                ok = download_submission(player_a_uuid, "player_a")
                delete_directory_contents(dl_directory)
                err=""
                
                if(ok or testing):   
                    logging.debug("Match ready, playing.")
                    
                    # TODO implement testing map string
                    #map_name = match_dict.get("mapName")
                    map_name = "test_map"
                    map_string = get_map_string(map_name)

                    ok, err= validate_submission(
                        play_directory, 
                        "player_a", 
                        limit_resources=limit_resources, 
                        use_gpu=use_gpu,
                        board_to_play=None,
                        map_string=map_string
                        ) 
                    logging.debug("Match complete.")

                if(ok):
                    winner = "submission_valid"
                else:
                    winner = "submission_invalid"
                logging.info(f"{ok}, {winner}, {err}")
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.error("validation error")
                err = str(e)[:200]
                logging.info(f"Validation failed with error: {err}")

            results = {"uuid":matchID,"status":winner}
            logging.debug("Publishing results.")
            publish_success = publish_result_with_confirm(ch, results)

            logging.info(f"Validation Complete")


        else:
            logging.info(f"Running Game")

            player_a_uuid = match_dict["submissionAUuid"]
            player_b_uuid = match_dict["submissionBUuid"]

            ok = download_submission(player_a_uuid, "player_a")
            ok = ok and download_submission(player_b_uuid, "player_b")
            delete_directory_contents(dl_directory)

            try:
                if(not (ok or testing)):
                    raise Exception("Submission not downloaded")

                # TODO implement testing map string
                #map_name = match_dict.get("mapName")
                if not "matchSettings" in match_dict.keys() or "map" not in match_dict["matchSettings"].keys() or not match_dict["matchSettings"]["map"]:
                    map_string = get_map_string("random")
                else:
                    map_name = match_dict["matchSettings"]["map"]
                    map_string = get_map_string(map_name)
                if map_string == "":
                    raise Exception("map not found")


                sim_time = time.perf_counter()
                logging.debug("Match ready, playing.")
                
                ch.basic_publish(exchange='',
                    routing_key=UPDATE_QUEUE,
                    body=json.dumps({
                        "uuid": matchID,
                        "started": True
                    })
                )

                # TODO implement map string and test game history
                outcome = play_game(
                    play_directory,
                    play_directory,
                    "player_a",
                    "player_b",
                    display_game=False,
                    clear_screen=False,
                    record=True,
                    output_stream=None,
                    limit_resources=limit_resources,
                    use_gpu=use_gpu,
                    board_to_play= None,
                    map_string=map_string,
                    annotate = True
                )
                logging.debug("Match complete.") 


                if outcome.result == Result.PLAYER_1:
                    winner = "team_a_win"
                elif outcome.result == Result.PLAYER_2:
                    winner = "team_b_win"
                else:
                    winner = "draw"
                logging.info(f"Winner: {winner}")

                sim_time = time.perf_counter() - sim_time
                turn_count = outcome.get_num_turns()
                logging.info(f"{sim_time} seconds elapsed for {turn_count} rounds.")

                out_dir = os.path.join(os.getcwd(), "game_env", "match.json")
                try:
                    with open(out_dir, 'w') as fp:
                        fp.write(outcome.get_history_json())

                    upload_game_match_file(
                        server_url,
                        game_match_uuid=matchID,
                        slug="game_log",
                        visibility="everyone",
                        file_path=out_dir,
                        token=auth_token,
                    )
                except:
                    logging.error(traceback.format_exc())
                    logging.error("Failed to write game to output directory.")

                results = {
                    "uuid": matchID,
                    "status": winner,
                }

                logging.debug("Publishing results.")
                publish_success = publish_result_with_confirm(ch, results)
                
            except Exception as e:
               logging.error(traceback.format_exc())
               logging.error("match error")
               logging.debug(f"Match error details: {str(e)[:200]}")
               results = {
                   "uuid": matchID,
                   "status": winner
               }
               logging.debug("Publishing error result.")
               publish_success = publish_result_with_confirm(ch, results)

            logging.info(f"Game Complete")
        
        # Only ack the input message if result was successfully published
        if publish_success:
            logging.debug(f"Result published successfully, acking input message")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logging.error(f"Result publish failed, nacking input message to retry")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
    return callback

if __name__=="__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    
    main()
