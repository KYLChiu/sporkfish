import chess
import pytest
from init_board_helper import board_setup, evaluator, init_board

from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode
from sporkfish.searcher.searcher_factory import SearcherFactory
from sporkfish.statistics import NodeTypes, PruningTypes, Statistics, TranspositionTable


class TestIncrementStatistics:
    def test_increment_visited(self):
        s = Statistics()
        for k, v in s.visited.items():
            assert v == 0
            s.increment_visited(k)

        for k, v in s.visited.items():
            assert v == 1

    def test_increment_null_move(self):
        s = Statistics()
        assert s.visited[PruningTypes.NULL_MOVE] == 0
        s.increment_visited(PruningTypes.NULL_MOVE)
        assert s.visited[PruningTypes.NULL_MOVE] == 1

    def test_increment_tt(self):
        s = Statistics()
        assert s.visited[TranspositionTable.TRANSPOSITITON_TABLE] == 0
        s.increment_visited(TranspositionTable.TRANSPOSITITON_TABLE)
        assert s.visited[TranspositionTable.TRANSPOSITITON_TABLE] == 1

    def test_increment_negamax(self):
        s = Statistics()
        assert s.visited[NodeTypes.NEGAMAX] == 0
        s.increment_visited(NodeTypes.NEGAMAX)
        assert s.visited[NodeTypes.NEGAMAX] == 1


class TestResetStatistics:
    def test_reset_visited(self):
        s = Statistics()
        for k, v in s.visited.items():
            assert v == 0
            s.increment_visited(k, 3)
            assert s.visited[k] == 3


def init_searcher(
    max_depth: int = 3,
    search_mode: SearchMode = SearchMode.NEGAMAX_SINGLE_PROCESS,
    enable_null_move_pruning=False,
    enable_futility_pruning=False,
    enable_delta_pruning=False,
    enable_transposition_table=False,
    enable_aspiration_windows=False,
    move_order_config=MoveOrderConfig(move_order_mode=MoveOrderMode.MVV_LVA),
):
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
        s = init_searcher(search_mode=SearchMode.NEGAMAX_SINGLE_PROCESS)
        assert s._statistics.visited[NodeTypes.NEGAMAX] == 0
        board = init_board(fen_string)
        depth = 1
        alpha = 0
        beta = 1
        zobrist_state = None
        s._negamax(board, depth, alpha, beta, zobrist_state)
        assert s._statistics.visited[NodeTypes.NEGAMAX] == 1

    # more tests needed!


def init_statistics_log(elapsed=10.0, score=100.0, move=chess.Move.null(), depth=3):
    s = Statistics()
    assert isinstance(s.info_data, dict)
    assert len(s.info_data) == 0
    s.log_info(elapsed, score, move, depth)
    return s


class TestLogging:
    def test_logging(self):
        s = init_statistics_log()
        assert isinstance(s.info_data, dict)
        assert len(s.info_data) > 0

    def test_log_depth(
        self, elapsed=0.421, score=24.21, move=chess.Move.null(), depth=342
    ):
        s = init_statistics_log(elapsed, score, move, depth)
        assert s.info_data["Depth"] == depth
