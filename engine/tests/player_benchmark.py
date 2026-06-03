import timeit
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from game import Player as RegularPlayer, GameConstants as RegularGameConstants, Location
from game_accelerated import Player as NumbaPlayer, GameConstants as NumbaGameConstants

from numba import njit

BASE_MAX_STAMINA = RegularGameConstants.BASE_MAX_STAMINA
HILL_MAX_STAMINA_BONUS = RegularGameConstants.HILL_MAX_STAMINA_BONUS

def benchmark_regular_player():
    """Benchmark without Numba acceleration"""
    p1 = RegularPlayer(1, Location(3, 5), BASE_MAX_STAMINA)
    
    # Basic operations
    p1.gain_hill_control(1)
    p1.gain_hill_control(2)
    p1.lose_hill_control(1)
    p1.gain_hill_control(3)
    
    # Stamina operations
    p1.stamina += 10
    p1.clamp_stamina()
    
    # Copy operation
    p1_copy = p1.get_copy()
    p1_copy.loc = (9, 9)
    p1_copy.stamina += 5
    
    # Check if dead
    is_dead = p1.is_dead()
    
    return p1

@njit
def benchmark_numba_player():
    """Benchmark with Numba acceleration"""
    p1 = NumbaPlayer(1, (3, 5), BASE_MAX_STAMINA, 0)
    
    # Basic operations
    p1.gain_hill_control(1)
    p1.gain_hill_control(2)
    p1.lose_hill_control(1)
    p1.gain_hill_control(3)
    
    # Stamina operations
    p1.stamina += 10
    p1.clamp_stamina()
    
    # Copy operation
    p1_copy = p1.get_copy()
    p1_copy.loc = (9, 9)
    p1_copy.stamina += 5
    
    # Check if dead
    is_dead = p1.is_dead()
    
    return p1

# Warm-up phase
print("=" * 70)
print("WARM-UP PHASE: Compiling Numba functions...")
print("=" * 70)

warmup_runs = 10
warmup_time = timeit.timeit(
    benchmark_numba_player,
    globals=globals(),
    number=warmup_runs
)
print(f"Warm-up completed: {warmup_runs} runs in {warmup_time:.6f} seconds")
print(f"(This includes JIT compilation time)\n")

# Actual benchmark phase
print("=" * 70)
print("BENCHMARK PHASE: Measuring performance...")
print("=" * 70)

num_runs = 4000000  # Large number for accurate timing

print(f"\nRunning {num_runs:,} iterations of Player operations...\n")

# Benchmark regular version
regular_time = timeit.timeit(
    benchmark_regular_player,
    globals=globals(),
    number=num_runs
)

# Benchmark Numba version (already compiled)
numba_time = timeit.timeit(
    benchmark_numba_player,
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
print(f"Regular Player (no Numba)")
print(f"  Total time     : {regular_time:.6f} seconds")
print(f"  Per operation  : {regular_time/num_runs:.3e} seconds")
print(f"  Ops per second : {num_runs/regular_time:,.0f}\n")

print(f"Numba Player (accelerated)")
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

def breakdown_hill_control():
    p = RegularPlayer(1, Location(3, 5), BASE_MAX_STAMINA)
    for i in range(100):
        p.gain_hill_control(i)
        p.lose_hill_control(i)

@njit
def breakdown_hill_control_numba():
    p = NumbaPlayer(1, (3, 5), BASE_MAX_STAMINA, 0)
    for i in range(100):
        p.gain_hill_control(i)
        p.lose_hill_control(i)

breakdown_runs = 550000

hill_regular = timeit.timeit(breakdown_hill_control, globals=globals(), number=breakdown_runs)
hill_numba = timeit.timeit(breakdown_hill_control_numba, globals=globals(), number=breakdown_runs)

print(f"\nHill Control Operations, {breakdown_runs:,} runs):")
print(f"  Regular: {hill_regular:.6f} s → {hill_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {hill_numba:.6f} s → {hill_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {hill_regular/hill_numba:.2f}x")

def breakdown_copy():
    p = RegularPlayer(1, Location(3, 5), BASE_MAX_STAMINA)
    p.gain_hill_control(1)
    p.gain_hill_control(2)
    for _ in range(100):
        p_copy = p.get_copy()

@njit
def breakdown_copy_numba():
    p = NumbaPlayer(1, (3, 5), BASE_MAX_STAMINA, 0)
    p.gain_hill_control(1)
    p.gain_hill_control(2)
    for _ in range(100):
        p_copy = p.get_copy()

copy_regular = timeit.timeit(breakdown_copy, globals=globals(), number=breakdown_runs)
copy_numba = timeit.timeit(breakdown_copy_numba, globals=globals(), number=breakdown_runs)

print(f"\nCopy Operations ({breakdown_runs:,} runs):")
print(f"  Regular: {copy_regular:.6f} s → {copy_regular/breakdown_runs:.3e} s per run")
print(f"  Numba  : {copy_numba:.6f} s → {copy_numba/breakdown_runs:.3e} s per run")
print(f"  Speedup: {copy_regular/copy_numba:.2f}x")

print("\n" + "=" * 70)