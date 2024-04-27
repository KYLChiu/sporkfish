from sporkfish.statistics import Statistics, NodeTypes, PruningTypes

# TODO: add tests to check searcher is indeed incrementing statistics correctly


class TestIncrementStatistics:
    def test_increment_node_visited(self):
        S = Statistics()
        for k, v in S.nodes_visited.items():
            assert v == 0
            S.increment_visited(k)

        for k, v in S.nodes_visited.items():
            assert v == 1


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

class TestLogging:
    def test_logging(self):
        S = Statistics()
        S.log_info()
        assert 1==0

    
