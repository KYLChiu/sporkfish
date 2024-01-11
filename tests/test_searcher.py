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


def test_fen():
    searcher_with_fen(
        "r1bqkb1r/1ppp1ppp/p1n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5"
    )
