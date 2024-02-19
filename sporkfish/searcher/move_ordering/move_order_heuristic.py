from abc import ABC, abstractmethod
from enum import Enum

import chess

from ...board.board import Board


class MoveOrderMode(Enum):
    MVV_LVA = "MVV_LVA"
    KILLER_MOVE = "KILLER_MOVE"


class MoveOrderHeuristic(ABC):
    @abstractmethod
    def evaluate(self, board: Board, move: chess.Move, depth: int) -> float:
        """
        Abstract method to evaluate the desirability of a move in a given board position.
        Higher values indicate more desirable moves.

        :param board: The current state of the chess board.
        :type board: Board
        :param move: The move to be evaluated.
        :type move: chess.Move
        :param depth: The current depth at which the move ordering is considered.
        :type depth: int
        :return: A floating-point value representing the evaluation of the move.
        :rtype: float
        """
        pass
