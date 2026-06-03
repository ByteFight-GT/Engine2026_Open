from game import *
import json
import os

# Load maps from config/maps.json
_maps_path = os.path.join(os.path.dirname(__file__), 'config', 'maps.json')
with open(_maps_path, 'r') as f:
    MAP_LIST = json.load(f)

def create_initial_board():
    powerup_schedule = [ScheduledPowerup(100, Location(2, 2))]

    wall_list = [
        Location(1, 4),
        Location(1, 3),
        Location(2, 3),
        Location(3, 2),
        Location(3, 1),
        Location(2, 1),
    ]

    h1 = Hill(1, [Location(1, 2)])
    h2 = Hill(2, [Location(2, 2), Location(3, 3)])

    hill_list = [h1, h2]

    b3 = Board(
        board_size=Location(15, 15), 
        p1_start=Location(0, 0), p2_start=Location(4, 4),
        powerup_schedule=powerup_schedule,
        hill_list=hill_list,
        wall_list=wall_list
    )

    return b3

def main():
    import os
    import time
    
    from game_runner.gameplay import play_game
    from game.outcome import Result

    a_name = "player_a"
    b_name = "player_a"


    out_dir = os.path.join(os.getcwd(), "game_env", "match.json")
    a_sub = os.path.join(os.getcwd(), "game_env", "game_subs", "temp")
    b_sub = os.path.join(os.getcwd(), "game_env", "game_subs", "temp")

    if not "controller.py" in os.listdir(os.path.join(a_sub, a_name)):
        print("Error: Bot 1 directory incorrect.")
        return

    if not "controller.py" in os.listdir(os.path.join(b_sub, b_name)):
        print("Error: Bot 2 directory incorrect.")
        return

    map_string = MAP_LIST["shuriken"]

    if(map_string is None):
        print("map not found")
        return

    sim_time = time.perf_counter()
    outcome = play_game(a_sub, b_sub, a_name, b_name, 
                        display_game=True, clear_screen=True, record=True, delay = 0.0,
                        limit_resources=False, map_string=map_string, output_stream=None)

    if outcome.result == Result.PLAYER_1:
        print("Player A won by", outcome.reason.name)
    elif outcome.result == Result.PLAYER_2:
        print("Player B won by", outcome.reason.name)
    else:
        print("Tie by", outcome.reason.name)

    sim_time = time.perf_counter() - sim_time
    turn_count = outcome.get_num_turns()
    print(f"{sim_time:.3f} seconds elapsed to simulate {turn_count} rounds.")

    try:
        with open(out_dir, 'w') as fp:
            fp.write(outcome.get_history_json())
    except:
        print("Failed to write game to output directory.")
        

if __name__=="__main__":
    main()
