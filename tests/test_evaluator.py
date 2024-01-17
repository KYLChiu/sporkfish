from sporkfish import evaluator
import chess

# NB: static evaluation function must return a score relative to the side to being evaluated, e.g. the simplest score evaluation could be:
# score = materialWeight * (numWhitePieces - numBlackPieces) * who2move


def score_fen(fen_string: str):
    board = chess.Board()
    board.set_fen(fen_string)
    ev = evaluator.Evaluator()
    return ev.evaluate(board)


def test_black_winning_black_to_move():
    score = score_fen("6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34")
    assert score > 0


def test_black_winning_white_to_move():
    score = score_fen("8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35")
    assert score < 0


def test_white_winning_white_to_move():
    score = score_fen("8/2Q5/8/8/1k1K4/8/8/8 w - - 15 74")
    assert score > 0


def test_white_winning_black_to_move():
    score = score_fen("8/1Q6/8/8/1k1K4/8/8/8 b - - 16 74")
    assert score < 0
