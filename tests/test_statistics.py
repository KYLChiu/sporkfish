from sporkfish.statistics import Statistics, NodeTypes, PruningTypes, TranpositionTable
import chess

# TODO: add tests to check searcher is indeed incrementing statistics correctly


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


class TestSearcherIncrement:
    def test_increment_searcher(self):
        assert 1==0

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

    
