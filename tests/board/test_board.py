import chess
import pytest

from sporkfish.board.board_factory import BoardFactory
from sporkfish.board.board_py_chess import BoardPyChess


class TestBoardPyChess:
    def test_board(self):
        board = BoardPyChess()
        board.push_uci("d2d4")
        assert chess.Move.from_uci("d2d4") not in [
            chess.Move.from_uci(move.uci()) for move in board.legal_moves
        ]
        board.pop()
        assert chess.Move.from_uci("d2d4") in [
            chess.Move.from_uci(move.uci()) for move in board.legal_moves
        ]


class TestBoardFactory:
    def test_unsupported_board_type_raises(self) -> None:
        with pytest.raises(
            TypeError, match="does not support the creation of board type"
        ):
            BoardFactory.create(int)
