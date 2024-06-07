from abc import ABC, abstractmethod
from typing import Optional

import chess

from sporkfish.board.board import Board


class EndgameTablebase(ABC):
    """
    Abstract base class for handling the endgame tablebase in chess engines.

    :method query(board: Board) -> Optional[chess.Move]: Abstract method to query the endgame tablebase.
    """

    @abstractmethod
    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Abstract method to query the endgame tablebase.

        :param board: The current state of the chess board.
        :type board: Board
        :return: The best move according to the tablebase, or None if no move is found.
        :rtype: Optional[chess.Move]
        """
        pass
