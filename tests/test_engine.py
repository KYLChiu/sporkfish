from unittest.mock import MagicMock
import chess
from sporkfish.engine import Engine
import sporkfish.opening_book as opening_book


def test_make_move():
    board = chess.Board()
    searcher = MagicMock()
    searcher.search.return_value = chess.Move.from_uci("e2e4")
    engine = Engine(searcher, opening_book.OpeningBook())
    move = engine.make_move(board=board)
    assert move == chess.Move.from_uci("e2e4")
    assert board.move_stack[-1] == move
