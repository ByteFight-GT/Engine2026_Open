from typing import Dict, Tuple
#from game_accelerated.game_structs import Location
from game_accelerated.game_constants import GameConstants
from numba import int64, types, boolean
from numba.experimental import jitclass
from numba.typed import Dict

BASE_MAX_STAMINA = GameConstants.BASE_MAX_STAMINA
HILL_MAX_STAMINA_BONUS = GameConstants.HILL_MAX_STAMINA_BONUS


spec = [
    ('stamina', int64),
    ('max_stamina', int64),
    ('loc', types.UniTuple(int64, 2)),
    ('beacon_count', int64),
    ('parity', int64),
    ('controlled_hills', types.DictType(int64, boolean)),
]

@jitclass(spec)
class Player:
    """
    Represents a player in the game. Parity of 1 for player 1, and parity of -1 for 
    player 2.
    """
    
    def __init__(self, 
              parity:int, 
              location:Tuple[int, int],
              max_stamina:int, copy:int=0):
        self.max_stamina = max_stamina
        self.loc = location
        self.parity = parity

        if copy == 0:
            self.stamina = max_stamina
            self.controlled_hills = Dict.empty(int64, boolean)
            self.beacon_count = 0
    
    def clamp_stamina(self) -> bool:
        # returns if stamina you are alive at the end
        if self.stamina > self.max_stamina:
            self.stamina = self.max_stamina
        return self.stamina >= 0
    
    def is_dead(self) -> bool:
        return self.stamina < 0
    
    def gain_hill_control(self, hill_id):
        if hill_id not in self.controlled_hills:
            self.controlled_hills[hill_id] = True   
            self.max_stamina = BASE_MAX_STAMINA + len(self.controlled_hills) * HILL_MAX_STAMINA_BONUS

    def lose_hill_control(self, hill_id):
        if hill_id in self.controlled_hills:
            del self.controlled_hills[hill_id]
            self.max_stamina = BASE_MAX_STAMINA + len(self.controlled_hills) * HILL_MAX_STAMINA_BONUS
            self.clamp_stamina()
    
    def get_copy(self) -> "Player":
        new_player = Player(
            self.parity,
            self.loc, 
            self.max_stamina,1
        )

        new_player.stamina = self.stamina
        new_player.controlled_hills = Dict.empty(int64, boolean)
        for h in self.controlled_hills:
            new_player.controlled_hills[h] = True
        new_player.beacon_count = self.beacon_count

        return new_player