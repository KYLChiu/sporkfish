from typing import Optional
import chess
import chess.polyglot
import sys
import os
import logging
from .configurable import Configurable


class OpeningBookConfig(Configurable):
    def __init__(self, opening_book_path: Optional[str] = None):
        self.opening_book_path = opening_book_path


class OpeningBook:
    """Class for handling the opening book in chess engines."""

    def __init__(self, config: OpeningBookConfig = OpeningBookConfig()) -> None:
        """
        Initialize the OpeningBook instance.

        :param opening_book_path: Path to the opening book file.
                                 If not provided, a default path is used.
        :type opening_book_path: Optional[str]
        :return: None
        """
        self._config = config
        self._db = self._load(
            self._config.opening_book_path or self._resource_path("data/opening.bin")
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
        :rtype: chess.polyglot.MemoryMappedReader
        """

        try:
            r = chess.polyglot.open_reader(opening_book_path)
            logging.info(f"Opening book succesfully loaded from {opening_book_path}.")
            return r
        except FileNotFoundError as _:
            logging.warn(f"No opening book found at {opening_book_path}, skipping.")
            return None

    def query(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Query the opening database for a given chess board position.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The recommended move from the opening database.
                Returns None if no matching entry is found.
        :rtype: Optional[chess.Move]
        """

        try:
            if self._db:
                entry = self._db.find(board)
                return entry.move if entry else None
            else:
                return None
        except IndexError:
            return None
