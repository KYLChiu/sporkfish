from unittest.mock import MagicMock
import chess
import time
from sporkfish.engine import Engine
from sporkfish.uci_client import UCIClient
import sporkfish.opening_book as opening_book


def test_timeout():
    board = chess.Board()
    eng = UCIClient.create_engine(100)
    start = time.time()
    score = eng.score(board, 1e-3)
    # Not the most reliable way to test but don't have better ideas
    assert time.time() - start < 1
