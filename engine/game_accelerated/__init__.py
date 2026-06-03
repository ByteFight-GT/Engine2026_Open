"""
Bytefight 2026 Game Engine - King of the Hill

A competitive coding game where players control territories, manage stamina,
and compete for control of hills on a dynamic battlefield. The files included
in these packages are sufficient for simulating the entirety of the game mechanics.
If you are a competitor, you will most likely only be looking at files in
this package (and potentially scripts if you are running from terminal).

If you are a developer, for game setup and gameplay management, 
see the game_runner package.
"""


from .game_structs import Action, MoveType, Location, Direction
from .game_constants import GameConstants
from .player import Player
from .board import Board, Hill
from .outcome import Result, WinReason

__all__ = [
    'Action',
    'MoveType',
    'GameConstants',
    'Location',
    'Direction',
    'Player',
	'Board',
	'CellState',
    'ScheduledPowerup',
    'Parity',
	'Hill',
	'Result',
	'WinReason',
]
