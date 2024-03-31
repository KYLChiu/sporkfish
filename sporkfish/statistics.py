from enum import Enum
from typing import Dict


class NodeTypes(Enum):
    NEGAMAX = "NEGAMAX"
    NEGAMAX_LAZY_SMP = "NEGAMAX_LAZY_SMP"
    QUIESCENSE = "QUIESCENSE"


class Statistics:
    """A class for tracking statistics related to node visits."""

    def __init__(self):
        """
        Initialize the Statistics object.
        Upon initialization, sets the counts of visited nodes, pruned nodes,
        and nodes stored in the transposition table to zero.
        """
        self._nodes_visited = {
            NodeTypes.NEGAMAX: 0,
            NodeTypes.NEGAMAX_LAZY_SMP: 0,
            NodeTypes.QUIESCENSE: 0,
        }
        self._pruned = 0
        self._nodes_in_tt = 0

    def increment_node_visited(
        self, visited_node_type: NodeTypes, count: int = 1
    ) -> None:
        """
        Increment the count of visited nodes of a specified type.

        :param visited_node_type: The type of node being visited.
        :type visited_node_type: NodeTypes
        :param count: The number of nodes to increment the count by. Default is 1.
        :type count: int
        :return: None
        :rtype: None
        """
        self._nodes_visited[visited_node_type] += count

    # TODO: enrich to record types of pruning
    def increment_pruning(self, count: int = 1) -> None:
        """
        Increments the pruning count by the specified amount.

        :param count: The amount by which to increment the pruning count (default is 1).
        :type count: int

        :return: None
        :rtype: None
        """
        self._pruned += count

    def increment_nodes_from_tt(self, count: int = 1) -> None:
        """
        Increments the nodes in TT count by the specified amount.

        :param count: The amount by which to increment the pruning count (default is 1).
        :type count: int

        :return: None
        :rtype: None
        """
        self._nodes_in_tt += count

    def reset_node_visited(self, default_val=0) -> None:
        """
        Reset the statistics by setting nodes_visited to a default value.

        :param default_val: The default value to set nodes_visited to (default is 0).
        :type default_val: int

        :return: None
        :rtype: None
        """
        for key in self._nodes_visited.keys():
            self._nodes_visited[key] = default_val

    def reset_pruning(self, default_val=0) -> None:
        """
        Reset the pruning count to a default value.

        :param default_val: The default value to set pruning count to (default is 0).
        :type default_val: int

        :return: None
        :rtype: None
        """
        self._pruned = default_val

    def reset_nodes_from_tt(self, default_val=0) -> None:
        """
        Reset the nodes in TT count to a default value.

        :param default_val: The default value to set nodes in TT count to (default is 0).
        :type default_val: int

        :return: None
        :rtype: None
        """
        self._nodes_in_tt = default_val

    @property
    def pruned(self) -> int:
        """
        Returns the count of pruned nodes.

        :return: The count of pruned nodes.
        :rtype: int
        """
        return self._pruned

    @property
    def nodes_from_tt(self) -> int:
        """
        :return: The count of nodes returned from the transposition table.
        :rtype: int
        """
        return self._nodes_in_tt

    @property
    def nodes_visited(self) -> Dict[NodeTypes, int]:
        """
        Returns a dictionary containing the count of visited nodes for different node types.

        :return: A dictionary containing the count of visited nodes for different node types.
        :rtype: dict
        """
        return self._nodes_visited
