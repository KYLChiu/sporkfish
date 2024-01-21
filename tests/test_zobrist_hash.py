from sporkfish.board.board_factory import Board, BoardFactory, BoardPyChess
from sporkfish.zobrist_hasher import ZobristHasher


def test_seeded_and_equivalent():
    board = BoardFactory.create(BoardPyChess)
    zh1 = ZobristHasher()

    hash1 = zh1.hash(board)

    zh2 = ZobristHasher()
    hash2 = zh2.hash(board)
    # Make sure internal hashes are equivalent (i.e. we seeded the random numbers) by checking the final hash.
    # Also check the final hashes are the same for the same board
    assert hash1 == hash2


def test_no_hash_collision():
    board = BoardFactory.create(BoardPyChess)
    zh = ZobristHasher()

    def check(board: Board):
        s = set()
        for move in board.legal_moves:
            board.push(move)

            hash = zh.hash(board)
            assert hash not in s
            s.add(hash)

            board.pop()

    check(board)


def test_incremental_hash():
    board = BoardFactory.create(BoardPyChess)
    zh = ZobristHasher()

    def check(board: Board):
        initial_hash = zh.hash(board)
        i = 0
        for move in board.legal_moves:
            print(move)
            board.push(move)

            full_hash = zh.hash(board)
            rolling_hash = zh.incremental_hash(initial_hash, board)
            assert full_hash == rolling_hash

            board.pop()
            i += 1

    check(board)
