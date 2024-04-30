from sporkfish.statistics import Statistics

# TODO: add tests to check searcher is indeed incrementing statistics correctly


class TestIncrementStatistics:
    def test_increment_node_visited(self):
        S = Statistics()
        for k, v in S.nodes_visited.items():
            assert v == 0
            S.increment_node_visited(k)

        for k, v in S.nodes_visited.items():
            assert v == 1

    def test_increment_pruning(self):
        S = Statistics()
        assert S.pruned == 0
        S.increment_pruning()
        assert S.pruned == 1

    def test_increment_nodes_in_tt(self):
        S = Statistics()
        assert S.nodes_from_tt == 0
        S.increment_nodes_from_tt()
        assert S.nodes_from_tt == 1


class TestResetStatistics:
    def test_reset_node_visited(self):
        S = Statistics()
        for k, v in S.nodes_visited.items():
            assert v == 0
            S.increment_node_visited(k, 3)
            assert S.nodes_visited[k] == 3

        S.reset_node_visited()
        for k, v in S.nodes_visited.items():
            assert v == 0

    def test_reset_pruning(self):
        S = Statistics()
        assert S.pruned == 0
        S.increment_pruning(3)
        assert S.pruned == 3
        S.reset_pruning(0)
        assert S.pruned == 0

    def test_reset_nodes_in_tt(self):
        S = Statistics()
        assert S.nodes_from_tt == 0
        S.increment_nodes_from_tt(32)
        assert S.nodes_from_tt == 32
        S.reset_nodes_from_tt(0)
        assert S.nodes_from_tt == 0
