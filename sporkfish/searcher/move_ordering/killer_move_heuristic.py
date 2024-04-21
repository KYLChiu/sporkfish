from typing import List

import chess

from sporkfish.board.board import Board
from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic


class KillerMoveHeuristic(MoveOrderHeuristic):
    def __init__(
        self,
        board: Board,
        killer_moves: List[List[chess.Move]],
        depth: int,
    ) -> None:
        super().__init__()
        self._board = board
        self._killer_moves = killer_moves
        self._depth = depth

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate the killer move heuristic, i.e. if a move caused a beta cutoff
        in previous runs, it is stored and given a higher score on future move
        ordering evaluations.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the killer evaluation of the move.
        :rtype: float
        """
        return (
            1
            if move in self._killer_moves[self._depth]
            and not self._board.is_capture(move)
            else 0
        )
