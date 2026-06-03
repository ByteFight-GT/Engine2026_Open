

def main():
    import os    
    
    import argparse
    import sys
    import time
    import json
    from game_runner.gameplay import play_game
    from game.outcome import Result

    parser = argparse.ArgumentParser(description='Run a game between two players')
    
   
    parser.add_argument('--a_name', '-a', type=str, help='Name of player A submission', default= "sample_controller")
    parser.add_argument('--b_name', '-b', type=str, help='Name of player B submission', default= "sample_controller")

    parser.add_argument('--no_display', action='store_true', dest='display_game', help="Do not display the game (override default: False)")
    parser.add_argument('--delay', type=float, default=0.1, help="Delay between game actions (default: 0.1)")
    parser.add_argument('--map_name', type=str, default="test_map", help="Map name to play on from engine/config/maps.json (default:test_map)")
    parser.add_argument('--game_directory', type=str, default="workspace", help="Location where your agents are located (default: workspace)")
    parser.add_argument('--no_clear_screen', action='store_true', dest='clear_screen', help="Do not clear screen (override default: False)")
    parser.add_argument('--output_file', type=str, default="result.json", help="(overrid default:result.json)")


    args = parser.parse_args(sys.argv[1:])
    play_directory = os.path.join(os.path.dirname(__file__), args.game_directory) 

    _maps_path = os.path.join(os.path.dirname(__file__), 'config', 'maps.json')
    with open(_maps_path, 'r') as f:
        MAP_LIST = json.load(f)

    map_string = MAP_LIST[args.map_name]
    # map_string = "5,5#0,0#4,4#0000000110010100110000000#1,2#2,2_1,1,3,3#1#100,2,2"

    if(map_string is None):
        print("map not found")
        return
    
    print(play_directory)
    
    sim_time = time.perf_counter()
    outcome = play_game(play_directory, play_directory, 
                        args.a_name, args.b_name, 
                        display_game=not args.display_game, 
                        delay=args.delay, 
                        clear_screen=not args.clear_screen, map_string=map_string,
                        record=True, limit_resources=False)  
    
    if outcome.result == Result.PLAYER_1:
        print("Player A won by", outcome.reason.name)
    elif outcome.result == Result.PLAYER_2:
        print("Player B won by", outcome.reason.name)
    else:
        print("Tie by", outcome.reason.name)

    sim_time = time.perf_counter() - sim_time
    turn_count = outcome.get_num_turns()
    print(f"{sim_time:.3f} seconds elapsed to simulate {turn_count} rounds.")


    out_file = args.output_file
    out_dir = os.path.join(play_directory, "match_runs") 

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, out_file), 'w') as fp:
        fp.write(outcome.get_history_json())

if __name__=="__main__":
    main()
