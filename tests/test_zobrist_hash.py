import chess
import pytest

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.zobrist_hasher import ZobristHasher


class TestZobristHashFull:
    def test_full_hash_seeded_and_equivalent(self):
        zh1 = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)
        hash1 = zh1.full_zobrist_hash(board).zobrist_hash

        zh2 = ZobristHasher()
        hash2 = zh2.full_zobrist_hash(board).zobrist_hash
        # Make sure internal hashes are equivalent (i.e. we seeded the random numbers) by checking the final hash.
        # Also check the final hashes are the same for the same board
        assert hash1 == hash2

    def test_full_hash_no_collision(self):
        zh = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)
        s = set()

        for move in board.legal_moves:
            board.push(move)

            hash = zh.full_zobrist_hash(board).zobrist_hash
            assert hash not in s
            s.add(hash)

            board.pop()


class TestZobristHashIncremental:
    """
    Consistency test of the incremental hash against the full hash
    """

    @pytest.fixture
    def _setup_board_and_move(self, fen, move_uci):
        zh = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)
        board.set_fen(fen)
        initial_zobrist_state = zh.full_zobrist_hash(board)
        move = chess.Move.from_uci(move_uci)
        previous_move_from_square = board.piece_at(move.from_square)
        captured_piece = board.piece_at(move.to_square)
        board.push(move)
        return (
            zh,
            board,
            initial_zobrist_state,
            move,
            previous_move_from_square,
            captured_piece,
        )

    def test_inc_hash_consistency_basic(self):
        zh = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)

        initial_zobrist_state = zh.full_zobrist_hash(board)
        for move in board.legal_moves:
            previous_move_from_square = board.piece_at(move.from_square)
            board.push(move)

            hash = zh.full_zobrist_hash(board).zobrist_hash
            inc_hash = zh.incremental_zobrist_hash(
                board,
                move,
                initial_zobrist_state,
                previous_move_from_square,
                None,  # No capturing moves from starting pos
            ).zobrist_hash

            assert (
                hash == inc_hash
            ), f"Incremental hash consistency failed for move {move}"

            board.pop()

    @pytest.mark.parametrize(
        "test_name, fen, move_uci",
        [
            (
                "capture",
                "rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1",
                "d4e5",
            ),
            (
                "promotion",
                "rnbq3r/ppppkP1p/5n1b/8/6p1/2N5/PPP1N1PP/R1BQKB1R w KQ - 0 1",
                "f7f8q",
            ),
            (
                "capturing_promotion",
                "rnbq2r1/ppppkP1p/5n1b/8/6p1/2N5/PPPBN1PP/R2QKB1R w KQ - 0 1",
                "f7g8q",
            ),
            (
                "en_passant",
                "rnbqkbnr/ppppp2p/6p1/4Pp2/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
                "e5f6",
            ),
            (
                "black_no_kingside_castling",
                "rnbqk1nr/ppppb1Qp/6p1/5p2/4P3/8/PPPP1PPP/RNB1KBNR w KQq - 0 1",
                "h2h4",
            ),
            (
                "black_no_castling",
                "rnbq1bnr/pppppk1p/6p1/5p2/5P2/6P1/PPPPP2P/RNBQKBNR w KQ - 0 1",
                "h2h4",
            ),
            (
                "all_no_castling",
                "rnbq1bnr/pppppk1p/6p1/5p2/5P2/6P1/PPPPPK1P/RNBQ1BNR w - - 0 1",
                "h2h4",
            ),
        ],
    )
    def test_inc_hash_consistency(self, _setup_board_and_move, test_name):
        (
            zh,
            board,
            initial_zobrist_state,
            move,
            previous_move_from_square,
            captured_piece,
        ) = _setup_board_and_move
        hash = zh.full_zobrist_hash(board).zobrist_hash
        inc_hash = zh.incremental_zobrist_hash(
            board,
            move,
            initial_zobrist_state,
            previous_move_from_square,
            captured_piece,
        ).zobrist_hash
        assert hash == inc_hash, f"{test_name} failed for move {move}"
