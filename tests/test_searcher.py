import pytest
from unittest.mock import patch, MagicMock
import chess
from sporkfish.searcher import Searcher


@pytest.fixture
def mock_evaluator():
    return MagicMock()


@patch("builtins.sorted", new_callable=MagicMock)
def test_search(mock_evaluator):
    searcher = Searcher(mock_evaluator)
    board = chess.Board()

    # Mock the _alpha_beta_search method
    searcher._negamax_search = MagicMock(return_value=(10000, "e2e4"))
    best_move = searcher.search(board)
    assert best_move == "e2e4"
