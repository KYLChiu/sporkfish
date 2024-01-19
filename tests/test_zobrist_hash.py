import chess

from sporkfish.board.board_factory import Board, BoardFactory, BoardPyChess
from sporkfish.board.move import Move
from sporkfish.zobrist_hasher import ZobristHasher


def test_seeded_and_equivalent():
    zh1 = ZobristHasher()
    board = BoardFactory.create(BoardPyChess)
    hash1 = zh1.hash(board)

    zh2 = ZobristHasher()
    hash2 = zh2.hash(board)
    # Make sure internal hashes are equivalent (i.e. we seeded the random numbers) by checking the final hash.
    # Also check the final hashes are the same for the same board
    assert hash1 == hash2


def test_no_hash_collision():
    zh = ZobristHasher()

    def check(board: Board):
        s = set()
        for move in board.legal_moves:
            board.push(move)

            hash = zh.hash(board)
            assert hash not in s
            s.add(hash)

            board.pop()

    check(BoardFactory.create(BoardPyChess))
