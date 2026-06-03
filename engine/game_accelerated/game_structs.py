from numba import types, njit,int64
from typing import Tuple, List
import numpy as np
DIRECTION_DOWN= (1,0)
DIRECTION_UP= (-1,0)
DIRECTION_LEFT= (0,-1)
DIRECTION_RIGHT= (0,1)

CARDINALS = (
    DIRECTION_UP,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
)

MOVE_REGULAR = 0
MOVE_ERASE = 1
MOVE_BEACON_TRAVEL = 2

NONE_LOCATION = (-999, -999)
NONE_DIRECTION = (-999, -999)

location_type = types.UniTuple(types.int64, 2)
direction_type = types.UniTuple(types.int64, 2)
move_action_type = types.Tuple([types.int64, types.int64, types.int64, types.boolean, types.int64, types.int64])  
paint_action_type = types.UniTuple(types.int64, 2)

@njit
def location_square_region(loc: Tuple[int, int], radius: int) -> np.ndarray:
    size = (2 * radius + 1)**2
    cells = np.empty((size, 2), dtype=int64)
    idx=0
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            cells[idx,0] = loc[0] + dr
            cells[idx,1] = loc[1] + dc
            idx+=1
    return cells
@njit
def location_neighbors(loc:Tuple[int, int], allow_diagonals:bool=False) -> List[Tuple[int, int]]:
    return [(loc[0] +d[0], loc[1] + d[1]) for d in CARDINALS]

@njit    
def location_add(loc: Tuple[int, int], direction: Tuple[int, int]) -> Tuple[int, int]:
    return (loc[0] + direction[0], loc[1] + direction[1])
@njit
def location_sub(loc1: Tuple[int, int], loc2: Tuple[int, int]) -> Tuple[int, int]:
    return (loc1[0] - loc2[0], loc1[1] - loc2[1])

def location_equals(loc1: Tuple[int, int], loc2: Tuple[int, int]) -> bool:
    return loc1[0] == loc2[0] and loc1[1] == loc2[1]


def location_hash(loc: Tuple[int, int]) -> int:
    return hash((loc[0], loc[1]))

@njit
def manhattan_distance(loc1: Tuple[int, int], loc2: Tuple[int, int]) -> int:
    return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])


def create_move_action(direction: Tuple[int, int], move_type: int = MOVE_REGULAR, place_beacon: bool = False, beacon_target: Tuple[int, int] = None) -> Tuple[int, int, int, bool, int, int]:
    dir_r = direction[0] if direction is not None else -999
    dir_c = direction[1] if direction is not None else -999
    target_r = beacon_target[0] if beacon_target is not None else -999
    target_c = beacon_target[1] if beacon_target is not None else -999
    return (dir_r, dir_c, move_type, place_beacon, target_r, target_c)


def create_paint_action(location: Tuple[int, int]) -> Tuple[int, int]:
    return (location[0], location[1])


def get_move_direction(move_action: Tuple) -> Tuple[int, int]:
    dir_r, dir_c = move_action[0], move_action[1]
    if dir_r == -999:
        return None
    return (dir_r, dir_c)


def get_move_type(move_action: Tuple) -> int:
    return move_action[2]


def is_beacon_travel(move_action: Tuple) -> bool:
    return move_action[2] == MOVE_BEACON_TRAVEL


def should_place_beacon(move_action: Tuple) -> bool:
    return move_action[3]


def get_beacon_target(move_action: Tuple) -> Tuple[int, int]:
    target_r, target_c = move_action[4], move_action[5]
    if target_r == -999:
        return None
    return (target_r, target_c)


def is_valid_location(loc: Tuple[int, int]) -> bool:
    return loc[0] != -999 and loc[1] != -999

def is_valid_direction(direction: Tuple[int, int]) -> bool:
    return direction[0] != -999 and direction[1] != -999


def get_paint_location(paint_action: Tuple) -> Tuple[int, int]:
    return (paint_action[0], paint_action[1])

#
#Forget all of the class definitions below this point. I have decided to just use the functions above.
#I am just not deleting them yet in case I change my mind.
#
class Location:
    def __init__(self, r: int, c: int):
        self.r = r
        self.c = c

    def to_tuple(self) -> Tuple[int, int]:
        return (self.r, self.c)

    @staticmethod
    def from_tuple(loc_tuple: Tuple[int, int]) -> "Location":
        return Location(loc_tuple[0], loc_tuple[1])
    
    def __add__(self, other: Tuple[int, int]) -> "Location":
        if isinstance(other, Direction):
            return Location.from_tuple(location_add(self.to_tuple(), other.to_tuple()))
        elif isinstance(other, tuple):
            return Location.from_tuple(location_add(self.to_tuple(), other))
        return NotImplemented
    def __sub__(self, other):
        if isinstance(other, Location):
            return Location.from_tuple(location_sub(self.to_tuple(), other.to_tuple()))
        return NotImplemented
    def __eq__(self, other):
        if isinstance(other, Location):
            return location_equals(self.to_tuple(), other.to_tuple())
        return False
    def __hash__(self):
        return location_hash(self.to_tuple())
    def neighbors(self, allow_diagonals: bool = False): 
        return [Location.from_tuple(t) for t in location_neighbors(self.to_tuple(), allow_diagonals)]
    def square_region(self, radius: int):
        return [Location.from_tuple(t) for t in location_square_region(self.to_tuple(), radius)]
    

class Direction:
    UP= DIRECTION_UP
    DOWN= DIRECTION_DOWN
    LEFT= DIRECTION_LEFT
    RIGHT= DIRECTION_RIGHT

    def __init__(self, direction_tuple: Tuple[int, int]):
        self.value = direction_tuple
    def to_tuple(self) -> Tuple[int, int]:
        return self.value
    @staticmethod
    def cardinals():
        return tuple(Direction(d) for d in CARDINALS)
class Action:
    class Move:
        def __init__(self,direction, move_type=MOVE_REGULAR, place_beacon=False, beacon_target=None):
            if hasattr(direction, "to_tuple"):
                self.direction = direction.to_tuple()
            elif isinstance(direction, tuple):
                self.direction = direction
            elif direction is None:
                self.direction = NONE_DIRECTION
            else:
                self.direction = direction
            self.move_type = move_type
            self.place_beacon = place_beacon
            
            if beacon_target is None:
                self.beacon_target = NONE_LOCATION
            elif isinstance(beacon_target, Location):
                self.beacon_target = beacon_target.to_tuple()
            elif isinstance(beacon_target, tuple):
                self.beacon_target = beacon_target
            else:
                self.beacon_target = NONE_LOCATION
        @staticmethod
        def to_tuple(self):
            return create_move_action(self.direction, self.move_type, self.place_beacon, self.beacon_target)
            
    class Paint:
        def __init__(self, location):
            self.location = location.to_tuple() if isinstance(location, Location) else location
        @staticmethod
        def to_tuple(self):
            return create_paint_action(self.location)

class MoveType:
    REGULAR = MOVE_REGULAR
    ERASE = MOVE_ERASE
    BEACON_TRAVEL = MOVE_BEACON_TRAVEL    

