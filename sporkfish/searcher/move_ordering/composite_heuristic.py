from typing import List

import chess

from ...configurable import Configurable

from ...board.board import Board
from .killer_move_heuristic import KillerMoveHeuristic
from .move_order_heuristic import MoveOrderHeuristic, MoveOrderMode
from .mvv_lva_heuristic import MvvLvaHeuristic


class MoveOrderConfig(Configurable):
    def __init__(self, mvv_lva_weight: float = 2.0, killer_move_weight: float = 1.0):
        self.mvv_lva_weight = mvv_lva_weight
        self.killer_move_weight = killer_move_weight


class CompositeHeuristic(MvvLvaHeuristic, KillerMoveHeuristic, MoveOrderHeuristic):
    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        depth: int,
        move_order_config: MoveOrderConfig = MoveOrderConfig(),
    ) -> None:
        MvvLvaHeuristic.__init__(self, board)
        KillerMoveHeuristic.__init__(self, board, killer_moves, depth)
        MoveOrderHeuristic.__init__(self)

        # TODO: this design may be slow, no need to reinitialize these weights for every instance
        # Recall this can be created for every node if not sidetracked by other components, like TT.
        self._move_order_config = move_order_config
        self._move_order_weights = {
            MoveOrderMode.MVV_LVA: self._move_order_config.mvv_lva_weight,
            MoveOrderMode.KILLER_MOVE: self._move_order_config.killer_move_weight,
        }

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
        # TODO: this is using is_capture twice but lets leave that for later
        # Simple aggregation for now, to be improved.
        mvv_lva = self._move_order_weights[
            MoveOrderMode.MVV_LVA
        ] * MvvLvaHeuristic.evaluate(self, move)
        killer_move = self._move_order_weights[
            MoveOrderMode.KILLER_MOVE
        ] * KillerMoveHeuristic.evaluate(self, move)
        return mvv_lva + killer_move
