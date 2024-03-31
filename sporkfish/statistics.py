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

        Attributes:
        - nodes_visited (Value): The number of nodes visited. Shared across processes.
        """
        self._nodes_visited = {
            NodeTypes.NEGAMAX: 0,
            NodeTypes.NEGAMAX_LAZY_SMP: 0,
            NodeTypes.QUIESCENSE: 0
        }
        self._pruned = 0
        self._nodes_in_tt = 0

    def increment_node_visited(self, visited_node_type: NodeTypes, count: int = 1) -> None:
        """
        Increment the nodes_visited count.

        Parameters:
        - count (int): The number of nodes to increment the count by. Default is 1.
        """
        self._nodes_visited[visited_node_type] += count

    def increment_pruning(self, count: int = 1) -> None:
        """
        xxx
        """
        self._pruned += count

    def increment_nodes_in_tt(self, count: int = 1) -> None:
        """
        xxx
        """
        self._nodes_in_tt += count

    def reset_node_visited(self, default_val = 0) -> None:
        """
        Reset the statistics by setting nodes_visited to 0 
        and updating start_time to the current time. ???
        """
        for key in self._nodes_visited.keys():
            self._nodes_visited[key] = default_val

    def reset_pruning(self, default_val = 0) -> None:
        self._pruned = default_val

    def reset_nodes_in_tt(self, default_val = 0) -> None:
        self._nodes_in_tt = default_val

    @property
    def pruned(self) -> int:
        """
        xxx
        """
        return self._pruned
    
    @property
    def nodes_in_tt(self) -> int:
        """
        xxx
        """
        return self._nodes_in_tt
    
    @property
    def nodes_visited(self) -> Dict[NodeTypes, int]:
        """
        dda
        """
        return self._nodes_visited

