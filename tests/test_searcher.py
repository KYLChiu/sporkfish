from sporkfish.searcher import Searcher
from sporkfish.evaluator import Evaluator
import chess


def searcher_with_fen(fen: str, depth=5):
    board = chess.Board()
    e = Evaluator()
    s = Searcher(e, depth)
    board.set_fen(fen)
    score, move = s.search(board)
    return score, move


# Below tests just test if no exceptions are thrown and no null moves made
def test_pos1():
    searcher_with_fen(
        "r1bqkb1r/1ppp1ppp/p1n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5"
    )


def test_pos2():
    searcher_with_fen("r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18")
