from typing import Optional
import chess
import chess.polyglot
import sys
import os


class OpeningBook:
    """Class for handling the opening book in chess engines."""

    def __init__(self, opening_book_path: Optional[str] = None):
        """
        Initialize the OpeningBook instance.

        :param opening_book_path: Path to the opening book file.
                                 If not provided, a default path is used.
        :type opening_book_path: Optional[str]
        :return: None
        """

        self._opening_book_path = opening_book_path or self._resource_path(
            "data/opening.bin"
        )

    def _resource_path(self, relative_path: str):
        """
        Get the absolute path to a resource.

        :param relative_path: Relative path to the resource.
        :type relative_path: str
        :return: Absolute path to the resource.
        :rtype: str
        """

        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            # In a normal Python environment, use the original path
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _load(self, opening_book_path):
        """
        Load the opening database from the specified path.

        :param opening_book_path: Path to the opening book file.
        :type opening_book_path: str
        :return: The opened opening database reader.
                 Returns None if the file is not found.
        :rtype: chess.polyglot.MemoryMappedReader
        """

        try:
            return chess.polyglot.open_reader(opening_book_path)
        except FileNotFoundError as _:
            return None

    def query(self, board: chess.Board):
        """
        Query the opening database for a given chess board position.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The recommended move from the opening database.
                Returns None if no matching entry is found or an error occurs.
        :rtype: Optional[chess.Move]
        """

        try:
            db = self._load(self._opening_book_path)
            if db:
                with db:
                    entry = db.find(board)
                    return entry.move if entry else None
        except Exception as _:
            return None
