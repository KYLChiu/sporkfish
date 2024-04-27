from enum import Enum
from typing import Dict, Union
import chess
import logging


class NodeTypes(Enum):
    NEGAMAX = "NEGAMAX"
    NEGAMAX_LAZY_SMP = "NEGAMAX_LAZY_SMP"
    QUIESCENSE = "QUIESCENSE"
    TRANSPOSITITON_TABLE = "TRANSPOSITITON_TABLE"

class PruningTypes(Enum):
    NULL_MOVE = "NULL_MOVE"
    DELTA = "DELTA"
    FUTILITY = "FUTILITY"
    ALPHA_BETA = "ALPHA_BETA"

class TranpositionTable(Enum):
    TRANSPOSITITON_TABLE = "TRANSPOSITITON_TABLE"

class Statistics:
    """
    A class for tracking statistics related to node visits.
    """

    def __init__(self) -> None:
        """
        Initialize the Statistics object.
        Upon initialization, sets the counts of visited nodes, pruned nodes,
        and nodes stored in the transposition table to zero.
        """
        self._visited = {key: 0 for key in [*NodeTypes, *PruningTypes, *TranpositionTable]}

    # simplify to one api
    def increment_visited(
        self, visited_type: Union[NodeTypes, PruningTypes, TranpositionTable], count: int = 1
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
        self._visited[visited_type] += count

    def reset_visited(self, default_val: int = 0) -> None:
        """
        Reset the statistics by setting nodes_visited to a default value.

        :param default_val: The default value to set nodes_visited to (default is 0).
        :type default_val: int

        :return: None
        :rtype: None
        """
        for key in self._visited.keys():
            self._visited[key] = default_val

    @property
    def visited(self) -> Dict[NodeTypes, int]:
        """
        Returns a dictionary containing the count of visited nodes for different node types.

        :return: A dictionary containing the count of visited nodes for different node types.
        :rtype: dict
        """
        return self._visited
    
    def log_info(
        self, elapsed: float, score: float, move: chess.Move, depth: int
    ) -> Dict[str, Union[str, int, float, chess.Move]]:
        """
        :param elapsed: The time elapsed for the search process, in seconds.
        :type elapsed: float
        :param score: The evaluation score of the best move found.
        :type score: float
        :param move: The best move found during the search.
        :type move: chess.Move
        :param depth: The depth of the search.
        :type depth: int

        :return: A dictionary containing useful information about the search process.
        :rtype: dict
        """
        fields = {
            "Depth": depth,
            "Time": int(1000 * elapsed), # time in ms
            "Score cp": int(score) if score not in {float("inf"), -float("inf")} else float("nan"),
            "PV": move,  # Incorrect - pending: https://github.com/KYLChiu/sporkfish/issues/13
        }
        total_node = 0
        for type in NodeTypes:
            count = self._visited[type]
            fields[f"Node: {type}"] = self._visited[type]
            total_node += count
        fields["Total nodes"] = total_node

        total_pruning = 0
        for type in PruningTypes:
            count = self._visited[type]
            fields[f"Pruning: {type}"] = self._visited[type]
            total_pruning += count
        fields["Total pruning"] = total_pruning

        fields["Nodes from TT"] = self._visited[TranpositionTable.TRANSPOSITITON_TABLE]
        fields["NPS"] = float(total_node / elapsed) if elapsed > 0 else 0

        info_str = " ".join(f"{k} {v}" for k, v in fields.items())
        logging.info(f"info {info_str}")
