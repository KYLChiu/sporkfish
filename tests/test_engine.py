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
    _ = eng.score(board, 1e-3)
    # Timed out, impossible that depth 100 is <1 sec
    assert time.time() - start < 1


