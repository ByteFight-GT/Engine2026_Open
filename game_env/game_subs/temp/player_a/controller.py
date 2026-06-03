from collections.abc import Callable, Iterable
from typing import Union, Optional, Tuple

from game import *
from .player_board import PlayerBoard
import random
import time

# Global flag to control single move behavior
# If True: single moves are paint-only
# If False: single moves are movement-only
SINGLE_MOVE_IS_PAINT_ONLY = False

# Global flag to control beacon moves
ENABLE_BEACON_MOVES = True

# Global flag to prioritize stamina reset by teleporting to the same beacon
# When True: bot will preferentially teleport back to previous beacon to reset extra move stamina
# When False: bot uses normal beacon travel strategy
PRIORITIZE_STAMINA_RESET = True

# Global flag to prevent beacon teleportation spamming
# When True: bot can teleport through beacons but won't spam continuous beacon hops
# When False: bot can freely spam beacon teleportation
ALLOW_BEACON_SPAM = False

# Global flag to enable hill control strategy
ENABLE_HILL_CONTROL = False

# Detailed manual move selection for testing
# MANUAL_MOVE_SELECTION: maps (turn_number, player_parity) -> list of Action objects
# This allows precise control over bot behavior for testing
# 
# EXAMPLE MOVES:
# Action.Move(Direction.LEFT)          # Move left
# Action.Move(Direction.RIGHT)         # Move right
# Action.Move(Direction.UP)            # Move up
# Action.Move(Direction.DOWN)          # Move down
# Action.Move(Direction.NONE, move_type=MoveType.ERASE)  # Erase in current direction
# Action.Move(None, move_type=MoveType.BEACON_TRAVEL, beacon_target=Location(5, 7))  # Teleport to beacon at (5,7)
# Action.Move(Direction.RIGHT, place_beacon=True)  # Move right and place beacon
# Action.Paint(Location(3, 4))         # Paint cell at (3, 4)
#
# EXAMPLE CONFIGURATION:
# MANUAL_MOVE_SELECTION = {
#     (0, 1): [Action.Move(Direction.LEFT), Action.Move(Direction.UP), Action.Paint(Location(5, 5))],
#     (0, -1): [Action.Move(None, move_type=MoveType.BEACON_TRAVEL, beacon_target=Location(3, 4))],
#     (1, 1): [Action.Move(Direction.RIGHT), Action.Paint(Location(6, 6))],
# }
# 
# Leave empty {} to use default AI behavior
MANUAL_MOVE_SELECTION = {
}

# Customizable delay between bot moves (in seconds) for testing visibility
# Set to 0 for no delay, increase to slow down gameplay for observation
MOVE_DELAY_SECONDS = 0.01


class PlayerController:
    """
    You may add functions, however, __init__, bid, and play are the entry
    points for your program and should not be changed.
    """
    
    def __init__(self, player_parity:int, time_left: Callable):
        self.last_beacon_used = None  # Track the last beacon we teleported to for stamina reset
        self.turns_since_beacon_used = 0  # Track turns passed since last beacon teleportation
        self.turn_count = 0  # Track turn number for manual move selection
        return
    
    def bid(self, board: Board, player_parity: int, time_left: Callable) -> int:
        """
        Called at the start of the game. Return the number of stamina you
        want to bid for initiative. The player with the higher bid wins the
        first move and loses that much stamina (starts with 100 - bid amount).
        
        This stamina bidding mechanic prevents the first player from gaining
        an overwhelming advantage by taking too many moves first.
        """
        # Simple bidding strategy: bid based on remaining time
        # Higher bid if we have more time to think; conservative bid otherwise
        remaining_time = time_left()
        
        # Scale bid based on time remaining (in seconds)
        if remaining_time > 50:
            bid_amount = 20  # Aggressive bid if we have lots of time
        elif remaining_time > 30:
            bid_amount = 15
        elif remaining_time > 10:
            bid_amount = 10
        else:
            bid_amount = 5  # Conservative bid if low on time
        
        return bid_amount
    
    def play(
    self,
    board: Board,
    player_parity: int,
    time_left: Callable,
    ) -> Union[Action.Move, Action.Paint, Iterable[Action.Move | Action.Paint]]:
        # Add delay for visibility during testing (customize MOVE_DELAY_SECONDS)
        if MOVE_DELAY_SECONDS > 0:
            time.sleep(MOVE_DELAY_SECONDS)
        
        # Check for manual move selection first
        manual_moves = MANUAL_MOVE_SELECTION.get((self.turn_count, player_parity))
        self.turn_count += 1
        
        if manual_moves is not None:
            # Return the manually configured actions
            return manual_moves
        
        player = board.get_player(player_parity)
        opponent = board.get_opponent(player_parity)

        # We'll simulate stamina consumption as we build the action chain so
        # we never return an action sequence the engine will reject.
        simulated_stamina = player.stamina
        actions: list = []
        simulated_pos = player.loc
        movement_count = 0  # counts movement steps in the chain (first is free)

        # Emergency: Low stamina - retreat to regenerate
        if player.stamina < 15:
            safe_move = self._find_move_to_friendly_territory(board, player_parity)
            if PRIORITIZE_STAMINA_RESET:
                self.turns_since_beacon_used += 1
            return safe_move if safe_move else self._get_random_safe_move(board, player_parity)

        # PRIORITY 0: Check for hill control strategy if enabled
        if ENABLE_HILL_CONTROL:
            hill_control_info = self._find_best_hill_to_control(board, player_parity)
            if hill_control_info:
                hill_actions = self._generate_hill_control_actions(board, player_parity, hill_control_info)
                if hill_actions:
                    if PRIORITIZE_STAMINA_RESET:
                        self.turns_since_beacon_used += 1
                    return hill_actions

        # Step 1: Try to paint an owned or neutral, weak/adjacent square first
        if simulated_stamina >= GameConstants.PAINT_STAMINA_COST:
            paint_target = self._find_best_paint_target(board, player_parity)
            if paint_target:
                actions.append(Action.Paint(paint_target))
                simulated_stamina -= GameConstants.PAINT_STAMINA_COST

        # Step 2: Try to add up to 3 movement steps while checking stamina costs
        # PRIORITY 1: Stamina reset by teleporting to the same beacon if needed
        candidate_first = None
        stamina_reset_move = None
        
        if PRIORITIZE_STAMINA_RESET:
            stamina_reset_move = self._find_stamina_reset_beacon_move(board, player_parity)
        
        if stamina_reset_move:
            candidate_first = stamina_reset_move
        # PRIORITY 2: Hunt opponent beacons for destruction
        elif ENABLE_BEACON_MOVES:
            opponent_beacon_move = self._find_move_toward_opponent_beacon(board, player_parity)
            if opponent_beacon_move:
                candidate_first = opponent_beacon_move
        
        # PRIORITY 3: Fallback to regular beacon travel if available
        if not candidate_first and ENABLE_BEACON_MOVES:
            candidate_first = self._find_beacon_travel_move(board, player_parity)
        
        # PRIORITY 4: Final fallback to strategic movement
        if not candidate_first:
            candidate_first = self._find_strategic_move(board, player_parity)

        def move_step_cost(move: Action.Move, movement_index: int) -> int:
            """Compute stamina cost for a movement step given its index (1-based).
            First move is free; extra moves cost EXTRA_MOVE_COST * (movement_index-1).
            Additional costs: ERASE_STEP_EXTRA_COST for ERASE, BEACON_COST for placing a beacon.
            """
            cost = 0
            # extra-move cost applies only for second+ movement steps
            if movement_index >= 2:
                cost += GameConstants.EXTRA_MOVE_COST * (movement_index - 1)
            # ERASE per-step extra cost
            if move.move_type == MoveType.ERASE:
                cost += getattr(GameConstants, "ERASE_STEP_EXTRA_COST", 0)
            # beacon placement cost
            if getattr(move, "place_beacon", False):
                cost += getattr(GameConstants, "BEACON_COST", 0)
            return cost

        # Helper to try append a movement if affordable
        def try_append_move(move: Optional[Action.Move]) -> bool:
            nonlocal simulated_stamina, simulated_pos, movement_count
            if not move:
                return False
            movement_count += 1
            cost = move_step_cost(move, movement_count)
            if simulated_stamina >= cost:
                simulated_stamina -= cost
                actions.append(move)
                if move.move_type == MoveType.REGULAR and move.direction:
                    simulated_pos = simulated_pos + move.direction
                return True
            # if not affordable, rollback movement_count
            movement_count -= 1
            return False

        # First move - guarantee at least one movement in the sequence
        if candidate_first:
            try_append_move(candidate_first)
        else:
            # No candidate found, add a fallback safe move to guarantee a movement
            fallback_move = self._get_random_safe_move(board, player_parity)
            if fallback_move:
                try_append_move(fallback_move)

        # Attempt up to two more moves from simulated positions
        if movement_count >= 1:
            move2 = self._find_strategic_move_from_position(board, player_parity, simulated_pos)
            # avoid duplicate beacon travel to same dest
            if move2 and isinstance(candidate_first, Action.Move) and candidate_first.move_type == MoveType.BEACON_TRAVEL and move2.move_type == MoveType.BEACON_TRAVEL and candidate_first.beacon_target == move2.beacon_target:
                move2 = None
            if move2:
                try_append_move(move2)

        if movement_count >= 2:
            move3 = self._find_strategic_move_from_position(board, player_parity, simulated_pos)
            # avoid repeating beacon destinations
            existing_targets = [a.beacon_target for a in actions if isinstance(a, Action.Move) and a.move_type == MoveType.BEACON_TRAVEL]
            if move3 and move3.move_type == MoveType.BEACON_TRAVEL and move3.beacon_target in existing_targets:
                move3 = None
            if move3:
                try_append_move(move3)

        # If we have built any actions, choose how many to return but ensure we
        # never return more than we've appended (all appended are already affordable)
        if actions:
            num_moves_to_return = random.randint(1, len(actions))

            # Single-move behavior respects the SINGLE_MOVE_IS_PAINT_ONLY flag
            if num_moves_to_return == 1:
                if SINGLE_MOVE_IS_PAINT_ONLY:
                    # prefer returning a paint action if we have one
                    paint_actions = [a for a in actions if isinstance(a, Action.Paint)]
                    if paint_actions:
                        if PRIORITIZE_STAMINA_RESET:
                            self.turns_since_beacon_used += 1
                        return [paint_actions[0]]
                    # otherwise return a movement (first movement is free)
                    move_actions = [a for a in actions if isinstance(a, Action.Move)]
                    if move_actions:
                        if PRIORITIZE_STAMINA_RESET:
                            self.turns_since_beacon_used += 1
                        return [move_actions[0]]
                    if PRIORITIZE_STAMINA_RESET:
                        self.turns_since_beacon_used += 1
                    return [self._get_random_safe_move(board, player_parity)]
                else:
                    # movement-only single-move: MUST return a movement
                    move_actions = [a for a in actions if isinstance(a, Action.Move)]
                    if move_actions:
                        if PRIORITIZE_STAMINA_RESET:
                            self.turns_since_beacon_used += 1
                        return [move_actions[0]]
                    # No movement in actions, return a safe move instead
                    if PRIORITIZE_STAMINA_RESET:
                        self.turns_since_beacon_used += 1
                    return [self._get_random_safe_move(board, player_parity)]
            else:
                result_actions = actions[:num_moves_to_return]
                # Ensure at least one movement in multi-step result
                move_actions = [a for a in result_actions if isinstance(a, Action.Move)]
                if not move_actions:
                    # No movement in sliced actions, add one
                    move = next((a for a in actions if isinstance(a, Action.Move)), None)
                    if move:
                        result_actions.append(move)
                    else:
                        result_actions.append(self._get_random_safe_move(board, player_parity))
                if PRIORITIZE_STAMINA_RESET:
                    self.turns_since_beacon_used += 1
                return result_actions

        # Fallback: no planned actions, return a safe random move
        if PRIORITIZE_STAMINA_RESET:
            self.turns_since_beacon_used += 1
        return self._get_random_safe_move(board, player_parity)



    def _find_best_paint_target(self, board: Board, player_parity: int) -> Optional[Location]:
        """
        Find the best square to paint within range.
        Priority: Convert neutral/weak squares to owned (maximize paint value).
        Uses Manhattan distance for range checking.
        """
        player = board.get_player(player_parity)
        opponent_parity = Parity.get_opponent_parity(player_parity)
        candidates = []
    
        for dr in range(-GameConstants.PAINT_RANGE, GameConstants.PAINT_RANGE + 1):
            for dc in range(-GameConstants.PAINT_RANGE, GameConstants.PAINT_RANGE + 1):
                if dr == 0 and dc == 0:
                    continue
                
                manhattan_dist = abs(dr) + abs(dc)
                if manhattan_dist > GameConstants.PAINT_RANGE:
                    continue
            
                target_loc = Location(player.loc.r + dr, player.loc.c + dc)
                if board.oob(target_loc):
                    continue
            
                cell = board.cells[target_loc.r][target_loc.c]
                
                if cell.is_wall:
                    continue
                
                if cell.beacon_parity == player_parity:
                    continue

                if cell.beacon_parity == opponent_parity and cell.paint_value == 0:
                    score = 150
                    if manhattan_dist == 1:
                        score += 5
                    candidates.append((target_loc, score))
                    continue

                if cell.beacon_parity != 0:
                    continue

                if cell.owner_parity == player_parity or cell.owner_parity == 0:
                    paint_strength = abs(cell.paint_value)
                    score = GameConstants.MAX_PAINT_VALUE - paint_strength
                    if cell.owner_parity == 0 or cell.paint_value == 0:
                        score += 100
                    if manhattan_dist == 1:
                        score += 5
                    candidates.append((target_loc, score))
    
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
    
        return None

    def _find_best_hill_to_control(self, board: Board, player_parity: int) -> Optional[Tuple[int, Location]]:
        """
        Find the best hill to control and return (hill_id, beacon_cell_location).
        Prioritizes hills that are:
        1. Not yet controlled by us
        2. Not strongly controlled by opponent
        3. Close to our position
        
        Returns (hill_id, beacon_location) tuple or None if no suitable hill found.
        """
        if not board.hills or len(board.hills) == 0:
            return None
        
        player = board.get_player(player_parity)
        opponent_parity = Parity.get_opponent_parity(player_parity)
        
        best_hill = None
        best_score = -999
        best_beacon_cell = None
        
        for hill_id, hill in board.hills.items():
            # Skip hills we already control fully
            if hill.controller_parity == player_parity:
                continue
            
            # Skip hills strongly controlled by opponent (too costly to take)
            if hill.controller_parity == opponent_parity:
                continue
            
            hill_cells = hill.cells
            if len(hill_cells) == 0:
                continue
            
            # Find cells in this hill that are closest to player and not walls
            closest_cell = None
            closest_dist = float('inf')
            cells_we_own_count = 0
            
            for cell_loc in hill_cells:
                if board.oob(cell_loc):
                    continue
                cell = board.cells[cell_loc.r][cell_loc.c]
                if cell.is_wall:
                    continue
                
                dist = abs(player.loc.r - cell_loc.r) + abs(player.loc.c - cell_loc.c)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_cell = cell_loc
                
                if cell.owner_parity == player_parity:
                    cells_we_own_count += 1
            
            if closest_cell is None:
                continue
            
            # Score: prefer closer hills and hills with more cells we already own
            score = 100 - closest_dist + cells_we_own_count * 10
            
            if score > best_score:
                best_score = score
                best_hill = hill_id
                best_beacon_cell = closest_cell
        
        if best_hill is not None and best_beacon_cell is not None:
            return (best_hill, best_beacon_cell)
        
        return None

    def _generate_hill_control_actions(self, board: Board, player_parity: int, hill_control_info: Tuple[int, Location]) -> Optional[Iterable[Union[Action.Move, Action.Paint]]]:
        """
        Generate a sequence of moves and paints to control a hill.
        Strategy: Move toward a hill cell, place beacon on one cell, paint half the other cells.
        
        Returns an iterable of Actions or None if not possible.
        """
        if not hill_control_info:
            return None
        
        hill_id, beacon_cell = hill_control_info
        
        if not board.hills or hill_id not in board.hills:
            return None
        
        hill = board.hills[hill_id]
        player = board.get_player(player_parity)
        
        actions = []
        current_pos = player.loc
        
        # Collect all valid hill cells
        valid_hill_cells = []
        for cell_loc in hill.cells:
            if board.oob(cell_loc):
                continue
            cell = board.cells[cell_loc.r][cell_loc.c]
            if not cell.is_wall:
                valid_hill_cells.append(cell_loc)
        
        if len(valid_hill_cells) == 0:
            return None
        
        # Only generate moves if we're not already at the beacon cell
        if current_pos != beacon_cell:
            # Generate up to 2 moves to get closer to beacon cell
            for _ in range(2):
                if current_pos == beacon_cell:
                    break
                
                best_move = None
                best_dist = abs(current_pos.r - beacon_cell.r) + abs(current_pos.c - beacon_cell.c)
                best_next_pos = current_pos
                
                for direction in Direction.cardinals():
                    next_loc = current_pos + direction
                    if board.oob(next_loc):
                        continue
                    cell = board.cells[next_loc.r][next_loc.c]
                    if cell.is_wall:
                        continue
                    
                    dist = abs(next_loc.r - beacon_cell.r) + abs(next_loc.c - beacon_cell.c)
                    if dist < best_dist:
                        best_dist = dist
                        best_move = Action.Move(direction, place_beacon=(next_loc == beacon_cell))
                        best_next_pos = next_loc
                
                if best_move is None:
                    break
                
                actions.append(best_move)
                current_pos = best_next_pos
        
        # Paint half of the hill cells within paint range (excluding beacon cell)
        cells_to_paint = []
        for cell_loc in valid_hill_cells:
            if cell_loc == beacon_cell or cell_loc == current_pos:
                continue
            
            # Check if within paint range
            dist = abs(current_pos.r - cell_loc.r) + abs(current_pos.c - cell_loc.c)
            if dist <= GameConstants.PAINT_RANGE:
                cells_to_paint.append(cell_loc)
        
        # Paint up to half of the hill cells
        target_paint_count = max(1, len(valid_hill_cells) // 2)
        
        for i, paint_loc in enumerate(cells_to_paint):
            if i >= target_paint_count:
                break
            actions.append(Action.Paint(paint_loc))
        
        return actions if actions else None


    def _find_strategic_move(self, board: Board, player_parity: int) -> Optional[Action.Move]:
        """
        Find a strategic move - just pick a random valid cardinal direction.
        Avoids oscillation by not overthinking.
        """
        player = board.get_player(player_parity)
        opponent_parity = Parity.get_opponent_parity(player_parity)
        available = []
        
        for direction in Direction.cardinals():
            next_loc = player.loc + direction
            
            if board.oob(next_loc):
                continue
            
            cell = board.cells[next_loc.r][next_loc.c]
            if cell.is_wall:
                continue

            should_place_beacon = self._should_place_beacon_at(board, player_parity, next_loc)
            move_type = MoveType.REGULAR
            
            if cell.beacon_parity == opponent_parity and player.stamina >= GameConstants.ERASE_STEP_EXTRA_COST:
                move_type = MoveType.ERASE
            elif cell.paint_value * player_parity < 0 and player.stamina >= GameConstants.ERASE_STEP_EXTRA_COST and random.random() < 0.2:
                move_type = MoveType.ERASE
            
            available.append(Action.Move(direction, move_type=move_type, place_beacon=should_place_beacon))
        
        return random.choice(available) if available else None

    def _find_strategic_move_from_position(self, board: Board, player_parity: int, from_pos: Location) -> Optional[Action.Move]:
        """
        Find a strategic move from a specific position (for chained moves).
        Used to generate move2, move3, etc. which need to be valid from the simulated position.
        
        If from_pos is on a friendly beacon, considers beacon travel to other friendly beacons first.
        """
        # If from_pos is on one of our beacons, consider beacon travel first
        cur_cell = board.cells[from_pos.r][from_pos.c]
        if ENABLE_BEACON_MOVES and cur_cell.beacon_parity == player_parity:
            # Find other friendly beacons to teleport to
            candidates: list[Location] = []
            for r in range(board.board_size.r):
                for c in range(board.board_size.c):
                    if r == from_pos.r and c == from_pos.c:
                        continue
                    cell = board.cells[r][c]
                    if cell.beacon_parity == player_parity:
                        candidates.append(Location(r, c))

            if candidates:
                dest = random.choice(candidates)
                return Action.Move(direction=None, move_type=MoveType.BEACON_TRAVEL, beacon_target=dest)

        # Not on a beacon, or no other beacons available - find a regular movement
        available = []
        opponent_parity = Parity.get_opponent_parity(player_parity)

        for direction in Direction.cardinals():
            next_loc = from_pos + direction
            
            if board.oob(next_loc):
                continue
            
            cell = board.cells[next_loc.r][next_loc.c]
            if cell.is_wall:
                continue

            player = board.get_player(player_parity)
            move_type = MoveType.REGULAR
            
            if cell.beacon_parity == opponent_parity and player.stamina >= GameConstants.ERASE_STEP_EXTRA_COST:
                move_type = MoveType.ERASE
            elif cell.paint_value * player_parity < 0 and player.stamina >= GameConstants.ERASE_STEP_EXTRA_COST and random.random() < 0.2:
                move_type = MoveType.ERASE

            available.append(Action.Move(direction, move_type=move_type, place_beacon=False))
        
        return random.choice(available) if available else None

    def _find_beacon_travel_move(
        self, board: Board, player_parity: int
    ) -> Optional[Action.Move]:
        """
        If our agent is currently standing on one of its own beacons and there
        exists another friendly beacon on the board, build a BEACON_TRAVEL move
        targeting that beacon. The destination beacon just needs to exist and be friendly;
        it will be destroyed by the engine if it has 0 paint or enemy paint after teleportation.
        
        Returns None if not on a beacon or no other beacons exist.
        """
        if not ENABLE_BEACON_MOVES:
            return None
            
        player = board.get_player(player_parity)
        cur_cell = board.cells[player.loc.r][player.loc.c]
        
        if cur_cell.beacon_parity != player_parity:
            return None

        # Find all other friendly beacons we can teleport to
        candidates: list[Location] = []
        for r in range(board.board_size.r):
            for c in range(board.board_size.c):
                if r == player.loc.r and c == player.loc.c:
                    continue
                cell = board.cells[r][c]
                if cell.beacon_parity == player_parity:
                    candidates.append(Location(r, c))

        if not candidates:
            return None

        dest = random.choice(candidates)
        return Action.Move(
            direction=None,
            move_type=MoveType.BEACON_TRAVEL,
            beacon_target=dest,
        )

    def _find_stamina_reset_beacon_move(self, board: Board, player_parity: int) -> Optional[Action.Move]:
        """
        If stamina needs to be reset and we're on a friendly beacon, try to teleport
        back to the last beacon we used (or a friendly beacon if no last beacon tracked).
        This is a high-priority move that happens before normal strategic moves and helps
        regenerate stamina on friendly territory.
        
        Returns a BEACON_TRAVEL move to reset stamina, or None if conditions aren't met.
        """
        if not PRIORITIZE_STAMINA_RESET or not ENABLE_BEACON_MOVES:
            return None
        
        player = board.get_player(player_parity)
        
        # Only teleport if we could benefit from stamina regeneration (below 75 stamina)
        if player.stamina >= 75:
            return None
        
        # Check if we're currently on a friendly beacon
        cur_cell = board.cells[player.loc.r][player.loc.c]
        if cur_cell.beacon_parity != player_parity:
            return None
        
        # Check beacon spam prevention - don't teleport too frequently
        if not ALLOW_BEACON_SPAM and self.turns_since_beacon_used < 3:
            return None
        
        # Find all other friendly beacons we can teleport to
        candidates: list[Location] = []
        for r in range(board.board_size.r):
            for c in range(board.board_size.c):
                if r == player.loc.r and c == player.loc.c:
                    continue
                cell = board.cells[r][c]
                if cell.beacon_parity == player_parity:
                    candidates.append(Location(r, c))
        
        if not candidates:
            return None
        
        # Prioritize the last beacon we used if it still exists
        dest = None
        if self.last_beacon_used and self.last_beacon_used in candidates:
            dest = self.last_beacon_used
        else:
            # Otherwise pick a random friendly beacon
            dest = random.choice(candidates)
        
        # Track this beacon usage
        self.last_beacon_used = dest
        self.turns_since_beacon_used = 0
        
        return Action.Move(
            direction=None,
            move_type=MoveType.BEACON_TRAVEL,
            beacon_target=dest,
        )

    def _should_place_beacon_at(self, board: Board, player_parity: int, target_loc: Location) -> bool:
        if not ENABLE_BEACON_MOVES:
            return False
            
        player = board.get_player(player_parity)
        opponent_parity = Parity.get_opponent_parity(player_parity)

        if player.stamina < GameConstants.BEACON_COST:
            return False
        
        target_cell = board.cells[target_loc.r][target_loc.c]
        
        # Can place beacon if:
        # 1. Your cell (owned by you) with no beacon, OR
        # 2. Enemy beacon (to destroy it)
        is_own_cell = target_cell.owner_parity == player_parity
        is_enemy_beacon = target_cell.beacon_parity == opponent_parity
        
        if not (is_own_cell or is_enemy_beacon):
            return False
        
        # Own cells need to be clear of beacons
        if is_own_cell and target_cell.beacon_parity != 0:
            return False
        
        # Check 2/3 rule: need 2/3 of valid cells (non-wall, non-OOB) to be friendly
        window_radius = GameConstants.BEACON_WINDOW_SIZE_P // 2
        friendly_count = 0
        valid_cells_count = 0
        
        for dr in range(-window_radius, window_radius + 1):
            for dc in range(-window_radius, window_radius + 1):
                check_loc = Location(target_loc.r + dr, target_loc.c + dc)
                if board.oob(check_loc):
                    continue
                cell = board.cells[check_loc.r][check_loc.c]
                if cell.is_wall:
                    continue
                valid_cells_count += 1
                if cell.owner_parity == player_parity:
                    friendly_count += 1
        
        # Use proportional calculation: friendly_count * P^2 >= Q * valid_cells_count
        # Where P = BEACON_WINDOW_SIZE_P (3) and Q = BEACON_REQUIREMENT_Q (6)
        return friendly_count * (GameConstants.BEACON_WINDOW_SIZE_P ** 2) >= GameConstants.BEACON_REQUIREMENT_Q * valid_cells_count

    def _find_opponent_beacon_location(self, board: Board, player_parity: int) -> Optional[Location]:
        """
        Find the closest opponent beacon on the board.
        
        Returns the opponent beacon location closest to the player, or None if none exist.
        """
        player = board.get_player(player_parity)
        opponent_parity = Parity.get_opponent_parity(player_parity)
        
        closest_beacon = None
        closest_distance = float('inf')
        
        for r in range(board.board_size.r):
            for c in range(board.board_size.c):
                cell = board.cells[r][c]
                if cell.beacon_parity == opponent_parity:
                    beacon_loc = Location(r, c)
                    distance = abs(player.loc.r - r) + abs(player.loc.c - c)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_beacon = beacon_loc
        
        return closest_beacon

    def _find_move_toward_opponent_beacon(self, board: Board, player_parity: int) -> Optional[Action.Move]:
        """
        Find a move that brings the player closer to an opponent beacon.
        If adjacent, uses ERASE to destroy the beacon's paint.
        
        Returns a Move action toward the opponent beacon, or None if no opponent beacons exist.
        """
        opponent_beacon = self._find_opponent_beacon_location(board, player_parity)
        if not opponent_beacon:
            return None
        
        player = board.get_player(player_parity)
        
        manhattan_dist_to_beacon = abs(player.loc.r - opponent_beacon.r) + abs(player.loc.c - opponent_beacon.c)
        
        if manhattan_dist_to_beacon == 1:
            if player.stamina >= GameConstants.ERASE_STEP_EXTRA_COST:
                dr = opponent_beacon.r - player.loc.r
                dc = opponent_beacon.c - player.loc.c
                
                if dr == -1 and dc == 0:
                    direction = Direction.UP
                elif dr == 1 and dc == 0:
                    direction = Direction.DOWN
                elif dr == 0 and dc == -1:
                    direction = Direction.LEFT
                elif dr == 0 and dc == 1:
                    direction = Direction.RIGHT
                else:
                    direction = Direction.UP
                
                return Action.Move(direction, move_type=MoveType.ERASE, place_beacon=False)
        
        best_move = None
        best_distance = manhattan_dist_to_beacon
        
        for direction in Direction.cardinals():
            next_loc = player.loc + direction
            
            if board.oob(next_loc):
                continue
            
            cell = board.cells[next_loc.r][next_loc.c]
            if cell.is_wall:
                continue
            
            distance_to_beacon = abs(next_loc.r - opponent_beacon.r) + abs(next_loc.c - opponent_beacon.c)
            
            # Prefer moves that get closer to the beacon
            if distance_to_beacon < best_distance:
                best_distance = distance_to_beacon
                best_move = Action.Move(direction, move_type=MoveType.REGULAR, place_beacon=False)
        
        return best_move
        
    def _find_move_to_friendly_territory(self, board: Board, player_parity: int) -> Optional[Action.Move]:
        """
        Find a move toward friendly-colored squares for stamina regeneration.
        """
        player = board.get_player(player_parity)
        best_move = None
        best_score = -999
    
        for direction in Direction.cardinals():
            next_loc = player.loc + direction
        
            if board.oob(next_loc):
                continue
        
            cell = board.cells[next_loc.r][next_loc.c]
            if cell.is_wall:
                continue
        
            score = 0
            if cell.owner_parity == player_parity:
                score = 10
            elif cell.owner_parity == 0:
                score = 5
        
            if score > best_score:
                best_score = score
                best_move = Action.Move(direction)
    
        return best_move


    def _get_random_safe_move(self, board: Board, player_parity: int) -> Action.Move:
        """
        Fallback: return a random valid move.
        """
        player = board.get_player(player_parity)
        available = []
    
        for direction in Direction.cardinals():
            next_loc = player.loc + direction
            if not board.oob(next_loc) and not board.cells[next_loc.r][next_loc.c].is_wall:
                available.append(Action.Move(direction))
    
        return random.choice(available) if available else Action.Move(Direction.UP)


    def _count_friendly_adjacent(self, board: Board, loc: Location, player_parity: int) -> int:
        """
        Count adjacent friendly-colored squares.
        """
        count = 0
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                neighbor = Location(loc.r + dr, loc.c + dc)
                if not board.oob(neighbor):
                    if board.cells[neighbor.r][neighbor.c].owner_parity == player_parity:
                        count += 1
        return count


    def _can_place_beacon(self, board: Board, player_parity: int) -> bool:
        """
        Check if conditions are met to place a beacon.
        """
        player = board.get_player(player_parity)
    
        if player.stamina < GameConstants.BEACON_COST:
            return False
    
    # Count friendly squares in beacon window
        window_radius = GameConstants.BEACON_WINDOW_SIZE_P // 2
        friendly_count = 0
    
        for dr in range(-window_radius, window_radius + 1):
            for dc in range(-window_radius, window_radius + 1):
                check_loc = Location(player.loc.r + dr, player.loc.c + dc)
                if not board.oob(check_loc):
                    if board.cells[check_loc.r][check_loc.c].owner_parity == player_parity:
                        friendly_count += 1
    
        return friendly_count >= GameConstants.BEACON_REQUIREMENT_Q


    def _calculate_extra_moves_affordable(self, stamina: int) -> int:
        """
        Calculate how many extra moves can be afforded with current stamina.
        First move is free, subsequent moves cost EXTRA_MOVE_COST * move_number.
        """
        moves = 0
        remaining = stamina
        move_num = 1
    
        while remaining >= GameConstants.EXTRA_MOVE_COST * move_num:
            remaining -= GameConstants.EXTRA_MOVE_COST * move_num
            moves += 1
            move_num += 1
    
        return min(moves, 3)  # Cap at 3 extra moves per turn to be safe	

    def _find_safe_extra_move(self, board: Board, player_parity: int, previous_move: Action.Move) -> Optional[Action.Move]:
        player = board.get_player(player_parity)
    
        available_moves = []
    
        for direction in Direction.cardinals():
                    # Can't paint yourself
                    if dr == 0 and dc == 0:
                        continue

                    # Check Manhattan distance
                    manhattan_dist = abs(dr) + abs(dc)
                    if manhattan_dist > GameConstants.PAINT_RANGE:
                        continue

                    target_loc = Location(player.loc.r + dr, player.loc.c + dc)
                    if board.oob(target_loc):
                        continue

                    cell = board.cells[target_loc.r][target_loc.c]

                    # Only paint squares we already own (engine requires owned target)
                    if cell.owner_parity == player_parity and abs(cell.paint_value) < GameConstants.MAX_PAINT_VALUE:
                        # Score: higher for weaker squares (easier to complete)
                        paint_strength = abs(cell.paint_value)
                        score = (GameConstants.MAX_PAINT_VALUE - paint_strength)
                        # Bonus for adjacent squares
                        if manhattan_dist == 1:
                            score += 5
                        candidates.append((target_loc, score))
        return None
    
    def commentate(self, board: Board, player_parity: int, time_left: Callable) -> str:
        """
        Allows for you to display a string at the end of the match on our online
        portal for your own statistics usage. Be careful, your opponents will be 
        able to see this as well.
        """
        return ""
        
