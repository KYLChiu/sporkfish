from abc import ABC, abstractmethod

import chess


class MoveOrderHeuristic(ABC):
    @abstractmethod
    def evaluate(self, move: chess.Move) -> float:
        """
        Abstract method to evaluate the desirability of a move in a given board position.
        Higher values indicate more desirable moves.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the evaluation of the move.
        :rtype: float
        """
        pass
