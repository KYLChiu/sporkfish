from typing import Dict, List

import chess

from sporkfish.board.board import Board
from sporkfish.searcher.move_ordering.history_heuristic import HistoryHeuristic
from sporkfish.searcher.move_ordering.killer_move_heuristic import KillerMoveHeuristic
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
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

        # TODO: this design may be slow, no need to reinitialize these weights for every instance
        # Recall this can be created for every node if not sidetracked by other components, like TT.
        self._move_order_config = move_order_config
        self._move_order_weights = {
            MoveOrderMode.MVV_LVA: self._move_order_config.mvv_lva_weight,
            MoveOrderMode.KILLER_MOVE: self._move_order_config.killer_moves_weight,
            MoveOrderMode.HISTORY: self._move_order_config.history_weight,
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
        history = self._move_order_weights[
            MoveOrderMode.HISTORY
        ] * HistoryHeuristic.evaluate(self, move)
        return mvv_lva + killer_move + history
