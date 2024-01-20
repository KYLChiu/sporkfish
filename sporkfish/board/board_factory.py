from typing import Type

from .board import Board
from .board_py_chess import BoardPyChess


class BoardFactory:
    """
    Factory class for creating instances of different board types.
    """

    @staticmethod
    def create(board_type: Type) -> Board:
        """
        Create an instance of the specified board type.

        :param board_type: The type of the board to create.
        :type board_type: Type
        :return: An instance of the specified board type.
        :rtype: Board
        :raises TypeError: If the specified board type is not supported by BoardFactory.
        """
        if board_type is BoardPyChess:
            return BoardPyChess()
        raise TypeError(
            f"BoardFactory does not support the creation of board type {type(board_type).__name__}."
        )
