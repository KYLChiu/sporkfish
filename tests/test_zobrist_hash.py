from sporkfish.board.board_factory import Board, BoardFactory, BoardPyChess
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

        def check(board: Board):
            s = set()
            for move in board.legal_moves:
                board.push(move)

                hash = zh.full_zobrist_hash(board).zobrist_hash
                assert hash not in s
                s.add(hash)

                board.pop()

        check(BoardFactory.create(BoardPyChess))


class TestZobristHashIncremental:
    def test_inc_hash_consistency_basic(self):
        zh = ZobristHasher()

        def check(board: Board):
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

        check(BoardFactory.create(BoardPyChess))
