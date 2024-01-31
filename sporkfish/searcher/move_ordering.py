from abc import ABC, abstractmethod
from typing import List

import chess

from ..board.board import Board


class MoveOrder(ABC):
    @abstractmethod
    def evaluate(self, board: Board, move: chess.Move) -> float:
        pass


class MvvLvaHeuristic(MoveOrder):
    def __init__(self) -> None:
        # Columns: attacker P, N, B, R, Q, K
        self._MVV_LVA = [
            [15, 14, 13, 12, 11, 10],  # victim P
            [25, 24, 23, 22, 21, 20],  # victim N
            [35, 34, 33, 32, 31, 30],  # victim B
            [45, 44, 43, 42, 41, 40],  # victim R
            [55, 54, 53, 52, 51, 50],  # victim Q
            [0, 0, 0, 0, 0, 0],  # victim K
        ]

    @property
    def mvv_lva_matrix(self) -> List[List[int]]:
        return self._MVV_LVA

    def evaluate(self, board: Board, move: chess.Move) -> float:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value
        for a capturing move based on the value of the captured piece.

        Parameters:
            board (Board): The chess board.
            move (chess.Move): The capturing move.

        Returns:
            int: The heuristic value of the capturing move based on the value of the captured piece.
        """

        captured_piece = board.piece_at(move.to_square)
        moving_piece = board.piece_at(move.from_square)

        if (
            captured_piece is not None
            and moving_piece is not None
            and board.is_capture(move)
        ):
            return self._MVV_LVA[captured_piece.piece_type - 1][
                moving_piece.piece_type - 1
            ]
        else:
            return 0
