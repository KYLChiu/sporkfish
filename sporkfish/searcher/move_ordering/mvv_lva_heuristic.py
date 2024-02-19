from typing import List

import chess

from ...board.board import Board
from .move_order_heuristic import MoveOrderHeuristic


class MvvLvaHeuristic(MoveOrderHeuristic):
    # Columns: attacker P, N, B, R, Q, K
    _MVV_LVA = [
        [15, 14, 13, 12, 11, 10],  # victim P
        [25, 24, 23, 22, 21, 20],  # victim N
        [35, 34, 33, 32, 31, 30],  # victim B
        [45, 44, 43, 42, 41, 40],  # victim R
        [55, 54, 53, 52, 51, 50],  # victim Q
        [0, 0, 0, 0, 0, 0],  # victim K
    ]

    def __init__(self, board: Board) -> None:
        self._board = board

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value
        for a capturing move based on the value of the captured piece.

        :param board: The current state of the chess board.
        :type board: Board
        :param move: The move to be evaluated.
        :type move: chess.Move
        :param depth: The current depth at which the move ordering is considered.
        :type depth: int
        :return: A floating-point value representing the MVV-LVA evaluation of the move.
        :rtype: float
        """

        if (
            self._board.is_capture(move)
            and (captured_piece := self._board.piece_at(move.to_square))
            and (moving_piece := self._board.piece_at(move.from_square))
        ):
            return MvvLvaHeuristic._MVV_LVA[captured_piece.piece_type - 1][
                moving_piece.piece_type - 1
            ]
        else:
            return 0
