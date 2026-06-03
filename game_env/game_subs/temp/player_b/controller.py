from collections.abc import Callable, Iterable
from typing import Union
import time
import random

from game import Action, World


class PlayerController:
	"""
	/you may add functions, however, __init__, bid, and play are the entry
	points for your program and should not be changed.
	"""

	def __init__(self, time_left: Callable):
		return

	def bid(self, world: World, player_num: int, time_left: Callable) -> int:
		"""
		Called at the start of the game. Return the number of stamina you
		want to bid for initiative.
		"""
		remaining_time = time_left()
		
		if remaining_time > 50:
			bid_amount = 10
		elif remaining_time > 30:
			bid_amount = 8
		elif remaining_time > 10:
			bid_amount = 5
		else:
			bid_amount = 2
		
		return bid_amount

	def play(
		self,
		world: World,
		player_num: int,
		time_left: Callable,
	) -> Union[Action.Move, Action.Paint, Iterable[Action.Move | Action.Paint]]:
		# Artificial delay to test timeout mechanics
		time.sleep(0.1)
		
		# Return randomly 1-3 moves to test move chaining
		actions = []
		
		# Generate up to 3 random moves
		for _ in range(3):
			# Simple random action (would need actual game logic here)
			actions.append(Action.Move(random.randint(0, 3)))  # Dummy move
		
		# Randomly select 1, 2, or 3 moves to return
		if actions:
			num_moves = random.randint(1, len(actions))
			return actions[:num_moves]
		
		return []

