from unittest.mock import MagicMock
import chess
from sporkfish.engine import Engine
from sporkfish.uci_client import UCIClient
import sporkfish.opening_book as opening_book


def test_timeout():
    board = chess.Board()
    eng = UCIClient.create_engine(100)
    score = eng.score(board, 1e-12)
    assert score == -float("inf")
