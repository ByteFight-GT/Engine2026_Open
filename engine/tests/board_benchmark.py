import faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(3600, repeat=True)


import timeit
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from game import Board as RegularBoard, Location, ScheduledPowerup, Hill, Action, MoveType
from game import Direction
from game import GameConstants as RegularGameConstants

# Import Numba board directly
from game_accelerated.board import Board as NumbaBoard, Hill as NumbaHill
from game_accelerated.game_constants import GameConstants as NumbaGameConstants

from numba import njit, types, int64
from numba.typed import List as TypedList

BASE_MAX_STAMINA = RegularGameConstants.BASE_MAX_STAMINA

def benchmark_regular_board():
    """Benchmark without Numba acceleration"""
    # Create board with walls and hills
    wall_list = [
        Location(1, 2),
        Location(1, 3),
        Location(2, 3),
        Location(3, 2),
        Location(3, 1),
        Location(2, 1),
    ]
    
    h1 = Hill(1, [Location(2, 2)])
    h2 = Hill(2, [Location(1, 1), Location(3, 3)])
    hill_list = [h1, h2]
    
    powerup_schedule = [ScheduledPowerup(100, Location(2, 2))]
    
    board = RegularBoard(
        board_size=Location(15, 15),
        p1_start=Location(0, 0),
        p2_start=Location(14, 14),
        powerup_schedule=powerup_schedule,
        hill_list=hill_list,
        wall_list=wall_list
    )
    
    # Apply bid
    board.apply_bid(10, 5)
    
    # Execute some moves
    move1 = Action.Move(direction=Direction.UP)
    board.apply_action(1, move1)
    
    move2 = Action.Move(direction=Direction.LEFT)
    board.apply_action(1, move2)
    
    # Execute paint action
    paint1 = Action.Paint(location=Location(2, 1))
    board.apply_action(1, paint1)
    
    # End turn
    board.end_turn()
    
    # Get copy
    board_copy = board.get_copy()
    
    # Territory count
    territory = board.get_territory_count(1)
    
    # Check winner
    winner = board.get_winner()
    
    return board

@njit
def benchmark_numba_board():
    """Benchmark with Numba acceleration"""
    # Create board with walls and hills
    wall_list = np.array([
        [1, 2],
        [1, 3],
        [2, 3],
        [3, 2],
        [3, 1],
        [2, 1],
    ], dtype=np.int64)
    
    # Hills as list of tuples (id, cells, control_positive, control_negative, controller_parity)
    h1_cells = np.array([[2, 2]], dtype=np.int64)
    h2_cells = np.array([[1, 1], [3, 3]], dtype=np.int64)
    
    hill_list = TypedList()
    hill_list.append((np.int64(1), h1_cells, np.int64(0), np.int64(0), np.int64(0)))
    hill_list.append((np.int64(2), h2_cells, np.int64(0), np.int64(0), np.int64(0)))
    
    powerup_schedule = np.array([[100, 2, 2]], dtype=np.int64)
    
    # Use positional arguments only (no keywords) for Numba jitclass
    board = NumbaBoard(
        (15, 15),      # board_size
        (0, 0),        # p1_start
        (14, 14),      # p2_start
        powerup_schedule,
        wall_list,
        hill_list,
        0              # copy_mode
    )
    
    # Apply bid
    board.apply_bid(10, 5)
    
    # Execute some moves (direction_r, direction_c, move_type, place_beacon, beacon_target_r, beacon_target_c)
    move1 = (1, 0, 0, False, -999, -999)  # MOVE_REGULAR = 0
    board.apply_action(1, move1, 0)
    
    move2 = (0, 1, 0, False, -999, -999)
    board.apply_action(1, move2, 1)
    
    # Execute paint action (target_r, target_c)
    paint1 = (2, 1)
    board.apply_action(1, paint1, 0)
    
    # End turn
    board.end_turn()
    
    # Get copy
    board_copy = board.get_copy()
    
    # Territory count
    territory = board.get_territory_count(1)
    
    # Check winner
    winner = board.get_winner()
    
    return board


@njit
def benchmark_numba_hill():
    """Test function to verify Hill jitclass compiles properly"""
    
    # Create a simple hill with one cell
    h1_cells = np.array([[2, 2]], dtype=np.int64)
    hill1 = NumbaHill(
        np.int64(1),      # id
        h1_cells,          # cells
        np.int64(0),       # control_positive
        np.int64(0),       # control_negative
        np.int64(0)        # controller_parity
    )
    
    # Test basic operations
    control_diff = hill1.get_control_diff(1)
    is_above = hill1.above_threshold(1, 5)
    fraction = hill1.control_fraction(1)
    
    # Test increment/decrement
    hill1.increment_control(1)
    hill1.decrement_control(1)
    
    # Create a hill with multiple cells
    h2_cells = np.array([[1, 1], [3, 3], [5, 5]], dtype=np.int64)
    hill2 = NumbaHill(
        np.int64(2),      # id
        h2_cells,          # cells
        np.int64(5),       # control_positive
        np.int64(-3),      # control_negative
        np.int64(1)        # controller_parity
    )
    
    # Test get_copy
    hill2_copy = hill2.get_copy()
    
    # Increment control on copy
    hill2_copy.increment_control(-1)
    
    # Test with hill list (like in Board)
    hill_list = TypedList()
    hill_list.append((np.int64(1), h1_cells, np.int64(0), np.int64(0), np.int64(0)))
    hill_list.append((np.int64(2), h2_cells, np.int64(5), np.int64(-3), np.int64(1)))
    
    # Create Hill objects from tuples
    for i in range(len(hill_list)):
        hill_tuple = hill_list[i]
        hill_obj = NumbaHill(
            hill_tuple[0],  # id
            hill_tuple[1],  # cells
            hill_tuple[2],  # control_positive
            hill_tuple[3],  # control_negative
            hill_tuple[4]   # controller_parity
        )
        
        # Test operations
        _ = hill_obj.get_control_diff(1)
        _ = hill_obj.above_threshold(1, 3)
    
    return hill1.id




print("Testing Hill compilation...")
try:
    result = benchmark_numba_hill()
    print(f"✓ Hill compiled successfully! Result: {result}")
except Exception as e:
    print(f"✗ Hill compilation failed!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()


print("Calling benchmark_numba_board() directly...")
benchmark_numba_board()
print("Returned from benchmark_numba_board")




# Warm-up phase
print("=" * 70)
print("WARM-UP PHASE: Compiling Numba functions...")
print("=" * 70)

warmup_runs = 1
warmup_time = timeit.timeit(
    benchmark_numba_board,
    globals=globals(),
    number=warmup_runs
)
print(f"Warm-up completed: {warmup_runs} runs in {warmup_time:.6f} seconds")
print(f"(This includes JIT compilation time)\n")

# Actual benchmark phase
print("=" * 70)
print("BENCHMARK PHASE: Measuring performance...")
print("=" * 70)

num_runs = 500000  # Reasonable number for Board operations (they're heavier than Player ops)

print(f"\nRunning {num_runs:,} iterations of Board operations...\n")

# Benchmark regular version
regular_time = timeit.timeit(
    benchmark_regular_board,
    globals=globals(),
    number=num_runs
)

# Benchmark Numba version (already compiled)
numba_time = timeit.timeit(
    benchmark_numba_board,
    globals=globals(),
    number=num_runs
)

# Calculate speedup
speedup = regular_time / numba_time

# Display results
print("=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Total runs: {num_runs:,}\n")
print(f"Regular Board (no Numba)")
print(f"  Total time     : {regular_time:.6f} seconds")
print(f"  Per operation  : {regular_time/num_runs:.3e} seconds")
print(f"  Ops per second : {num_runs/regular_time:,.0f}\n")

print(f"Numba Board (accelerated)")
print(f"  Total time     : {numba_time:.6f} seconds")
print(f"  Per operation  : {numba_time/num_runs:.3e} seconds")
print(f"  Ops per second : {num_runs/numba_time:,.0f}\n")

print("=" * 70)
print(f"SPEEDUP: {speedup:.2f}x faster with Numba")
print("=" * 70)

# Additional detailed breakdown
print("\n" + "=" * 70)
print("DETAILED BREAKDOWN")
print("=" * 70)

def breakdown_board_creation():
    wall_list = [Location(1, 2), Location(1, 3)]
    h1 = Hill(1, [Location(2, 2)])
    
    for _ in range(10):
        board = RegularBoard(
            board_size=Location(10, 10),
            p1_start=Location(0, 0),
            p2_start=Location(9, 9),
            hill_list=[h1],
            wall_list=wall_list
        )

@njit
def breakdown_board_creation_numba():
    wall_list = np.array([[1, 2], [1, 3]], dtype=np.int64)
    h1_cells = np.array([[2, 2]], dtype=np.int64)
    hill_list = TypedList()
    hill_list.append((np.int64(1), h1_cells, np.int64(0), np.int64(0), np.int64(0)))
    powerup_schedule = np.empty((0, 3), dtype=np.int64)
    
    for _ in range(10):
        board = NumbaBoard(
            (10, 10),     # board_size
            (0, 0),       # p1_start
            (9, 9),       # p2_start
            powerup_schedule,
            wall_list,
            hill_list,
            0             # copy_mode
        )

breakdown_runs = 100000

creation_regular = timeit.timeit(breakdown_board_creation, globals=globals(), number=breakdown_runs)
creation_numba = timeit.timeit(breakdown_board_creation_numba, globals=globals(), number=breakdown_runs)

print(f"\nBoard Creation ({breakdown_runs:,} runs):")
print(f"  Regular: {creation_regular:.6f} s → {creation_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {creation_numba:.6f} s → {creation_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {creation_regular/creation_numba:.2f}x")

def breakdown_copy():
    board = RegularBoard(
        board_size=Location(10, 10),
        p1_start=Location(0, 0),
        p2_start=Location(9, 9)
    )
    for _ in range(50):
        board_copy = board.get_copy()

HILL_TUPLE_TYPE=types.Tuple((int64, int64[:,:], int64, int64, int64))
@njit
def breakdown_copy_numba():
    powerup_schedule = np.empty((0, 3), dtype=np.int64)
    wall_list = np.empty((0, 2), dtype=np.int64)
    # Create empty typed list for hills
    hill_list = TypedList.empty_list(HILL_TUPLE_TYPE)
    
    board = NumbaBoard(
        (10, 10),     # board_size
        (0, 0),       # p1_start
        (9, 9),       # p2_start
        powerup_schedule,
        wall_list,
        hill_list,
        0             # copy_mode
    )
    for _ in range(50):
        board_copy = board.get_copy()

# Need to compile breakdown_copy_numba before running timing
_ = breakdown_copy_numba()

copy_regular = timeit.timeit(breakdown_copy, globals=globals(), number=breakdown_runs)
copy_numba = timeit.timeit(breakdown_copy_numba, globals=globals(), number=breakdown_runs)

print(f"\nBoard Copy Operations ({breakdown_runs:,} runs):")
print(f"  Regular: {copy_regular:.6f} s → {copy_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {copy_numba:.6f} s → {copy_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {copy_regular/copy_numba:.2f}x")

def breakdown_move_operations():
    board = RegularBoard(
        board_size=Location(10, 10),
        p1_start=Location(5, 5),
        p2_start=Location(9, 9)
    )
    board.apply_bid(10, 0)
    
    for i in range(20):
        move = Action.Move(direction=Direction.RIGHT if i % 2 == 0 else Direction.DOWN)
        board.apply_action(1, move, i)

@njit
def breakdown_move_operations_numba():
    powerup_schedule = np.empty((0, 3), dtype=np.int64)
    wall_list = np.empty((0, 2), dtype=np.int64)
    hill_list = TypedList.empty_list(HILL_TUPLE_TYPE)
    
    board = NumbaBoard(
        (10, 10),     # board_size
        (5, 5),       # p1_start
        (9, 9),       # p2_start
        powerup_schedule,
        wall_list,
        hill_list,
        0             # copy_mode
    )
    board.apply_bid(10, 0)
    
    for i in range(20):
        if i % 2 == 0:
            move = (0, 1, 0, False, -999, -999)
        else:
            move = (1, 0, 0, False, -999, -999)
        board.apply_action(1, move, i)

move_regular = timeit.timeit(breakdown_move_operations, globals=globals(), number=breakdown_runs)
move_numba = timeit.timeit(breakdown_move_operations_numba, globals=globals(), number=breakdown_runs)

print(f"\nMove Operations ({breakdown_runs:,} runs):")
print(f"  Regular: {move_regular:.6f} s → {move_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {move_numba:.6f} s → {move_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {move_regular/move_numba:.2f}x")

def breakdown_territory_count():
    board = RegularBoard(
        board_size=Location(20, 20),
        p1_start=Location(0, 0),
        p2_start=Location(19, 19)
    )
    # Paint some cells
    board.apply_bid(50, 0)
    for i in range(10):
        paint = Action.Paint(location=Location(i, i))
        board.apply_action(1, paint)
    
    for _ in range(100):
        count = board.get_territory_count(1)

@njit
def breakdown_territory_count_numba():
    powerup_schedule = np.empty((0, 3), dtype=np.int64)
    wall_list = np.empty((0, 2), dtype=np.int64)
    hill_list = TypedList.empty_list(HILL_TUPLE_TYPE)
    
    board = NumbaBoard(
        (20, 20),     # board_size
        (0, 0),       # p1_start
        (19, 19),     # p2_start
        powerup_schedule,
        wall_list,
        hill_list,
        0             # copy_mode
    )
    # Paint some cells
    board.apply_bid(50, 0)
    for i in range(10):
        paint = (i, i)
        board.apply_action(1, paint, 0)
    
    for _ in range(100):
        count = board.get_territory_count(1)

territory_regular = timeit.timeit(breakdown_territory_count, globals=globals(), number=breakdown_runs)
territory_numba = timeit.timeit(breakdown_territory_count_numba, globals=globals(), number=breakdown_runs)

print(f"\nTerritory Count ({breakdown_runs:,} runs):")
print(f"  Regular: {territory_regular:.6f} s → {territory_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {territory_numba:.6f} s → {territory_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {territory_regular/territory_numba:.2f}x")

print("\n" + "=" * 70)