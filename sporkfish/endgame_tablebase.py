import logging
import os
import sys
from enum import IntEnum, auto
from typing import Optional, Tuple

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
        self._db = None
        if self._config.endgame_tablebase_path:
            self._db = self._load(
                self._resource_path(self._config.endgame_tablebase_path)
            )
        else:
            logging.warning(
                "Skip loading endgame tablebase as the endgame tablebase directory path is not passed in configuration."
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
        Categorizes the Distance to Zeroing (DTZ) value into different categories.

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
        Compares two Distance to Zeroing (DTZ) values based on their categories.
        Returns the best resulting DTZ value, based on the condition of the category.
        For example, for the CURSED_LOSS category, we want to save our loss as quickly as possible.
        CURSED_LOSS values are negative, thus we want to pick the biggest one.

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
        # We want make the unconditional loss last as long as possible, in case they run out of time
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_LOSS:
            return min(dtz, best_dtz)
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_DRAW:
            return 0
        # We want to unconditionally win as quickly as possible
        elif category == EndgameTablebase.DTZCategory.UNCONDITIONAL_WIN:
            return min(dtz, best_dtz)
        # We want to extend our cursed win as much as possible, in case they run out of time
        elif category == EndgameTablebase.DTZCategory.CURSED_WIN:
            return max(dtz, best_dtz)
        else:
            raise TypeError(f"Invalid enum type '{category}' passed for DTZCategory")

    def _pick_move(
        self,
        category: DTZCategory,
        dtz: int,
        move: chess.Move,
        best_category: DTZCategory,
        best_dtz: int,
        best_move: Optional[chess.Move],
    ) -> Tuple[DTZCategory, int, Optional[chess.Move]]:
        """
        Picks the best move based on the category and DTZ score.

        Moves are first compared by their category, then their DTZ score within that category.
        If the category is more desirable than the rolling best category, then take the new move.
        If the category is equally desirable as the rolling best category,
        then pick the move based on the most desirable DTZ score (conditioned on the type of category).
        If the new best DTZ score is different than the current score, then take the new move.

        :param category: The category of the current move.
        :type category: DTZCategory
        :param dtz: The DTZ (Distance to Zeroing) value of the current move.
        :type dtz: int
        :param move: The move to consider.
        :type move: chess.Move
        :param best_category: The category of the best move so far.
        :type best_category: DTZCategory
        :param best_dtz: The DTZ value of the best move so far.
        :type best_dtz: int
        :param best_move: The best move so far.
        :type best_move: Optional[chess.Move]
        :return: A tuple containing the category, DTZ value, and move to pick.
        :rtype: Tuple[DTZCategory, int, Optional[chess.Move]]
        """
        if category > best_category:
            return category, dtz, move
        elif category == best_category:
            if self._compare_dtz(dtz, best_dtz, best_category) != best_dtz:
                return category, dtz, move
        return best_category, best_dtz, best_move

    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Query the endgame database for a given chess board position.
        It uses the Distance to Zeroing (DTZ) as metric.

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
            best_category, best_dtz, best_move = (
                EndgameTablebase.DTZCategory.UNCONDITIONAL_LOSS,
                -sys.maxsize,
                None,
            )
            for move in board.legal_moves:
                cboard.push(move)
                # Refer to https://python-chess.readthedocs.io/en/latest/syzygy.html
                # Probe the opponents DTZ, after our legal move.
                # Our DTZ is the inversion of that.
                # TODO: check if there any issues for rounding error
                # Note that we have to check for None, because:
                # a) we may not have the corresponding Syzygy tablebase file to our position,
                # b) Moreover the position may not exist within the Syzygy tablebase, see e.g.
                #    5k2/8/8/8/2B5/8/3B4/3K4 w - - 2 2, move=c4d8 doesn't exist in the tablebase.
                dtz = -opp_dtz if (opp_dtz := self._db.get_dtz(cboard)) else None
                cboard.pop()

                if not dtz:
                    continue

                category = self._categorize_dtz(dtz)
                best_category, best_dtz, best_move = self._pick_move(
                    category, dtz, move, best_category, best_dtz, best_move
                )

            return best_move

        return None
