import unittest
from game import Action, Direction, MoveType, Location

class TestStructs(unittest.TestCase):
    def test_create_struct(self):
        a1 = Action.Move(Direction.LEFT, MoveType.REGULAR, place_beacon=False, beacon_target=None)
        a2 = Action.Paint(Location(1, 1))
    
    def test_location(self):
        location1 = Location(1, 1)
        location2 = Location(0, 0)
        newloc = location1 - location2

        assert location1 == newloc

        location3 = location1 - Location(2, 2)
        assert location3 == Location(-1, -1)
        assert not location3 is Location(-1, -1)    
        
        location1 += Direction.DOWN
        assert location1 == Location(2, 1)
        location1 += Direction.RIGHT
        assert location1 == Location(2, 2)
        location1 += Direction.UP
        assert location1 == Location(1, 2)
        location1 += Direction.LEFT
        assert location1 == Location(1, 1)

    def test_direction(self):
        Direction.cardinals()