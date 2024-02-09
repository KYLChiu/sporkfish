import logging
import os
import sys
from enum import IntEnum, auto
from typing import Optional

import chess
import chess.syzygy

from .board.board import Board
from .configurable import Configurable


class EndgameTablebaseConfig(Configurable):
    """Configuration class for an endgame tablebase."""

    def __init__(self, endgame_tablebase_path: Optional[str] = None):
        """
        Initialize an EndgameTablebaseConfig instance.

        :param endgame_tablebase_path: Relative path (to root directory) to endgame tablebase folder. Defaults to None.
        :type endgame_tablebase_path: Optional[str]
        """
        self.endgame_tablebase_path = endgame_tablebase_path


class EndgameTablebase:
    """Class for handling the endgame tablebase in chess engines."""

    class DTZCategory(IntEnum):
        """
        Represents the different types of DTZ moves.
        The order represents the desirability in ascending order.
        """

        UNCONDITIONAL_LOSS = auto()
        CURSED_LOSS = auto()
        UNCONDITIONAL_DRAW = auto()
        CURSED_WIN = auto()
        UNCONDITIONAL_WIN = auto()

    def __init__(
        self, config: EndgameTablebaseConfig = EndgameTablebaseConfig()
    ) -> None:
        """
        Initialize the EndgameTablebase instance.

        :param config: Endgame tablebase config. If not provided, the default endgame tablebase is used.
        :type config: EndgameTablebaseConfig
        :return: None
        """
        self._config = config
        if self._config.endgame_tablebase_path:
            self._db = self._load(
                self._resource_path(self._config.endgame_tablebase_path)
            )
        else:
            logging.warning(
                "Skip loading endgame tablebase as the endgame tablebase binary path is not passed in configuration."
            )

    def _resource_path(self, relative_to_absolute_path: str) -> str:
        """
        Get the absolute path to a resource.

        :param relative_to_absolute_path: Relative path to the resource.
        :type relative_to_absolute_path: str
        :return: Absolute path to the resource.
        :rtype: str
        """
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_to_absolute_path)

    def _load(self, endgame_tablebase_path: str) -> Optional[chess.syzygy.Tablebase]:
        """
        Load the endgame database from the specified path.

        :param endgame_tablebase_path: Path to the endgame tablebase directory.
        :type endgame_tablebase_path: str
        :return: The opened endgame database reader.
                 Returns None if the file is not found.
        :rtype: Optional[chess.syzygy.Tablebase]
        """

        try:
            r = chess.syzygy.open_tablebase(endgame_tablebase_path)
            logging.info(
                f"Endgame tablebase succesfully loaded from {endgame_tablebase_path}."
            )
            return r
        except FileNotFoundError as _:
            logging.warning(
                f"No endgame tablebase found at {endgame_tablebase_path}, skipping."
            )
            return None

    def _should_query(self, board: Board, max_syzygy_size: int = 6) -> bool:
        """
        Determine whether to query the endgame tablebase based on the number of pieces on the board.

        :param board: The current state of the chess board.
        :type board: chess.Board
        :param max_syzygy_size: The maximum number of pieces beyond which the endgame tablebase should not be queried, defaults to 6
        :type max_syzygy_size: int

        :return: True if the endgame tablebase should be queried, False otherwise
        :rtype: bool
        """
        piece_count = 0
        for square in chess.SQUARES:
            if board.piece_at(square):
                piece_count += 1
            if piece_count > max_syzygy_size:
                return False
        return True

    def _categorize_dtz(self, dtz: int) -> "EndgameTablebase.DTZCategory":
        """
        Categorizes the DTZ (Distance-to-Zero) value into different categories.

        :param dtz: The DTZ value to categorize, from our perspective.
        :type dtz: int
        :return: The category of the DTZ value.
        :rtype: EndgameTablebase.DTZCategory
        """
        assert isinstance(
            dtz, int
        ), f"Expected DTZ to be of type int but got {type(dtz).__name__}."
        if dtz < -100:
            return EndgameTablebase.DTZCategory.CURSED_LOSS
        elif -100 <= dtz <= -1:
            return EndgameTablebase.DTZCategory.UNCONDITIONAL_LOSS
        elif dtz == 0:
            return EndgameTablebase.DTZCategory.UNCONDITIONAL_DRAW
        elif 1 <= dtz <= 100:
            return EndgameTablebase.DTZCategory.UNCONDITIONAL_WIN
        else:
            return EndgameTablebase.DTZCategory.CURSED_WIN

    def _compare_dtz(self, dtz: int, best_dtz: int, category: DTZCategory) -> int:
        """
        Compares two DTZ (Distance-to-Zero) values based on their categories.

        :param dtz: The DTZ value to compare.
        :type dtz: int
        :param best_dtz: The best DTZ value so far.
        :type best_dtz: int
        :param category: The category of the DTZ value.
        :type category: EndgameTablebase.DTZCategory
        :return: The best resulting DTZ value, based on condition of the category.
        :rtype: int
        """
        # We want to save our cursed loss as quickly as possible
        if category == EndgameTablebase.DTZCategory.CURSED_LOSS:
            return max(dtz, best_dtz)
        # We want make the unconditional last as long as possible, in case they run out of time
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_LOSS:
            return min(dtz, best_dtz)
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_DRAW:
            return 0
        # We want to unconditionally win as quickly as possible
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_WIN:
            return min(dtz, best_dtz)
        # We want to extend our cursed win as much as possible, in case they run out of time
        else:
            return max(dtz, best_dtz)

    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Query the endgame database for a given chess board position.
        It uses the Depth to Zero (DTZ) as metric.

        :param board: The current chess board position.
        :type board: Board
        :return: The recommended move from the endgame database.
                Returns None if no matching entry is found.
        :rtype: Optional[chess.Move]
        """

        if self._db and self._should_query(board):
            # We need to use a chess.Board() to be compatible with the endgame tablebase
            # This is a small performace hit but is miniscule compared to searching
            cboard = chess.Board()
            cboard.set_fen(board.fen())
            best_move = None
            best_dtz = -sys.maxsize
            best_category = EndgameTablebase.DTZCategory.UNCONDITIONAL_LOSS
            for move in board.legal_moves:
                cboard.push(move)
                # Refer to https://python-chess.readthedocs.io/en/latest/syzygy.html
                # Invert the dtz as we are looking from the perspective of the opponent
                dtz = -opp_dtz if (opp_dtz := self._db.get_dtz(cboard)) else None
                cboard.pop()

                if not dtz:
                    continue

                category = self._categorize_dtz(dtz)
                if category > best_category:
                    best_dtz = dtz
                    best_move = move
                elif category == best_category:
                    if self._compare_dtz(dtz, best_dtz, best_category) != best_dtz:
                        best_dtz = dtz
                        best_move = move

            return best_move

        return None
