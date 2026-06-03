import unittest
from game import *
from typing import List


class TestBoard(unittest.TestCase):

    def setUp(self):
        # minimal board setup
        self.b1 = Board(
            board_size=Location(5, 5), 
            p1_start=Location(0, 0), p2_start=Location(4,4),
        )

        powerup_schedule = [ScheduledPowerup(100, Location(2, 2))]

        self.b2 = Board(
            board_size=Location(5, 5), 
            p1_start=Location(0, 0), p2_start=Location(4, 4),
            powerup_schedule=powerup_schedule
        )

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

        self.b3 = Board(
            board_size=Location(5, 5), 
            p1_start=Location(0, 0), p2_start=Location(4, 4),
            powerup_schedule=powerup_schedule,
            hill_list= hill_list,
            wall_list=wall_list
        )

        self.b3.apply_bid(10, 0)
        


        
    # apply_bid
    def test_apply_bid(self):
        self.b1.apply_bid(0, 1)
        assert self.b1.p1.stamina == GameConstants.BASE_MAX_STAMINA
        assert self.b1.p2.stamina == GameConstants.BASE_MAX_STAMINA - 1

        self.b2.apply_bid(1, 0)
        assert self.b2.p1.stamina == GameConstants.BASE_MAX_STAMINA - 1
        assert self.b2.p2.stamina == GameConstants.BASE_MAX_STAMINA


    # is_valid_bid
    def test_is_valid_bid(self):
        assert self.b1.is_valid_bid(GameConstants.BASE_MAX_STAMINA)
        assert not self.b1.is_valid_bid(GameConstants.BASE_MAX_STAMINA+1)


    # register_hill
    def test_register_hill(self):
        h1 = Hill(1, [Location(2, 2)])
        h2 = Hill(2, [Location(1, 1), Location(3, 3)])

        self.b1.register_hill(h1)
        self.b1.register_hill(h2)

        assert self.b1.cells[2][2].hill_id == 1
        assert self.b1.cells[1][1].hill_id == 2
        assert self.b1.cells[3][3].hill_id == 2


        hill_locs = set([(1, 1), (2, 2), (3, 3)])
        for r in range(self.b1.board_size.r):
            for c in range (self.b1.board_size.c):
                if (r,c) in hill_locs:
                    continue
                assert self.b1.cells[r][c].hill_id == 0

    # get_player
    def test_get_player(self):
        assert self.b1.get_player(1) is self.b1.p1
        assert self.b1.get_player(-1) is self.b1.p2

        assert not self.b2.get_player(1) is self.b1.p1
        assert not self.b2.get_player(-1) is self.b1.p2

    # get_opponent
    def test_get_opponent(self):
        assert self.b1.get_opponent(1) is self.b1.p2
        assert self.b1.get_opponent(-1) is self.b1.p1

        assert not self.b2.get_opponent(1) is self.b1.p2
        assert not self.b2.get_opponent(-1) is self.b1.p1

    # get_copy
    def test_get_copy(self):
        h1 = Hill(1, [Location(2, 2)])
        h2 = Hill(2, [Location(1, 1), Location(3, 3)])

        self.b2 = Board(
            board_size=Location(5, 5), 
            p1_start=Location(0, 0), p2_start=Location(4, 4),
            powerup_schedule=[ScheduledPowerup(100, Location(2, 2))],
            hill_list= [h1, h2]
        )
        b1_copy = self.b1.get_copy()
        b2_copy = self.b2.get_copy()

        b3_copy = self.b3.get_copy()
        assert b3_copy.board_size is self.b3.board_size
        assert b3_copy.powerup_schedule is self.b3.powerup_schedule
        assert b3_copy.turn_count == self.b3.turn_count
        assert b3_copy.event_pointer == self.b3.event_pointer
        assert b3_copy.parity_to_play == self.b3.parity_to_play
        assert not b3_copy.cells is self.b3.cells 
        for r in range(self.b3.board_size.r):
            for c in range(self.b3.board_size.c):
                assert self.b3.cells[r][c].paint_value == b3_copy.cells[r][c].paint_value
                assert self.b3.cells[r][c].is_wall == b3_copy.cells[r][c].is_wall
                assert self.b3.cells[r][c].beacon_parity == b3_copy.cells[r][c].beacon_parity
                assert self.b3.cells[r][c].hill_id == b3_copy.cells[r][c].hill_id
                assert self.b3.cells[r][c].powerup == b3_copy.cells[r][c].powerup

        assert not self.b3.hills is b3_copy.hills

        for id in self.b3.hills.keys():
            og = self.b3.hills[id]
            new = b3_copy.hills[id]
            assert og.id == new.id
            assert og.cells is new.cells
            assert og.control_positive == new.control_positive
            assert og.control_negative == new.control_negative

    # apply_turn
    def test_apply_turn(self):
        pass

    # forecast_turn
    def test_forecast_turn(self):
        pass

    # apply_action
    def test_apply_action(self):
        pass

    # forecast_action
    def test_forecast_action(self):
        pass

    # _execute_move
    def test_execute_move(self):
        pass

    # _beacon_travel
    def test_beacon_travel(self):
        pass

    # _handle_step_effect
    def test_handle_step_effect(self):
        pass

    # _apply_powerup_if_present
    def test_apply_powerup_if_present(self):
        pass

    # _place_beacon
    def test_place_beacon(self):
        pass

    # _resolve_collision
    def test_resolve_collision(self):
        pass

    # _execute_paint
    def test_execute_paint(self):
        pass

    # end_turn
    def test_end_turn(self):
        self.b3.end_turn()
        assert self.b3.turn_count == 1
        assert self.b3.parity_to_play == -1

    # _claim_square
    def test_claim_release_square(self):
        self.b3._claim_square(self.b3.cells[2][2], 1)
        assert 1 in self.b3.p1.controlled_hills

        self.b3._claim_square(self.b3.cells[1][1], 1)
        assert 2 in self.b3.p1.controlled_hills
        self.b3._claim_square(self.b3.cells[3][3], -1)
        assert not 2 in self.b3.p1.controlled_hills
        assert not 2 in self.b3.p2.controlled_hills
        self.b3._release_square(self.b3.cells[1][1], 1)
        assert not 2 in self.b3.p1.controlled_hills
        assert 2 in self.b3.p2.controlled_hills
        self.b3._claim_square(self.b3.cells[1][1], -1)
        assert not 2 in self.b3.p1.controlled_hills
        assert 2 in self.b3.p2.controlled_hills
        self.b3._release_square(self.b3.cells[1][1], -1)
        assert not 2 in self.b3.p1.controlled_hills
        assert 2 in self.b3.p2.controlled_hills
        self.b3._release_square(self.b3.cells[3][3], -1)
        assert not 2 in self.b3.p1.controlled_hills
        assert not 2 in self.b3.p2.controlled_hills

    # _apply_regeneration
    def test_apply_regeneration(self):
        pass

    # _count_adjacent_friendly
    def test_count_adjacent_friendly(self):
        pass

    # _spawn_scheduled_powerups
    def test_spawn_scheduled_powerups(self):
        self.b2.turn_count = 199
        self.b2.end_turn()
        assert self.b2.cells[2][2].powerup == True

    # _spawn_powerup
    def test_spawn_powerup(self):
        self.b3._spawn_powerup(Location(3, 3))
        assert self.b3.cells[3][3].powerup == True

        for r in range(self.b1.board_size.r):
            for c in range (self.b1.board_size.c):
                if (r,c) == (3, 3):
                    continue
                assert self.b3.cells[r][c].powerup == 0

    # get_territory_count
    def test_get_territory_count(self):
        pass



if __name__ == "__main__":
    unittest.main()
