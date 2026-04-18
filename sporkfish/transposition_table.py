from typing import Dict, Optional, Tuple

import numpy as np


class TranspositionTable:
    EXACT = 0
    LOWER_BOUND = 1
    UPPER_BOUND = 2

    # Tuple layout: (depth, score, flag, best_move) - faster than a dict.
    # best_move is the move that produced `score`; stored for hash-move ordering.
    _DEPTH = 0
    _SCORE = 1
    _FLAG = 2
    _BEST_MOVE = 3

    def __init__(self, dct: Dict[np.int64, Tuple]) -> None:
        """
        Initialize the TranspositionTable object.

        :param dct: A dictionary containing Zobrist hash keys and associated entries.
        :type dct: Dict[np.int64, Tuple]
        """
        self._table = dct

    def store(
        self,
        zobrist_hash: np.int64,
        depth: int,
        score: float,
        flag: int,
        best_move=None,
    ) -> None:
        """
        Store an entry in the transposition table.
        Only stores if the existing entry depth is lower than the input one.

        :param zobrist_hash: The Zobrist hash value for the board position.
        :type zobrist_hash: np.int64
        :param depth: The depth at which the score was calculated.
        :type depth: int
        :param score: The score associated with the board position.
        :type score: float
        :param flag: The bound type (EXACT, LOWER_BOUND, or UPPER_BOUND).
        :type flag: int
        :param best_move: The move that produced this score; used for hash-move ordering.
        """
        existing_entry = self._table.get(zobrist_hash)
        if not existing_entry or depth > existing_entry[self._DEPTH]:
            self._table[zobrist_hash] = (depth, score, flag, best_move)

    def probe(self, zobrist_hash: np.int64, depth: int) -> Optional[Tuple]:
        """
        Retrieve an entry from the transposition table, if the existing entry depth is larger than the input one.

        :param zobrist_hash: The Zobrist hash value for the board position.
        :type zobrist_hash: np.int64
        :param depth: The depth at which the score is needed.
        :type depth: int

        :return: The stored entry as (depth, score, flag, best_move) if found, or None.
        :rtype: Optional[Tuple]
        """
        entry = self._table.get(zobrist_hash, None)
        if entry and entry[self._DEPTH] >= depth:
            return entry
        return None

    def get_best_move(self, zobrist_hash: np.int64):
        """
        Return the best move stored for this position, regardless of depth.
        Used for hash-move ordering at root nodes without requiring a depth match.

        :param zobrist_hash: The Zobrist hash value for the board position.
        :type zobrist_hash: np.int64

        :return: The stored best move, or None if no entry or no move stored.
        """
        entry = self._table.get(zobrist_hash)
        if entry and len(entry) > self._BEST_MOVE:
            return entry[self._BEST_MOVE]
        return None
