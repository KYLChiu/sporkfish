from abc import ABC, abstractmethod
from typing import Dict
from ..board.board import Board
import chess


class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, board: Board) -> float:
        """
        Abstract method to evaluating a given board position.

        :param board: The current chess board position.
        :type board: Board
        :return: The evaluation score.
        :rtype: float
        """
        pass

    @abstractmethod
    def piece_values(self) -> Dict[chess.PieceType, float]:
        """
        Abstract method to return the piece values for the evaluator.

        :return: The piece values.
        :rtype: Dict[chess.PieceType, int]
        """
        pass

    @abstractmethod
    def delta(self) -> float:
        """
        Abstract method to return the delta threshold for futility pruning for the evaluator.

        :return: The delta.
        :rtype: float
        """
        pass
