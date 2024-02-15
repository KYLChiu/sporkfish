from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

import chess

from ..board.board import Board


class MoveOrderMode(Enum):
    # can make a separate config for move ordering
    MVV_LVA = "MVV_LVA"
    KILLER_MOVE = "KILLER_MOVE"


class MoveOrder(ABC):
    @abstractmethod
    def evaluate(self, board: Board, move: chess.Move, depth: int) -> float:
        """
        Abstract method to evaluate the desirability of a move in a given board position.
        Higher values indicate more desirable moves.

        :param board: The current state of the chess board.
        :type board: Board
        :param move: The move to be evaluated.
        :type move: chess.Move

        :return: A floating-point value representing the evaluation of the move.
        :rtype: float
        """
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

    def evaluate(self, board: Board, move: chess.Move, depth: int) -> float:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value
        for a capturing move based on the value of the captured piece.

        Parameters:
            board (Board): The chess board.
            move (chess.Move): The capturing move.

        Returns:
            int: The heuristic value of the capturing move based on the value of the captured piece.
        """

        if (
            board.is_capture(move)
            and (captured_piece := board.piece_at(move.to_square))
            and (moving_piece := board.piece_at(move.from_square))
        ):
            return self._MVV_LVA[captured_piece.piece_type - 1][
                moving_piece.piece_type - 1
            ]
        else:
            return 0


class KillerMoveHeuristic(MoveOrder):
    def __init__(self, max_depth: int) -> None:
        # Initialize a list to store up to two killer moves for each depth
        # Using a fixed size per depth for simplicity; could be dynamic based on actual usage
        self.killer_moves: List[List[Optional[chess.Move]]] = [
            [None, None] for _ in range(max_depth)
        ]

    def add_killer_move(self, move: chess.Move, depth: int) -> None:
        """
        Add a move to the killer moves list for a given depth, ensuring it's not already present.
        If the move is new, it replaces the oldest killer move.

        Parameters:
            move (chess.Move): The move to be added as a killer move.
            depth (int): The depth at which the move proved to be a killer move.
        """
        killers = self.killer_moves[depth]
        if move not in killers:
            # Shift the existing killer moves down and add the new one at the front
            killers.pop()
            killers.insert(0, move)

    def evaluate(self, board: Board, move: chess.Move, depth: int) -> float:
        killers = self.killer_moves[depth]
        if move in killers:
            return 100
        else:
            return 0

    @property
    def killer_moves_matrix(self) -> List[List[Optional[chess.Move]]]:
        return self.killer_moves
