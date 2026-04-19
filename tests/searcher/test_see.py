import chess
from init_board_helper import init_board

from sporkfish.evaluator.pesto import Pesto
from sporkfish.searcher.see import static_exchange_eval


def test_see_non_capture_is_zero() -> None:
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    score = static_exchange_eval(board, move, Pesto().piece_values())
    assert score == 0.0


def test_see_winning_capture_positive() -> None:
    board = init_board("k7/8/8/8/8/8/7K/6qR w - - 1 34")
    move = chess.Move.from_uci("h1g1")
    score = static_exchange_eval(board, move, Pesto().piece_values())
    assert score > 0.0


def test_see_losing_capture_negative() -> None:
    # Qxd5 loses the queen after ...Qxd5 recapture.
    board = init_board("3qk3/8/8/3p4/8/8/8/3QK3 w - - 0 1")
    move = chess.Move.from_uci("d1d5")
    score = static_exchange_eval(board, move, Pesto().piece_values())
    assert score < 0.0
