import unittest
import numpy


from game import Player, GameConstants, Location


class TestPlayerBasics(unittest.TestCase):
    def test_player_init(self):
        p1 = Player(1, Location(3, 5), GameConstants.BASE_MAX_STAMINA)

        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA
        assert p1.parity == 1
        assert p1.loc.r == 3
        assert p1.loc.c == 5
        assert len(p1.controlled_hills) == 0
        assert p1.stamina == p1.max_stamina
        assert p1.stamina == GameConstants.BASE_MAX_STAMINA
        assert p1.beacon_count == 0

        assert not p1.is_dead()

    def test_hill_control(self):
        p1 = Player(1, Location(3, 5), GameConstants.BASE_MAX_STAMINA)

        p1.gain_hill_control(1)
        assert 1 in p1.controlled_hills
        assert len(p1.controlled_hills) == 1
        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA + \
            GameConstants.HILL_MAX_STAMINA_BONUS * len(p1.controlled_hills)

        p1.gain_hill_control(2)
        assert 1 in p1.controlled_hills
        assert 2 in p1.controlled_hills
        assert len(p1.controlled_hills) == 2
        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA + \
            GameConstants.HILL_MAX_STAMINA_BONUS * len(p1.controlled_hills)

        p1.lose_hill_control(1)
        assert not 1 in p1.controlled_hills
        assert 2 in p1.controlled_hills
        assert len(p1.controlled_hills) == 1
        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA + \
            GameConstants.HILL_MAX_STAMINA_BONUS * len(p1.controlled_hills)

        p1.gain_hill_control(3)
        assert not 1 in p1.controlled_hills
        assert 2 in p1.controlled_hills
        assert 3 in p1.controlled_hills
        assert len(p1.controlled_hills) == 2
        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA + \
            GameConstants.HILL_MAX_STAMINA_BONUS * len(p1.controlled_hills)

        p1.lose_hill_control(3)
        assert 2 in p1.controlled_hills
        assert not 1 in p1.controlled_hills
        assert not 3 in p1.controlled_hills
        assert len(p1.controlled_hills) == 1
        assert p1.max_stamina == GameConstants.BASE_MAX_STAMINA + \
            GameConstants.HILL_MAX_STAMINA_BONUS * len(p1.controlled_hills)
        
    def test_stamina(self):
        p1 = Player(1, Location(3, 5), GameConstants.BASE_MAX_STAMINA)

        prev_stamina = p1.stamina
        p1.gain_hill_control(1)
        assert prev_stamina == p1.stamina
        
        p1.stamina += GameConstants.HILL_MAX_STAMINA_BONUS + 1
        p1.clamp_stamina()
        assert p1.stamina  == p1.max_stamina
        
        prev_stamina = p1.stamina
        p1.gain_hill_control(2)
        assert prev_stamina == p1.stamina
        p1.stamina += GameConstants.HILL_MAX_STAMINA_BONUS + 1
        p1.clamp_stamina()
        assert p1.stamina  == p1.max_stamina

        prev_stamina = p1.stamina
        p1.lose_hill_control(1)
        assert prev_stamina == p1.stamina + GameConstants.HILL_MAX_STAMINA_BONUS

        prev_stamina = p1.stamina
        p1.gain_hill_control(3)
        assert prev_stamina == p1.stamina
        assert p1.stamina == p1.max_stamina - GameConstants.HILL_MAX_STAMINA_BONUS

        prev_stamina = p1.stamina
        p1.lose_hill_control(3)
        assert prev_stamina == p1.stamina

    def test_dead(self):
        p1 = Player(1, Location(3, 5), GameConstants.BASE_MAX_STAMINA)
        p1.stamina = -1

        assert p1.is_dead()
        p1.stamina = -100
        assert p1.is_dead()
        assert not p1.clamp_stamina()

        p1.stamina = 1
        assert not p1.is_dead()
        assert p1.clamp_stamina()

class TestPlayerCopy(unittest.TestCase):
    def test_copy_works(self):
        p1 = Player(1, Location(3, 5), GameConstants.BASE_MAX_STAMINA)
        p1_copy = p1.get_copy()

        assert not p1 is p1_copy
        assert not p1.loc is p1_copy.loc
        assert not p1.controlled_hills is p1_copy.controlled_hills

        print(type(p1.loc), type(p1_copy.loc))

        assert p1.stamina == p1_copy.stamina
        assert p1.controlled_hills == p1_copy.controlled_hills
        assert p1.beacon_count == p1_copy.beacon_count
        assert p1.max_stamina == p1_copy.max_stamina
        assert p1.loc == p1_copy.loc
        assert p1.parity == p1_copy.parity

    def test_copy_diff(self):
        p1 = Player(
            1,
            Location(3, 5),
            GameConstants.BASE_MAX_STAMINA
        )
        p1.gain_hill_control(1)
        p1.gain_hill_control(2)
        p1.beacon_count = 3


        p1_copy = p1.get_copy()

        p1_copy.loc = Location(9, 9)
        assert p1.loc == Location(3, 5)
        assert p1_copy.loc == Location(9, 9)

        
        p1_copy.gain_hill_control(10)
        assert 10 not in p1.controlled_hills
        assert 10 in p1_copy.controlled_hills
        assert 1 and 2 in p1.controlled_hills
        assert 1 and 2 in p1_copy.controlled_hills
        assert p1_copy.max_stamina != p1.max_stamina
        assert p1_copy.stamina == p1.stamina

        p1_copy.stamina += 10
        assert p1.stamina != p1_copy.stamina

        p1_copy.beacon_count += 1
        assert p1.beacon_count != p1_copy.beacon_count

        p1_copy.parity = p1.parity * -1
        assert p1.parity != p1_copy.parity


        






