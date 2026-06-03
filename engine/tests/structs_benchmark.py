import timeit
import numpy as np
from typing import Tuple
from numba import njit
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ===============================
# ORIGINAL (FROM game_structs.py - using classes)
# ===============================
from game.game_structs import Location, Direction

def location_add_py(loc: Tuple[int, int], direction: Tuple[int, int]) -> Tuple[int, int]:
    """Using game_structs.Location.__add__"""
    loc_obj = Location(loc[0], loc[1])
    dir_obj = Direction(direction)  # Create Direction enum from tuple
    result = loc_obj + dir_obj
    return (result.r, result.c)

def location_sub_py(loc1: Tuple[int, int], loc2: Tuple[int, int]) -> Tuple[int, int]:
    """Using game_structs.Location.__sub__"""
    loc1_obj = Location(loc1[0], loc1[1])
    loc2_obj = Location(loc2[0], loc2[1])
    result = loc1_obj - loc2_obj
    return (result.r, result.c)

def manhattan_distance_py(loc1: Tuple[int, int], loc2: Tuple[int, int]) -> int:
    """Pure Python implementation (not in game_structs classes)"""
    return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

def location_square_region_py(loc: Tuple[int, int], radius: int):
    """Using game_structs.Location.square_region"""
    loc_obj = Location(loc[0], loc[1])
    result = loc_obj.square_region(radius)
    return [(l.r, l.c) for l in result]

# ===============================
# NUMBA VERSIONS
# ===============================
from game_accelerated.game_structs import (
    location_add as location_add_numba,
    location_sub as location_sub_numba,
    manhattan_distance as manhattan_distance_numba,
    location_square_region as location_square_region_numba
)

# ===============================
# BENCHMARK WRAPPERS
# ===============================
def bench_location_add_py():
    #for _ in range(100):
    location_add_py((10, 20), (1, -1))

@njit
def bench_location_add_numba():
    #for _ in range(100):
    location_add_numba((10, 20), (1, -1))

def bench_location_sub_py():
    #for _ in range(100):
    location_sub_py((10, 20), (3, 5))

@njit
def bench_location_sub_numba():
    #for _ in range(100):
    location_sub_numba((10, 20), (3, 5))

def bench_manhattan_py():
    #for _ in range(100):
    manhattan_distance_py((10, 20), (3, 5))

@njit
def bench_manhattan_numba():
    #for _ in range(100):
    manhattan_distance_numba((10, 20), (3, 5))

def bench_square_region_py():
    #for _ in range(10):
    location_square_region_py((10, 20), 3)

@njit
def bench_square_region_numba():
    #for _ in range(10):
    location_square_region_numba((10, 20), 3)

# ===============================
# RUNNER
# ===============================
def run_test(name, py_func, numba_func, runs=10_700_000):
    py_time = timeit.timeit(py_func, number=runs)
    nb_time = timeit.timeit(numba_func, number=runs)
    print(f"\n{name}")
    print(f"Runs: {runs:,}")
    print(f"Python : {py_time:.6f}s → {py_time / runs:.3e}s per run")
    print(f"Numba  : {nb_time:.6f}s → {nb_time / runs:.3e}s per run")
    print(f"Speedup: {py_time / nb_time:.1f}×")

def warm_up():
    print("\n=== WARM-UP PHASE: Compiling Numba functions... ===")
    bench_location_add_numba()
    bench_location_sub_numba()
    bench_manhattan_numba()
    bench_square_region_numba()
    print("=== WARM-UP COMPLETE ===\n")

if __name__ == "__main__":
    print("\n=== STRUCT FUNCTION BENCHMARKS ===")
    
    warm_up()

    run_test(
        "location_add",
        bench_location_add_py,
        bench_location_add_numba,
    )
    
    run_test(
        "location_sub",
        bench_location_sub_py,
        bench_location_sub_numba,
    )
    
    run_test(
        "manhattan_distance",
        bench_manhattan_py,
        bench_manhattan_numba,
    )
    
    run_test(
        "location_square_region",
        bench_square_region_py,
        bench_square_region_numba,
        runs=10_700_000,  # heavier work
    )