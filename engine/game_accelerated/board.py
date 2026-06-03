from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from game_accelerated.player import Player

from game_accelerated.game_constants import GameConstants
#from game.player import Player 

from numba import int64, types, njit, boolean
from numba.experimental import jitclass
from numba.typed import Dict, List as TypedList
import numpy as np

from game_accelerated.game_structs import (
    location_add, location_square_region, manhattan_distance,
    MOVE_REGULAR, MOVE_ERASE, MOVE_BEACON_TRAVEL,
    move_action_type, paint_action_type
)

HILL_TUPLE_TYPE = types.Tuple((
    int64,
    int64[:, :],
    int64,
    int64,
    int64,
))


BASE_MAX_STAMINA = GameConstants.BASE_MAX_STAMINA
EXTRA_MOVE_COST = GameConstants.EXTRA_MOVE_COST
ERASE_STEP_EXTRA_COST = GameConstants.ERASE_STEP_EXTRA_COST
BEACON_CONSUME_LEFTOVER_PAINT = GameConstants.BEACON_CONSUME_LEFTOVER_PAINT
STAMINA_POWERUP_AMOUNT = GameConstants.STAMINA_POWERUP_AMOUNT
BEACON_COST = GameConstants.BEACON_COST
BEACON_WINDOW_SIZE_P = GameConstants.BEACON_WINDOW_SIZE_P
BEACON_REQUIREMENT_Q = GameConstants.BEACON_REQUIREMENT_Q
MAX_PAINT_VALUE = GameConstants.MAX_PAINT_VALUE
PAINT_RANGE = GameConstants.PAINT_RANGE
PAINT_STAMINA_COST = GameConstants.PAINT_STAMINA_COST
HILL_CONTROL_THRESHOLD = GameConstants.HILL_CONTROL_THRESHOLD
DOMINATION_WIN_THRESHOLD = GameConstants.DOMINATION_WIN_THRESHOLD
BASE_STAMINA_REGEN = GameConstants.BASE_STAMINA_REGEN
ADJACENT_REGEN_BONUS = GameConstants.ADJACENT_REGEN_BONUS
BEACON_REGEN_BONUS = GameConstants.BEACON_REGEN_BONUS
ADJACENCY_RADIUS = GameConstants.ADJACENCY_RADIUS
MAX_ROUNDS = GameConstants.MAX_ROUNDS

# player 1 has parity -1, player 2 has parity 1

#Parity functions

@njit
def parity_from_value(value: int):
	return 0 if value == 0 else value / abs(value)

@njit	
def get_opponent_parity(parity: int):
	return -1 * parity

@njit	
def owned(cell_parity, player_parity):
	return cell_parity * player_parity > 0
	
@njit
def unowned(cell_parity):
	return cell_parity == 0

#CellState functions

@njit
def get_owner_parity(paint_value: int, beacon_parity: int) -> int:
	if beacon_parity != 0:
		return beacon_parity
	return parity_from_value(paint_value)

@njit		
def clear_beacon(paint_value: int, beacon_parity: int, leftover_value: int = 1) -> Tuple[int, int]:
	new_paint_value = beacon_parity * leftover_value
	new_beacon_parity = 0
	return new_paint_value, new_beacon_parity

@njit		
def set_beacon_value(beacon_parity:int, player_parity: int) -> int:
	return player_parity

@njit
def paint_cell(paint_value: int, beacon_parity: int, player_parity: int, max_value: int) -> int:
	if (
		unowned(beacon_parity) and (unowned(paint_value) or owned(paint_value, player_parity))
	):
		return min(max(paint_value + player_parity, -max_value),  max_value)
	return paint_value
@njit
def weaken_opponent(paint_value: int, beacon_parity: int, player_parity: int) -> int:
	if (
		unowned(beacon_parity) and owned(paint_value, get_opponent_parity(player_parity))
	):
		return paint_value + player_parity
	return paint_value
@njit
def erase(paint_value: int, beacon_parity: int) -> int:
	if(unowned(beacon_parity)):
		return 0
	return paint_value

spec_hill = (
	('id', int64),
    ('cells', int64[:, :]),
    ('control_positive', int64),
    ('control_negative', int64),
    ('controller_parity', int64),
)

@jitclass(spec_hill)
class Hill:
	"""Represents a hill on the map."""
	
	def __init__(self, id_val, cells, control_positive = 0, control_negative = 0, controller_parity = 0):
		self.id = id_val
		self.cells = cells
		
		self.control_positive = control_positive
		self.control_negative = control_negative
		self.controller_parity = controller_parity

	def get_control_diff(self, parity):
		return (self.control_positive + self.control_negative) * parity

	def above_threshold(self, parity, thresh):
		return self.control_positive * parity > thresh or self.control_negative * parity > thresh
	
	def decrement_control(self, player_parity):
		if(player_parity > 0):
			self.control_positive -= 1
		elif(player_parity < 0):
			self.control_negative += 1
			
	def increment_control(self, player_parity):
		if(player_parity > 0):
			self.control_positive += 1
		elif(player_parity < 0):
			self.control_negative -= 1
	
	def control_fraction(self, player_parity):
		num_cells = self.cells.shape[0]
		if(player_parity > 0):
			return self.control_positive / num_cells
		elif(player_parity < 0):
			return self.control_negative / num_cells
		return 0.0
		#probably don't even need return 0.0 to be honest. I will check that later.
	def get_copy(self):
		return Hill(
			self.id,
			self.cells,
			self.control_positive,
			self.control_negative,
			self.controller_parity
		)

HILL_TYPE = Hill.class_type.instance_type



spec_board = [
	('board_size', types.UniTuple(int64, 2)),
    ('current_round', int64),
    ('turn_count', int64),
    ('event_pointer', int64),
    ('parity_to_play', int64),
    
    # Cell state 
    ('paint_values', int64[:, :]),      
    ('is_wall', boolean[:, :]),          
    ('beacon_parity', int64[:, :]),     
    ('hill_id', int64[:, :]),           
    ('powerup', boolean[:, :]),         
    
    # Players
    ('p1', Player.class_type.instance_type),
    ('p2', Player.class_type.instance_type),
    
    # Hills 
    ('hills', types.DictType(int64, Hill.class_type.instance_type)),
    
    # Powerup schedule 
    ('powerup_schedule', int64[:, :]),


]

@jitclass(spec_board)
class Board:
	"""
	Represents the game world state.
	This class will be given to players' code for querying and mutating game state.
	Note that the class is not written for maximum efficiency of simulation,
	but rather for readability and clarity. If you want to speed up simulation,
	the board class and its supporting structures are written in such a way to be 
	easily rewritten in compiled languages or for python JIT compilers.
	"""
	
	def __init__(
		self,
        board_size: Tuple[int, int],
        p1_start: Tuple[int, int],
        p2_start: Tuple[int, int],
        powerup_schedule: np.ndarray,
        wall_list: np.ndarray,
        hill_list: List,
        copy_mode: int = 0
	):
		rows, cols = board_size
		self.board_size = board_size
		self.powerup_schedule = powerup_schedule

		self.paint_values = np.zeros((rows, cols), dtype=np.int64)
		self.is_wall = np.zeros((rows, cols), dtype=np.bool_)
		self.beacon_parity = np.zeros((rows, cols), dtype=np.int64)
		self.hill_id = np.zeros((rows, cols), dtype=np.int64)
		self.powerup = np.zeros((rows, cols), dtype=np.bool_)

		#Experiment to put player here to see if it is causing the problems
		'''
		self.p1 = Player(
				1, 
				p1_start, 
				BASE_MAX_STAMINA, 
				0
			)
		dummy_cells = np.array([[0, 0]], dtype=np.int64)
		dummy_hill = Hill(np.int64(-999), dummy_cells, np.int64(0), np.int64(0), np.int64(0))

		for i in range(len(hill_list)):
				hill_tuple = hill_list[i]
				hill_obj = Hill(
        			hill_tuple[0],  # id
        			hill_tuple[1],  # cells
        			hill_tuple[2],  # control_positive
        			hill_tuple[3],  # control_negative
        			hill_tuple[4]   # controller_parity
    			)
				self.register_hill(hill_obj)

		self.hills = Dict.empty(types.int64, HILL_TYPE)
		'''
		#
		#print("success making experiment")

		self.p1 = Player(
				1, 
				p1_start, 
				BASE_MAX_STAMINA, 
				0
			)

		self.p2 = Player(
				-1, 
				p2_start, 
				BASE_MAX_STAMINA, 
				0
			)
		
		dummy_cells = np.array([[0, 0]], dtype=np.int64)
		dummy_hill = Hill(np.int64(-999), dummy_cells, np.int64(0), np.int64(0), np.int64(0))
		self.hills = Dict.empty(types.int64, HILL_TYPE)
		self.hills[np.int64(-999)] = dummy_hill
		del self.hills[np.int64(-999)]
		
		self.current_round = 0
		self.turn_count = 0
		self.event_pointer = 0
		self.parity_to_play = 0
			
		if copy_mode == 1:
			return
			
			
		for i in range(wall_list.shape[0]):
			r, c = wall_list[i, 0], wall_list[i, 1]
			if not self.oob((r, c)):
				self.is_wall[r,c] = True
			
		
			
		for i in range(len(hill_list)):
			hill_tuple = hill_list[i]
			hill_obj = Hill(
        		hill_tuple[0],  # id
        		hill_tuple[1],  # cells
        		hill_tuple[2],  # control_positive
        		hill_tuple[3],  # control_negative
        		hill_tuple[4]   # controller_parity
    		)
			self.register_hill(hill_obj)

		self._spawn_scheduled_powerups()
		
			
	def oob(self, loc: Tuple[int, int]) -> bool:
		
		return loc[0] < 0 or loc[1] < 0 or loc[0] >= self.board_size[0] or loc[1] >= self.board_size[1]
		
		#return False  # Out-of-bounds checking is not supported in accelerated mode.

	def apply_bid(self, bid1:int, bid2:int):
		# assumes given bids are valid
		
		if not self.is_valid_bid(bid1) or not self.is_valid_bid(bid2):
			return
		
		if(bid1 > bid2):
			self.parity_to_play = 1
			self.p1.stamina -= bid1
		elif(bid1 < bid2):
			self.parity_to_play = -1
			self.p2.stamina -= bid2
		else:
			if np.random.random() < 0.5:
				self.parity_to_play = 1
				self.p1.stamina -= bid1
			else:
				self.parity_to_play = -1
				self.p2.stamina -= bid2
		

	def is_valid_bid(self, bid: int) -> bool:
		return bid <= BASE_MAX_STAMINA
	
	def register_hill(self, hill: Hill):
		
		self.hills[hill.id] = hill
		
		for i in range(hill.cells.shape[0]):
			r, c = hill.cells[i, 0], hill.cells[i, 1]
			if not self.oob((r, c)):
				self.hill_id[r,c] = hill.id
		
	
	def get_player(self, player_parity: int):
		
		return self.p1 if player_parity == 1 else self.p2
		
		#return self
	
	def get_opponent(self, player_parity: int):
		
		return self.p2 if player_parity == 1 else self.p1
		
		#return self
	
	def get_copy(self):
		
		empty_hill_list = TypedList.empty_list(HILL_TUPLE_TYPE)
		new_board = Board(
			self.board_size,
			self.p1.loc,
            self.p2.loc,
            self.powerup_schedule,
            np.empty((0, 2), dtype=np.int64),
            empty_hill_list,
            1
		)

		new_board.current_round = self.current_round
		new_board.event_pointer = self.event_pointer
		new_board.turn_count = self.turn_count
		new_board.parity_to_play = self.parity_to_play
		
		new_board.p1 = self.p1.get_copy()
		new_board.p2 = self.p2.get_copy()
		
		new_board.paint_values[:] = self.paint_values
		new_board.is_wall[:] = self.is_wall
		new_board.beacon_parity[:] = self.beacon_parity
		new_board.hill_id[:] = self.hill_id
		new_board.powerup[:] = self.powerup

		dummy_cells = np.array([[0,0]], dtype = np.int64)
		dummy_hill = Hill(np.int64(-999), dummy_cells, np.int64(0), np.int64(0), np.int64(0))
		new_board.hills = Dict.empty(types.int64, HILL_TYPE)
		new_board.hills[np.int64(-999)] = dummy_hill
		del new_board.hills[np.int64(-999)]
		
		# hill cells are copied by reference since they don't change between hills
		# reregistering hills is unnecessary because target hill_ids were set when copying cells
		for hill_id in self.hills:
			new_board.hills[hill_id] = self.hills[hill_id].get_copy()		
		
		return new_board
		
		#return self
		

	def apply_turn(self, player_parity: int, actions) -> bool:
		
		# keeps track of the number of moves thave have already executed this turn
		moves_this_turn = 0
		for action in actions:
			if len(action) == 6:
				if not self._execute_move(player_parity, action, moves_this_turn):
					return False
				moves_this_turn += 1
			elif len(action) == 2:
				if not self._execute_paint(player_parity, action):
					return False
			
			if self.get_player(player_parity).is_dead():
				return False
			
			if self.get_opponent(player_parity).is_dead():
				return moves_this_turn > 0
		
		self.end_turn()

		return moves_this_turn > 0
		
		#return False  # Applying turns is not supported in accelerated mode.
	
	def forecast_turn(self, player_parity: int, actions):
		
		world_copy = self.get_copy()
		ok = world_copy.apply_turn(player_parity, actions)
		return world_copy, ok
		
		#return self, False  # Forecasting turns is not supported in accelerated mode.
	
	def apply_action(self, player_parity: int, action, moves_this_turn: int = 0) -> bool:
		
		if len(action) == 6:
			return self._execute_move(player_parity, action, moves_this_turn)
		if len(action) == 2:
			return self._execute_paint(player_parity, action)
		return False
		
		#return False  # Applying actions is not supported in accelerated mode.
	
	def forecast_action(self, player_parity: int, action, moves_this_turn: int = 0):
		
		world_copy = self.get_copy()
		ok = world_copy.apply_action(player_parity, action, moves_this_turn)
		return world_copy, ok
		
		#return self, False  # Forecasting actions is not supported in accelerated mode.
	
	def _execute_move(self, player_parity: int, move_action: Tuple, moves_this_turn: int) -> bool:
		
		player = self.get_player(player_parity)
		r,c = player.loc
		self._apply_powerup_if_present(player_parity, r,c)

		if moves_this_turn >= 1:
			cost = EXTRA_MOVE_COST * moves_this_turn
			if player.stamina < cost:
				return False 
			player.stamina -= cost

		move_type = move_action[2]

		if move_type == MOVE_ERASE:
			cost = ERASE_STEP_EXTRA_COST
			if player.stamina < cost:
				return False 
			player.stamina -= cost
			
		if move_type == MOVE_BEACON_TRAVEL:
			# use beacon to travel 
			target_loc = self._beacon_travel(player_parity, move_action)
			if target_loc[0] == -999:
				return False
		else:
			# don't use beacon to travel
			direction = (move_action[0], move_action[1])
			target_loc = location_add(player.loc, direction)
			if self.oob(target_loc):
				return False
		
		# movement occurs here
		target_r, target_c = target_loc
		if self.is_wall[target_r, target_c]:
			return False

		if self._resolve_collision(player_parity):
			return True

		
		player.loc = target_loc
		
		# handle movement effects
		self._handle_erase_effects(player_parity, target_r, target_c, move_type)
		self._apply_powerup_if_present(player_parity, target_r, target_c)

		if move_action[3]:
			self._place_beacon(player_parity, target_loc)

		#  important that this comes before collision resolution
		if not player.clamp_stamina():
			return False
		
		
		return True
	
		
		#return False  # Executing moves is not supported in accelerated mode.
	
	def _beacon_travel(self, player_parity: int, move_action: Tuple):
		
		player = self.get_player(player_parity)
		r, c = player.loc
        
        
		if self.beacon_parity[r, c] != player_parity:
			return (-999, -999)  # Invalid beacon travel
        
		target_r, target_c = move_action[4], move_action[5]
		if target_r == -999:  # Invalid target
			return (-999, -999)
        
		target_loc = (target_r, target_c)
		if self.oob(target_loc):
			return (-999, -999)
		if self.beacon_parity[target_r, target_c] != player_parity:
			return (-999, -999)  # Invalid target beacon
        
		self.paint_values[r, c] = player_parity * BEACON_CONSUME_LEFTOVER_PAINT
		self.beacon_parity[r, c] = 0
		player.beacon_count = max(0, player.beacon_count - 1)
        
		return target_loc
		
		#return (-999, -999)  # Beacon travel is not supported in accelerated mode.
	
	def _handle_erase_effects(self, player_parity: int, r: int, c: int, move_type: int):
		
		if not unowned(self.beacon_parity[r, c]):
			return
        
		prev = self.paint_values[r, c]

		if move_type == MOVE_ERASE:
			self.paint_values[r, c] = 0
		else:
            
			if owned(prev, get_opponent_parity(player_parity)):
				self.paint_values[r, c] = prev + player_parity
        
		now = self.paint_values[r, c]
        
		if now == 0 and prev != 0:
			self._release_square(r, c, parity_from_value(prev))
		

	def _apply_powerup_if_present(self, player_parity: int, r: int, c: int):
		
		if not self.powerup[r, c]:
			return
        
		player = self.get_player(player_parity)
		player.stamina = min(player.max_stamina, player.stamina + STAMINA_POWERUP_AMOUNT)
		self.powerup[r, c] = False
		
	
	def _place_beacon(self, player_parity: int, origin: Tuple[int, int]) -> bool:
		
		if self.oob(origin):
			return False
        
		r, c = origin
		player = self.get_player(player_parity)
        
        
		owner = get_owner_parity(self.paint_values[r, c], self.beacon_parity[r, c])
		if owner != player_parity:
			return False
        
		if self.beacon_parity[r, c] != 0:
			return False
        
		if player.stamina < BEACON_COST:
			return False
        
       
		window_radius = BEACON_WINDOW_SIZE_P // 2
		window_cells = location_square_region(origin, window_radius)
        
		friendly_count = 0
		opponent_parity = get_opponent_parity(player_parity)
        
        
		for i in range(window_cells.shape[0]):
			wr, wc = window_cells[i, 0], window_cells[i, 1]
			if self.oob((wr, wc)):
				continue
            
			if unowned(self.beacon_parity[wr, wc]):
				if owned(self.paint_values[wr, wc], player_parity):
					friendly_count += 1
        
		if friendly_count < BEACON_REQUIREMENT_Q:
			return False
        
		player.stamina -= BEACON_COST
        
        
		for i in range(window_cells.shape[0]):
			wr, wc = window_cells[i, 0], window_cells[i, 1]
			if self.oob((wr, wc)):
				continue
            
			if unowned(self.beacon_parity[wr, wc]):
				if owned(self.paint_values[wr, wc], player_parity):
					self.paint_values[wr, wc] -= player_parity
					if self.paint_values[wr, wc] == 0:
						self._release_square(wr, wc, player_parity)
				elif owned(self.paint_values[wr, wc], opponent_parity):
					self.paint_values[wr, wc] = max(
                        -MAX_PAINT_VALUE,
                        min(MAX_PAINT_VALUE, self.paint_values[wr, wc] + opponent_parity)
                    )
        
		self.beacon_parity[r, c] = player_parity
		player.beacon_count += 1
        
		return True
		
		#return False  # Placing beacons is not supported in accelerated mode.
	
	def _resolve_collision(self, moving_player_parity: int) -> bool:
		
		moving_player = self.get_player(moving_player_parity)
		opponent = self.get_opponent(moving_player_parity)
		
		if moving_player.loc[0] != opponent.loc[0] or moving_player.loc[1] != opponent.loc[1]:
			return False
		
		r,c = moving_player.loc
		cell_owner = get_owner_parity(self.paint_values[r, c], self.beacon_parity[r, c])
		
		if cell_owner == opponent.parity:
			moving_player.stamina = -1
		else:
			opponent.stamina = -1
		return True
		
		#return False  # Resolving collisions is not supported in accelerated mode.
	def _execute_paint(self, player_parity: int, paint_action: Tuple) -> bool:
		
		player = self.get_player(player_parity)
		target_r, target_c = paint_action[0], paint_action[1]
		
		if self.oob((target_r, target_c)):
			return False
		
		manhattan_dist = manhattan_distance(player.loc, (target_r, target_c))
		if manhattan_dist == 0 or manhattan_dist > PAINT_RANGE:
			return False
		
		if player.stamina < PAINT_STAMINA_COST:
			return False
		
		owner = get_owner_parity(self.paint_values[target_r, target_c], self.beacon_parity[target_r, target_c])
		if owner != player_parity:
			return False
		
		player.stamina -= PAINT_STAMINA_COST

		prev = self.paint_values[target_r, target_c]

		if unowned(self.beacon_parity[target_r, target_c]) and (unowned(prev) or owned(prev, player_parity)):
			self.paint_values[target_r, target_c] = min(
				max(prev + player_parity, -MAX_PAINT_VALUE), 
				MAX_PAINT_VALUE
			)

		next_val = self.paint_values[target_r, target_c]

		if(prev == 0 and next_val != 0): 
			# you can't paint on squares of opponent color
			self._claim_square(target_r, target_c, player_parity)
		if not player.clamp_stamina():
			return False
		
		return True
		
		#return False  # Executing paint actions is not supported in accelerated mode.
		
	# turn	
	def end_turn(self):
		
		self.turn_count += 1
		self.parity_to_play *= -1 
		self.current_round = self.turn_count // 2
		self._spawn_scheduled_powerups()
		self._apply_regeneration(self.parity_to_play)
		
	
	"""
	# TODO: Do we want inlined hill control calcualtions, or do we want to do it all at the end of a round
	# def _update_hill_control(self, hill_id) -> None:
	# 	for hill in self.hills.values():
	# 		controller, fraction = hill.control_fraction(self.cells)
	# 		threshold = GameConstants.HILL_CONTROL_THRESHOLD
	# 		if controller == 0 or fraction < threshold:
	# 			if hill.controller != 0:
	# 				self._release_hill(hill.controller, hill.id)
	# 			hill.controller = 0
	# 			continue
			
	# 		if hill.controller == controller:
	# 			continue
			
	# 		if hill.controller != 0:
	# 			self._release_hill(hill.controller, hill.id)
			
	# 		hill.controller = controller
	# 		self._claim_hill(controller, hill.id)
	"""

	def _claim_square(self, r:int, c:int, player_parity: int):
		
		hid = self.hill_id[r,c]
		if hid == 0:
			return
		
		hill =self.hills[hid]
		hill.increment_control(player_parity)

		opponent_parity = get_opponent_parity(player_parity)
		opponent = self.get_opponent(player_parity)

		if owned(hill.controller_parity, opponent_parity):
			if hill.get_control_diff(player_parity) >= 0:
				opponent.lose_hill_control(hid)
				hill.controller_parity = 0

		if unowned(hill.controller_parity):
			if hill.above_threshold(player_parity, HILL_CONTROL_THRESHOLD):
				if hill.get_control_diff(player_parity) > 0:
					player = self.get_player(player_parity)
					player.gain_hill_control(hid)
					hill.controller_parity = player_parity
					if len(self.hills) > 0 and len(player.controlled_hills) >= DOMINATION_WIN_THRESHOLD * len(self.hills):
						opponent.stamina = -1
		

			
	def _release_square(self, r: int, c: int, owner_parity: int):
		
		hid = self.hill_id[r,c]
		if(hid == 0):
			return
		
		hill =self.hills[hid]
		hill.decrement_control(owner_parity)

		# only way to lose a hill is if your opponent has equal or more cells than you do on the hill
		# TODO: may want to make it so that loss also happens if you go below threshold
		# via # or not hill.above_threshold(owner_parity, GameConstants.HILL_CONTROL_THRESHOLD)
		
		if owned(hill.controller_parity, owner_parity):
			if hill.get_control_diff(owner_parity) <= 0:
				owner = self.get_player(owner_parity)
				owner.lose_hill_control(hid)
				hill.controller_parity = 0

		# opponent still have to be above threshold though to gain it
		opponent_parity = get_opponent_parity(owner_parity)
		if unowned(hill.controller_parity):
			if hill.above_threshold(opponent_parity, HILL_CONTROL_THRESHOLD):
				if hill.get_control_diff(owner_parity) < 0:
					opponent = self.get_player(opponent_parity)
					opponent.gain_hill_control(hid)
					hill.controller_parity = opponent_parity
					
	
	
	def _apply_regeneration(self, player_parity: int):
		
		player = self.get_player(player_parity)
		if player.is_dead():
			return
		
		regen = BASE_STAMINA_REGEN
		regen += self._count_adjacent_friendly(player_parity) * ADJACENT_REGEN_BONUS
		if player.beacon_count > 0:
			regen += player.beacon_count * BEACON_REGEN_BONUS
		
		player.stamina = min(player.max_stamina, player.stamina + regen)
		
	
	def _count_adjacent_friendly(self, player_parity: int) -> int:
		
		player = self.get_player(player_parity)
		r, c = player.loc
		count = 0
		radius = max(1, ADJACENCY_RADIUS)
		for dr in range(-radius, radius + 1):
			for dc in range(-radius, radius + 1):
				nr, nc = r + dr, c + dc
				if self.oob((nr, nc)):
					continue
				owner = get_owner_parity(self.paint_values[nr, nc], self.beacon_parity[nr, nc])
				if owner == player_parity:
					count += 1
		return count
		
		#return 0  # Counting adjacent friendly cells is not supported in accelerated mode.
	
	def _spawn_scheduled_powerups(self):
		
		while self.event_pointer < self.powerup_schedule.shape[0]:
			round_num = self.powerup_schedule[self.event_pointer][0]
			if round_num > self.current_round:
				break
			r = self.powerup_schedule[self.event_pointer, 1]
			c = self.powerup_schedule[self.event_pointer, 2]
			self._spawn_powerup((r, c))
			self.event_pointer += 1	
		
	
	def _spawn_powerup(self, location: Tuple[int, int]):
		
		if self.oob(location):
			return
		r, c = location
		if self.is_wall[r, c]:
			return
		
		self.powerup[r, c] = True
		

	
	def get_territory_count(self, player_parity: int) -> int:
		
		count = 0
		for r in range(self.board_size[0]):
			for c in range(self.board_size[1]):
				owner = get_owner_parity(self.paint_values[r, c], self.beacon_parity[r, c])
				if owner == player_parity:
					count += 1
		return count

		#return 0  # Getting territory count is not supported in accelerated mode.
	
	
	def get_winner(self) -> Tuple:
		
		if self.p1.is_dead():
			if len(self.hills) > 0 and len(self.p1.controlled_hills) >= DOMINATION_WIN_THRESHOLD * len(self.hills):
				return (-1, 7)
			if self.p1.loc[0] == self.p2.loc[0] and self.p1.loc[1] == self.p2.loc[1]:
				return (-1, 8)
			return (-1, 5)
		if self.p2.is_dead():
			if len(self.hills) > 0 and len(self.p2.controlled_hills) >= DOMINATION_WIN_THRESHOLD * len(self.hills):
				return (1, 7)
			if self.p1.loc[0] == self.p2.loc[0] and self.p1.loc[1] == self.p2.loc[1]:
				return (1, 8)
			return (1, 5)

		if self.current_round >= MAX_ROUNDS:
			p1_territory = self.get_territory_count(1)
			p2_territory = self.get_territory_count(-1)
			if p1_territory > p2_territory:
				return (1, 0)
			if p2_territory > p1_territory:
				return (-1, 0)
			return (0, 0)
		return (0, -1)
		
		#return (0, -1)  # Determining the winner is not supported in accelerated mode.
	

