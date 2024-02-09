import logging
import os
import random
import sys
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
        # TODO: configure as part of config later on
        random.seed(1)
        self.endgame_tablebase_path = endgame_tablebase_path


class EndgameTablebase:
    """Class for handling the endgame tablebase in chess engines."""

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

        try:
            if self._db:
                if not self._should_query(board):
                    return None

                # We need to use a chess.Board() to be compatible with the endgame tablebase
                # This is a small performace hit but is miniscule compared to searching
                cboard = chess.Board()
                cboard.set_fen(board.fen())
                dtz_scores = []
                legal_moves = list(cboard.legal_moves)
                for move in legal_moves:
                    cboard.push(move)
                    # https://python-chess.readthedocs.io/en/latest/syzygy.html
                    dtz = self._db.probe_dtz(cboard)
                    # We only handle unconditional "wins" (including zeroing) at the moment
                    # This is equivalent to unconditional losses for the opponent
                    # TODO: try to draw a cursed win?
                    # TODO: try to save a cursed loss?
                    dtz_scores.append(dtz if -100 <= dtz <= -1 else float("-inf"))
                    cboard.pop()
                # The least negative number is the one closest to losing for the opponent
                # This is valid as all scores are clamped to float("-inf") including potential positive scores
                best_dtz_idx = dtz_scores.index(max(dtz_scores))
                best_dtz = dtz_scores[best_dtz_idx]
                return legal_moves[best_dtz_idx] if best_dtz != float("-inf") else None
            return None
        except chess.syzygy.MissingTableError:
            return None
