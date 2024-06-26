import logging
import os
import sys
from typing import Optional

import chess
import chess.polyglot

from sporkfish.board.board import Board
from sporkfish.configurable import Configurable


class OpeningBookConfig(Configurable):
    """
    Configuration class for an opening book.
    """

    def __init__(self, opening_book_path: Optional[str] = None):
        """
        Initialize an OpeningBookConfig instance.

        :param opening_book_path: Relative (to root directory) or absolute path to opening book binary. Defaults to None.
        :type config: Optional[str]
        """
        self.opening_book_path = opening_book_path


class OpeningBook:
    """Class for handling the opening book in chess engines."""

    def __init__(self, config: OpeningBookConfig = OpeningBookConfig()) -> None:
        """
        Initialize the OpeningBook instance.

        :param config: Opening book config. If not provided, the default opening book is used.
        :type config: OpeningBookConfig
        """
        self._config = config
        self._db = None
        if self._config.opening_book_path:
            self._db = self._load(self._resource_path(self._config.opening_book_path))
        else:
            logging.warning(
                "Skip loading opening book as the opening book binary path is not passed in configuration."
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
        self, opening_book_path: str
    ) -> Optional[chess.polyglot.MemoryMappedReader]:
        """
        Load the opening database from the specified path.

        :param opening_book_path: Path to the opening book file.
        :type opening_book_path: str

        :return: The opened opening database reader.
                 Returns None if the file is not found.
        :rtype: Optional[chess.polyglot.MemoryMappedReader]
        """

        try:
            r = chess.polyglot.open_reader(opening_book_path)
            logging.info(f"Opening book succesfully loaded from {opening_book_path}.")
            return r
        except FileNotFoundError as _:
            logging.warning(f"No opening book found at {opening_book_path}, skipping.")
            return None

    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Query the opening database for a given chess board position.

        :param board: The current chess board position.
        :type board: Board

        :return: The recommended move from the opening database.
                Returns None if no matching entry is found.
        :rtype: Optional[chess.Move]
        """

        try:
            if self._db:
                # We need to use a chess.Board() to be compatible with the opening book
                # This is a small performace hit but is miniscule compared to searching
                cboard = chess.Board()
                cboard.set_fen(board.fen())
                entry = self._db.find(cboard)
                return entry.move if entry else None
            else:
                return None
        except IndexError:
            return None
