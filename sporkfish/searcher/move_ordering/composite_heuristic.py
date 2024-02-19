from enum import IntEnum
from typing import List

import chess

from ...board.board import Board
from .killer_move_heuristic import KillerMoveHeuristic
from .mvv_lva_heuristic import MvvLvaHeuristic


# TODO: To be tuned later
# I'm personally not very big fan of letting thisbe configurable from config
# People can input whatever nonsensical values
# But perhaps it could be useful for testing when we first start out. TBD.
class CompositeHeuristicScore(IntEnum):
    KILLER_MOVE = 1
    MVV_LVA = 2


class CompositeHeuristic(MvvLvaHeuristic, KillerMoveHeuristic):
    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        depth: int,
    ) -> None:
        super(MvvLvaHeuristic, self).__init__(board)
        super(KillerMoveHeuristic, self).__init__(board, killer_moves, depth)

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate composite heuristic, combining multiple move ordering strategies at once.
        Simple aggregation for now, to be improved.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the composite evaluation of the move.
        :rtype: float
        """
        # TODO: this is using is_capture twice but lets leave that for later
        mvv_lva = CompositeHeuristicScore.MVV_LVA * MvvLvaHeuristic.evaluate(self, move)
        killer_move = (
            CompositeHeuristicScore.KILLER_MOVE
            * KillerMoveHeuristic.evaluate(self, move)
        )
        return mvv_lva + killer_move
