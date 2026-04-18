from abc import ABC, abstractmethod
from typing import Dict

import chess

from sporkfish.board.board import Board


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

    def on_push(self, board: Board, move: chess.Move) -> None:
        """
        Called immediately *before* a move is pushed onto the board.

        Override in stateful evaluators (e.g. incremental PeSTO) to update
        cached scores.  The default implementation is a no-op so that simple
        evaluators require no changes.
        """
        pass

    def on_pop(self) -> None:
        """
        Called immediately *after* a move is popped from the board.

        Override in stateful evaluators to restore cached scores.
        The default implementation is a no-op.
        """
        pass

    def init_from_board(self, board: Board) -> None:
        """
        Initialise any cached state from a fresh board position.

        Called once at the start of each search iteration (after deepcopy).
        Override in stateful evaluators.  The default implementation is a no-op.
        """
        pass
