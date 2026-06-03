import time

from game import *

# TRY CATCH NEEDS TO GO BACK IN BEFORE PROD
def main():
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    
    # dl_func = get_test_download()

    # dl_func("2d10ea3a-1f4f-416a-b69e-7e03f481c439", "player_a")
    # test_game_no_limit()
    # test_map_strings()
    test_socket_connection()

def test_socket_connection():
    import socket
    import json
    

    buffer = ""
    start_time = time.time()
    timeout = 10
    while True:
        print("trying")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", 8765))
            print("Connected!")
            break
        except ConnectionRefusedError:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Server not ready after {timeout} seconds")
            time.sleep(0.5)  # wait 100ms before retrying

    while True:
        data = sock.recv(4096)
        if not data:
            print("Connection closed by server")
            break

        buffer += data.decode("utf-8")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            try:
                msg = json.loads(line)
                print(msg)
            except json.JSONDecodeError:
                print(f"(raw), {line}")
    



def test_map_strings():
    from game_runner.gen_board import convert_map_string, map_string_from_board, get_board_from_map_string
    from game_runner.board_viz import print_board

    wall_list = [
        Location(1, 2),
        Location(1, 3),
        Location(2, 3),
        Location(3, 2),
        Location(3, 1),
        Location(2, 1),
    ]

    powerup_schedule = [ScheduledPowerup(100, Location(2, 2))]

    h1 = Hill(1, [Location(2, 2)])
    h2 = Hill(2, [Location(1, 1), Location(3, 3)])

    hill_list = [h1, h2]

    b3 = Board(
        board_size=Location(5, 5), 
        p1_start=Location(0, 0), p2_start=Location(4, 4),
        powerup_schedule=powerup_schedule,
        hill_list= hill_list,
        wall_list=wall_list
    )

    map_string = map_string_from_board(b3)
    print(map_string)

    board_copy = get_board_from_map_string(map_string)
    print(board_copy.board_size)
    print(board_copy.p1.loc)
    print(board_copy.p2.loc)
    print(board_copy.powerup_schedule)
    
    print_board(b3, 0, 0)
    print_board(board_copy, 0, 0)

def test_securitization():
    import os
    from game_runner.gameplay import play_game
    from game_runner.board_viz import get_history_json

    sim_time = time.perf_counter()

    game_sub_dir = os.path.join(os.getcwd(),"game_env", "game_subs")
    play_directory =  os.path.join(game_sub_dir, "temp")

    outcome = play_game(play_directory, play_directory, 
                        "player_a", "player_b", 
                        display_game=True, delay=0, clear_screen=False, 
                        record=True, limit_resources=True, use_gpu=False)
    
    sim_time = time.perf_counter() - sim_time
    turn_count = outcome.turn_count
    print(f"{sim_time} seconds elapsed for {turn_count} rounds.")

    out_file = 'result.json'
    out_dir = os.path.join(os.getcwd(), "game_env", "match_runs") 

    with open(os.path.join(out_dir, out_file), 'w') as fp:
        fp.write(get_history_json(outcome))
    

    
def test_game_no_limit():
    import os
    from game_runner.gameplay import play_game
    from game_runner.board_viz import get_history_json

    sim_time = time.perf_counter()

    game_sub_dir = os.path.join(os.getcwd(),"game_env", "game_subs")
    play_directory =  os.path.join(game_sub_dir, "temp")

    outcome = play_game(play_directory, play_directory, 
                        "player_a", "player_a", 
                        display_game=True, delay=0.1, clear_screen=True, 
                        record=True, limit_resources=False)  
    

    sim_time = time.perf_counter() - sim_time
    turn_count = outcome.turn_count
    print(f"{sim_time} seconds elapsed for {turn_count} rounds.")

    out_file = 'result.json'
    out_dir = os.path.join(os.getcwd(), "game_env", "match_runs") 

    with open(os.path.join(out_dir, out_file), 'w') as fp:
        fp.write(get_history_json(outcome))
    
def get_test_download():
    import os
    # import pika
    # import pika.exceptions
    import logging
    import traceback
    import requests
    import sys
    import zipfile
    from server import copy_files, find, exists_or_make

    from dotenv import load_dotenv
    
    load_dotenv()

    logging.basicConfig(
        stream=sys.stdout, 
        level=logging.DEBUG, 
        format='%(asctime)s - %(levelname)s - %(message)s')
    
    auth_token = os.getenv('AUTH_TOKEN') 
    server_url = os.getenv("WEBSERVER_URL")
    download_endpoint = '/api/v1/submission/download/'


    download_folder = "downloads"
    game_folder = "gameplay"

    dl_directory = os.path.join(os.getcwd(),"game_env", "game_subs", download_folder)
    exists_or_make(dl_directory)
    game_directory = os.path.join(os.getcwd(), "game_env", "game_subs", game_folder)
    exists_or_make(game_directory)

    def download_submission(uuid, local_name): 
        zip_dir = os.path.join(dl_directory, local_name+".zip")

        headers = {"Authorization": f"Bearer {auth_token}"}
        logging.debug(f"Download {uuid} submission to {local_name}")
        url = server_url + download_endpoint + f"{uuid}"
        response = requests.get(url, headers=headers)
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

    
    return download_submission

    

if __name__=="__main__":
    main()
