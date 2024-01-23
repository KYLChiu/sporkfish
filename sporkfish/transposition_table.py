from typing import Dict, Optional
import numpy as np


class TranspositionTable:
    def __init__(self, dct: Dict[np.uint64, Dict[str, float]]) -> None:
        """
        Initialize the TranspositionTable object, wrapping a dict.

        """
        self._table = dct

    def store(
        self,
        zobrist_hash: np.uint64,
        depth: int,
        score: float,
    ) -> None:
        """
        Store an entry in the transposition table.

        Parameters:
        - zobrist_hash (np.uint64): The Zobrist hash value for the board position.
        - depth (int): The depth at which the score was calculated.
        - score (float): The score associated with the board position.
        """
        # TODO: test and consider what happens on rewrites
        # We could potentially lose lots of time if we probe first as a condition
        self._table[zobrist_hash] = {"depth": depth, "score": score}

    def probe(self, zobrist_hash: np.uint64, depth: int) -> Optional[Dict]:
        """
        Retrieve an entry from the transposition table.

        Parameters:
        - zobrist_hash (np.uint64): The Zobrist hash value for the board position.
        - depth (int): The depth at which the score is needed.

        Returns:
        - Optional[dict]: The stored entry if found, or None if not found or the depth is insufficient.
        """
        entry = self._table.get(zobrist_hash, None)
        if entry and entry["depth"] >= depth:
            return entry
        return None
