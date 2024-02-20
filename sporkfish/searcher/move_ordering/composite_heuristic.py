from typing import List

import chess

from ...board.board import Board
from .killer_move_heuristic import KillerMoveHeuristic
from .move_order_heuristic import MoveOrderHeuristic, MoveOrderMode
from .mvv_lva_heuristic import MvvLvaHeuristic


class CompositeHeuristic(MvvLvaHeuristic, KillerMoveHeuristic, MoveOrderHeuristic):
    # TODO: To be tuned later
    # TODO: to be configured later on, issue #120
    _MOVE_ORDER_WEIGHTS = {
        MoveOrderMode.MVV_LVA: 2.0,
        MoveOrderMode.KILLER_MOVE: 1.0,
    }

    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        depth: int,
    ) -> None:
        MvvLvaHeuristic.__init__(self, board)
        KillerMoveHeuristic.__init__(self, board, killer_moves, depth)
        MoveOrderHeuristic.__init__(self)

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate composite heuristic, combining multiple move ordering strategies at once.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the composite evaluation of the move.
        :rtype: float
        """
        # TODO: this is using is_capture twice but lets leave that for later
        # Simple aggregation for now, to be improved.
        mvv_lva = CompositeHeuristic._MOVE_ORDER_WEIGHTS[
            MoveOrderMode.MVV_LVA
        ] * MvvLvaHeuristic.evaluate(self, move)
        killer_move = CompositeHeuristic._MOVE_ORDER_WEIGHTS[
            MoveOrderMode.KILLER_MOVE
        ] * KillerMoveHeuristic.evaluate(self, move)
        return mvv_lva + killer_move
