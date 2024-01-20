import chess

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
