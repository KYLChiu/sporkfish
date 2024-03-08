from typing import Dict, Optional

import numpy as np


class TranspositionTable:
    def __init__(self, dct: Dict[np.int64, Dict[str, float]]) -> None:
        """
        Initialize the TranspositionTable object.

        :param dct: A dictionary containing Zobrist hash keys and associated entries.
        :type dct: Dict[np.int64, Dict[str, float]]
        """
        self._table = dct

    def store(
        self,
        zobrist_hash: np.int64,
        depth: int,
        score: float,
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
        """
        existing_entry = self._table.get(zobrist_hash)
        if not existing_entry or depth > existing_entry["depth"]:
            self._table[zobrist_hash] = {"depth": depth, "score": score}

    def probe(self, zobrist_hash: np.int64, depth: int) -> Optional[Dict]:
        """
        Retrieve an entry from the transposition table, if the existing entry depth is larger than the input one.

        :param zobrist_hash: The Zobrist hash value for the board position.
        :type zobrist_hash: np.int64
        :param depth: The depth at which the score is needed.
        :type depth: int
        :return: The stored entry if found, or None if not found or the depth is insufficient.
        :rtype: Optional[Dict]
        """
        entry = self._table.get(zobrist_hash, None)
        if entry and entry["depth"] >= depth:
            return entry
        return None
