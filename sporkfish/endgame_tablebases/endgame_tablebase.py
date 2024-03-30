from abc import ABC, abstractmethod
from typing import Optional

import chess

from sporkfish.board.board import Board


class EndgameTablebase(ABC):
    """Class for handling the endgame tablebase in chess engines."""

    @abstractmethod
    def query(self, board: Board) -> Optional[chess.Move]:
        pass
