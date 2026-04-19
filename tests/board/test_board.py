import copy

import chess
import pytest

from sporkfish.board.board_bitboard import BoardBitboard
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
    def test_bitboard_board_type_is_supported(self) -> None:
        board = BoardFactory.create(BoardBitboard)
        assert isinstance(board, BoardBitboard)

    def test_unsupported_board_type_raises(self) -> None:
        with pytest.raises(
            TypeError, match="does not support the creation of board type"
        ):
            BoardFactory.create(int)


class TestBoardBitboard:
    @staticmethod
    def _assert_snapshot_consistent(board: BoardBitboard) -> None:
        snapshot = board.piece_bitboards()
        assert snapshot.pawns == int(board.pawns)
        assert snapshot.knights == int(board.knights)
        assert snapshot.bishops == int(board.bishops)
        assert snapshot.rooks == int(board.rooks)
        assert snapshot.queens == int(board.queens)
        assert snapshot.kings == int(board.kings)
        assert snapshot.white_occ == int(board.occupied_co[chess.WHITE])
        assert snapshot.black_occ == int(board.occupied_co[chess.BLACK])
        assert snapshot.all_occ == int(board.occupied)

    def test_cache_restores_after_push_pop(self) -> None:
        board = BoardBitboard()
        start_bb = board.piece_bitboards()

        board.push_uci("e2e4")
        board.push_uci("c7c5")

        board.pop()
        board.pop()

        assert board.piece_bitboards() == start_bb

    def test_cache_resets_after_reset(self) -> None:
        board = BoardBitboard()
        board.push_uci("d2d4")
        board.push_uci("d7d5")

        board.reset()
        start = BoardBitboard()

        assert board.piece_bitboards() == start.piece_bitboards()

    def test_snapshot_consistency_en_passant(self) -> None:
        board = BoardBitboard()
        for uci in ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"]:
            board.push_uci(uci)
            self._assert_snapshot_consistent(board)

    def test_snapshot_consistency_promotion(self) -> None:
        board = BoardBitboard("8/P7/8/8/8/8/8/k6K w - - 0 1")
        board.push_uci("a7a8q")
        self._assert_snapshot_consistent(board)

    def test_snapshot_consistency_castling(self) -> None:
        board = BoardBitboard()
        for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1e2", "g8f6", "e1g1"]:
            board.push_uci(uci)
            self._assert_snapshot_consistent(board)

        board = BoardBitboard("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        board.push_uci("e1c1")
        self._assert_snapshot_consistent(board)

        board = BoardBitboard("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
        board.push_uci("e8c8")
        self._assert_snapshot_consistent(board)

    def test_deepcopy_preserves_cache_and_independence(self) -> None:
        board = BoardBitboard()
        for uci in ["e2e4", "e7e5", "g1f3", "b8c6"]:
            board.push_uci(uci)

        cloned = copy.deepcopy(board)

        # Clone should preserve the exact position and cache state.
        assert cloned.fen() == board.fen()
        assert cloned.piece_bitboards() == board.piece_bitboards()
        self._assert_snapshot_consistent(cloned)

        # Mutating clone should not affect original board.
        cloned.pop()
        self._assert_snapshot_consistent(cloned)
        assert board.fen() != cloned.fen()
