import logging
from enum import Enum
from typing import Dict, Union

import chess


class NodeTypes(Enum):
    NEGAMAX = "NEGAMAX"
    NEGAMAX_LAZY_SMP = "NEGAMAX_LAZY_SMP"
    QUIESCENSE = "QUIESCENSE"


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
        self._visited = {
            key: 0 for key in [*NodeTypes, *PruningTypes, *TranpositionTable]
        }
        self._fields: Dict = {}

    def increment_visited(
        self,
        visited_type: Union[NodeTypes, PruningTypes, TranpositionTable],
        count: int = 1,
    ) -> None:
        """
        Increment the count of visited nodes of a specified type.

        :param visited_node_type: The type of node being visited.
        :type visited_node_type: Union[NodeTypes, PruningTypes, TranpositionTable]
        :param count: The number of nodes to increment the count by. Default is 1.
        :type count: int
        """
        self._visited[visited_type] += count

    def reset_visited(self, default_val: int = 0) -> None:
        """
        Reset the statistics by setting nodes_visited to a default value.

        :param default_val: The default value to set nodes_visited to (default is 0).
        :type default_val: int
        """
        for key in self._visited.keys():
            self._visited[key] = default_val

    @property
    def visited(self) -> Dict[NodeTypes, int]:
        """
        Returns a dictionary containing the count of visited nodes for different node types.

        :return: A dictionary containing the count of visited nodes for different node types.
        :rtype: Dict[NodeTypes, int]
        """
        return self._visited

    @property
    def info_data(self) -> Dict:
        """
        Returns a dictionary containing useful information about the search process.

        :return: A dictionary containing useful information about the search process.
        :rtype: Dict
        """
        return self._fields

    def log_info(
        self, elapsed: float, score: float, move: chess.Move, depth: int
    ) -> None:
        """
        :param elapsed: The time elapsed for the search process, in seconds.
        :type elapsed: float
        :param score: The evaluation score of the best move found.
        :type score: float
        :param move: The best move found during the search.
        :type move: chess.Move
        :param depth: The depth of the search.
        :type depth: int
        """
        self._fields = {
            "Depth": depth,
            "Time": int(1000 * elapsed),  # time in ms
            "Score cp": int(score)
            if score not in {float("inf"), -float("inf")}
            else float("nan"),
            "PV": move,  # Incorrect - pending: https://github.com/KYLChiu/sporkfish/issues/13
        }
        total_node = 0
        for type in NodeTypes:
            count = self._visited[type]
            self._fields[f"Node: {type}"] = self._visited[type]
            total_node += count
        self._fields["Total nodes"] = total_node

        total_pruning = 0
        for type in PruningTypes:  # type: ignore
            count = self._visited[type]
            self._fields[f"Pruning: {type}"] = self._visited[type]
            total_pruning += count
        self._fields["Total pruning"] = total_pruning

        self._fields["Nodes from TT"] = self._visited[
            TranpositionTable.TRANSPOSITITON_TABLE
        ]
        self._fields["NPS"] = float(total_node / elapsed) if elapsed > 0 else 0

        # TODO: clean up / format self._info_str
        self._info_str = " ".join(f"{k} {v}" for k, v in self._fields.items())
        logging.info(f"info {self._info_str}")
