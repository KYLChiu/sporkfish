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
    def test_inc_hash_consistency_basic(self):
        zh = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)

        initial_zobrist_state = zh.full_zobrist_hash(board)
        for move in board.legal_moves:
            captured_piece = (
                board.piece_at(move.to_square) if board.is_capture(move) else None
            )
            board.push(move)

            hash = zh.full_zobrist_hash(board).zobrist_hash
            inc_hash = zh.incremental_zobrist_hash(
                board, move, initial_zobrist_state, captured_piece
            ).zobrist_hash

            assert (
                hash == inc_hash
            ), f"Incremental hash consistency failed for move {move}"

            board.pop()

    def test_inc_hash_consistency_capture(self):
        zh = ZobristHasher()
        board = BoardFactory.create(BoardPyChess)
        initial_zobrist_state = zh.full_zobrist_hash(board)

        board.set_fen("rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1")
        capturing_moves = [move for move in board.legal_moves if board.is_capture(move)]
        assert len(capturing_moves) == 1, "Should only be one capturing move."
        move = capturing_moves[0]
        captured_piece = board.piece_at(move.to_square)

        board.push(move)

        hash = zh.full_zobrist_hash(board).zobrist_hash
        inc_hash = zh.incremental_zobrist_hash(
            board, move, initial_zobrist_state, captured_piece
        ).zobrist_hash

        assert hash == inc_hash, f"Incremental hash consistency failed for move {move}"
