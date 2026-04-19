from typing import Dict, List, Optional

import chess

from sporkfish.board.board import Board
from sporkfish.searcher.move_ordering.history_heuristic import HistoryHeuristic
from sporkfish.searcher.move_ordering.killer_move_heuristic import KillerMoveHeuristic
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
)
from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic
from sporkfish.searcher.move_ordering.mvv_lva_heuristic import MvvLvaHeuristic


class CompositeHeuristic(
    MvvLvaHeuristic, KillerMoveHeuristic, HistoryHeuristic, MoveOrderHeuristic
):
    """
    Combines MVV-LVA, killer move and history heuristics into a single score.

    Each component is weighted by a configurable coefficient (default: 3 / 2 / 1).
    The combined score is used to sort moves before searching, with higher scores
    tried first.  Captures are scored by MVV-LVA only; quiet moves receive killer
    and history bonuses on top.

    The three sub-heuristics share a single ``is_capture`` call per move to avoid
    redundant board queries (previously responsible for 3x the hot-path overhead).
    """

    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        history_table: Dict[chess.Move, int],
        counter_move_table: Optional[Dict[chess.Move, chess.Move]],
        depth: int,
        move_order_config: MoveOrderConfig = MoveOrderConfig(),
    ) -> None:
        MvvLvaHeuristic.__init__(self, board)
        KillerMoveHeuristic.__init__(self, board, killer_moves, depth)
        HistoryHeuristic.__init__(self, board, history_table)
        MoveOrderHeuristic.__init__(self)

        # Pre-extract weights as plain floats so evaluate() uses direct float
        # multiplication instead of dict lookups keyed by MoveOrderMode enum.
        # The enum __hash__ call for each lookup was showing up as ~83k calls in profiling.
        self._w_mvv_lva = move_order_config.mvv_lva_weight
        self._w_killer = move_order_config.killer_moves_weight
        self._w_history = move_order_config.history_weight
        self._w_counter = move_order_config.counter_move_weight
        self._counter_move_table = (
            counter_move_table if counter_move_table is not None else {}
        )

    def evaluate(
        self,
        move: chess.Move,
    ) -> float:
        """
        Calculate composite heuristic, combining multiple move ordering strategies at once.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the composite evaluation of the move.
        :rtype: float
        """

        # Compute is_capture once and share it across all three sub-heuristics.
        # Previously each sub-heuristic called board.is_capture() independently,
        # costing 3x the ~62k is_capture calls seen in profiling.
        is_cap = self._board.is_capture(move)

        # MVV-LVA: reward captures by most-valuable-victim / least-valuable-aggressor.
        mvv_lva = 0.0
        if is_cap:
            captured_type = self._board.piece_type_at(move.to_square)
            moving_type = self._board.piece_type_at(move.from_square)
            if captured_type and moving_type:
                mvv_lva = (
                    self._w_mvv_lva
                    * MvvLvaHeuristic._MVV_LVA[captured_type - 1][moving_type - 1]
                )

        # Killer move and history heuristics only apply to quiet (non-capture) moves.
        if is_cap:
            return mvv_lva

        killer = self._w_killer * (1 if move in self._killer_moves[self._depth] else 0)
        history = self._w_history * self._history_table.get(move, 0)
        counter = 0.0
        if self._counter_move_table and self._board.move_stack:
            previous_move = self._board.move_stack[-1]
            if self._counter_move_table.get(previous_move) == move:
                counter = self._w_counter
        return mvv_lva + killer + history + counter
