from abc import ABC, abstractmethod

from ..board.board import Board


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
