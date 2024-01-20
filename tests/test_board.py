from sporkfish.board import BLACK, KNIGHT, PAWN, WHITE
from sporkfish.board.board_py_chess import BoardPyChess
from sporkfish.board.move import Move
from sporkfish.board.piece import Piece


class TestPiece:
    def test_piece_hash_white_knight(self):
        p = Piece(KNIGHT, WHITE)
        assert hash(p) == 1

    def test_piece_hash_black_pawn(self):
        p = Piece(PAWN, BLACK)
        assert hash(p) == 6

    def test_eq(self):
        p = Piece(PAWN, BLACK)
        p2 = Piece(PAWN, BLACK)
        p3 = Piece(PAWN, WHITE)
        k = Piece(KNIGHT, BLACK)
        assert p == p2
        assert p != p3
        assert p != k


class TestMove:
    def test_move(self):
        move = Move.from_uci("a1b1")
        assert move.from_square == 0
        assert move.to_square == 1
        assert move.promotion is None


class TestBoardPyChess:
    def test_board(self):
        board = BoardPyChess()
        board.push_uci("d2d4")
        assert Move.from_uci("d2d4") not in [
            Move.from_uci(move.uci()) for move in board.legal_moves
        ]
        board.pop()
        assert Move.from_uci("d2d4") in [
            Move.from_uci(move.uci()) for move in board.legal_moves
        ]
