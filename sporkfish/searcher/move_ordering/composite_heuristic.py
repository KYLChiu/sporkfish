from typing import Dict, List

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
    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        history_table: Dict[chess.Move, int],
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
        # costing 3× the ~62k is_capture calls seen in profiling.
        is_cap = self._board.is_capture(move)

        # MVV-LVA: reward captures by most-valuable-victim / least-valuable-aggressor.
        mvv_lva = 0.0
        if (
            is_cap
            and (captured_piece := self._board.piece_at(move.to_square))
            and (moving_piece := self._board.piece_at(move.from_square))
        ):
            mvv_lva = (
                self._w_mvv_lva
                * MvvLvaHeuristic._MVV_LVA[captured_piece.piece_type - 1][
                    moving_piece.piece_type - 1
                ]
            )

        # Killer move and history heuristics only apply to quiet (non-capture) moves.
        if is_cap:
            return mvv_lva

        killer = self._w_killer * (1 if move in self._killer_moves[self._depth] else 0)
        history = self._w_history * self._history_table.get(move, 0)
        return mvv_lva + killer + history
