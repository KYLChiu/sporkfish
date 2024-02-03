import logging
import os
import sys
from typing import Optional

import chess
import chess.syzygy

from .board.board import Board
from .configurable import Configurable


class EndgameTablebaseConfig(Configurable):
    """Configuration class for an endgame tablebase.

    Attributes:
        endgame_tablebase_path (Optional[str]): Relative (to root directory) or absolute path to endgame tablebase binary. Defaults to None.

    """

    def __init__(self, endgame_tablebase_path: Optional[str] = None):
        """
        Initialize an EndgameTablebaseConfig instance.

        Args:
            endgame_tablebase_path (Optional[str]): Relative (to root directory) or absolute path to endgame tablebase binary. Defaults to None.
        """
        self.endgame_tablebase_path = endgame_tablebase_path


class EndgameTablebase:
    """Class for handling the endgame tablebase in chess engines."""

    def __init__(self, config: EndgameTablebaseConfig = EndgameTablebaseConfig()) -> None:
        """
        Initialize the EndgameTablebase instance.

        :param config: Endgame tablebase config. If not provided, the default endgame tablebase is used.
        :type config: EndgameTablebaseConfig
        :return: None
        """
        self._config = config
        if self._config.endgame_tablebase_path:
            self._db = self._load(self._resource_path(self._config.endgame_tablebase_path))
        else:
            logging.warning(
                f"Skip loading endgame tablebase as the endgame tablebase binary path is not passed in configuration."
            )

    def _resource_path(self, relative_path: str) -> str:
        """
        Get the absolute path to a resource.

        :param relative_path: Relative path to the resource.
        :type relative_path: str
        :return: Absolute path to the resource.
        :rtype: str
        """
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _load(
        self, endgame_tablebase_path: str
    ) -> Optional[chess.syzygy.Tablebase]:
        """
        Load the endgame database from the specified path.

        :param endgame_tablebase_path: Path to the endgame tablebase directory.
        :type endgame_tablebase_path: str
        :return: The opened endgame database reader.
                 Returns None if the file is not found.
        :rtype: Optional[chess.syzygy.Tablebase]
        """

        try:
            r = chess.syzygy.open_tablebase (endgame_tablebase_path)
            logging.info(f"Endgame tablebase succesfully loaded from {endgame_tablebase_path}.")
            return r
        except FileNotFoundError as _:
            logging.warning(f"No endgame tablebase found at {endgame_tablebase_path}, skipping.")
            return None

    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Query the endgame database for a given chess board position.

        :param board: The current chess board position.
        :type board: Board
        :return: The recommended move from the endgame database.
                Returns None if no matching entry is found.
        :rtype: Optional[chess.Move]
        """

        try:
            if self._db:
                # We need to use a chess.Board() to be compatible with the endgame tablebase
                # This is a small performace hit but is miniscule compared to searching
                cboard = chess.Board()
                cboard.set_fen(board.fen())

                for move in cboard.legal_moves():
                    cboard.push_move(move)
                    wdl_score = self._db.probe_wdl(cboard)
                    if wdl_score > 0:
                        return move
                    cboard.pop()
                return None
            return None
        except chess.syzygy.MissingTableError:
            return None