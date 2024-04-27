from sporkfish.statistics import Statistics, NodeTypes, PruningTypes, TranpositionTable
import chess
import pytest
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.searcher_factory import SearcherFactory
from init_board_helper import board_setup, evaluator, init_board
from sporkfish.board.board_factory import Board, BoardFactory, BoardPyChess





class TestIncrementStatistics:
    def test_increment_visited(self):
        S = Statistics()
        for k, v in S.visited.items():
            assert v == 0
            S.increment_visited(k)

        for k, v in S.visited.items():
            assert v == 1

    def test_increment_null_move(self):
        S = Statistics()
        assert S.visited[PruningTypes.NULL_MOVE] == 0
        S.increment_visited(PruningTypes.NULL_MOVE)
        assert S.visited[PruningTypes.NULL_MOVE] == 1

    def test_increment_tt(self):
        S = Statistics()
        assert S.visited[TranpositionTable.TRANSPOSITITON_TABLE] == 0
        S.increment_visited(TranpositionTable.TRANSPOSITITON_TABLE)
        assert S.visited[TranpositionTable.TRANSPOSITITON_TABLE] == 1

    def test_increment_negamax(self):
        S = Statistics()
        assert S.visited[NodeTypes.NEGAMAX] == 0
        S.increment_visited(NodeTypes.NEGAMAX)
        assert S.visited[NodeTypes.NEGAMAX] == 1

class TestResetStatistics:
    def test_reset_visited(self):
        S = Statistics()
        for k, v in S.visited.items():
            assert v == 0
            S.increment_visited(k, 3)
            assert S.visited[k] == 3


def init_searcher(
    max_depth: int = 3,
    search_mode: SearchMode = SearchMode.NEGA_MAX_SINGLE_PROCESS,
    enable_null_move_pruning=False,
    enable_futility_pruning=False,
    enable_delta_pruning=False,
    enable_transposition_table=False,
    enable_aspiration_windows=False,
    move_order_config=MoveOrderConfig(move_order_mode=MoveOrderMode.MVV_LVA),
):
    board = BoardFactory.create(board_type=BoardPyChess)
    s = SearcherFactory.create(
        SearcherConfig(
            max_depth=max_depth,
            search_mode=search_mode,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_futility_pruning=enable_futility_pruning,
            enable_delta_pruning=enable_delta_pruning,
            enable_transposition_table=enable_transposition_table,
            enable_aspiration_windows=enable_aspiration_windows,
            move_order_config=move_order_config,
        ),
        evaluator=evaluator(),
    )
    return s

@pytest.mark.parametrize(
    ("fen_string"),
    [
        (board_setup["white"]["mid"]),
    ],
)
class TestSearcherIncrement:
    def test_increment_negamax_sp_searcher(self, fen_string):
        s = init_searcher(search_mode = SearchMode.NEGA_MAX_SINGLE_PROCESS)
        assert s._statistics.visited[NodeTypes.NEGAMAX] == 0
        board = init_board(fen_string)
        depth = 1
        alpha = 0
        beta = 1
        zobrist_state = None
        s._negamax(board, depth, alpha, beta, zobrist_state)
        assert s._statistics.visited[NodeTypes.NEGAMAX] == 1

    # more tests needed!


def init_statistics_log(elapsed = 10.0, score = 100.0, move = chess.Move.null(), depth = 3):
    S = Statistics()
    assert S.info_data is None
    S.log_info(elapsed, score, move, depth)
    return S

class TestLogging:
    def test_logging(self):
        S = init_statistics_log()
        assert isinstance(S.info_data, dict)

    def test_log_depth(self, elapsed = 0.421, score = 24.21, move = chess.Move.null(), depth = 342):
        S = init_statistics_log(elapsed, score, move, depth)
        assert S.info_data["Depth"] == depth

    
