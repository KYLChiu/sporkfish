from abc import ABC, abstractmethod
from enum import Enum

import chess


class MoveOrderMode(Enum):
    MVV_LVA = "MVV_LVA"
    KILLER_MOVE = "KILLER_MOVE"


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
