from sporkfish.zobrist_hasher import ZobristHasher
import chess


def test_seeded_and_equivalent():
    zh1 = ZobristHasher()
    board = chess.Board()
    board.push(chess.Move.from_uci("d2d4"))
    hash1 = zh1.hash(board)

    zh2 = ZobristHasher()
    hash2 = zh2.hash(board)
    # Make sure internal hashes are equivalent (i.e. we seeded the random numbers) by checking the final hash.
    # Also check the final hashes are the same for the same board
    assert hash1 == hash2


def test_no_hash_collision():
    zh = ZobristHasher()

    def check(board: chess.Board):
        s = set()
        for move in board.legal_moves:
            board.push(move)

            hash = zh.hash(board)
            assert hash not in s
            s.add(hash)

            board.pop()

    board1 = chess.Board()
    check(chess.Board())
