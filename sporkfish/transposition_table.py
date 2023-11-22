import chess
from typing import Optional


class TranspositionTable:
    def __init__(self) -> None:
        """
        Initialize the TranspositionTable object.
        """
        # Eventually use Manager.dict() here from multiprocessing
        # Issues arise when attempting to pickle any object with Manager, needs rethinking
        self._table = {}

    def store(
        self,
        zobrist_hash: int,
        depth: int,
        score: float,
        best_move: Optional[chess.Move] = None,
    ) -> None:
        """
        Store an entry in the transposition table.

        Parameters:
        - zobrist_hash (int): The Zobrist hash value for the board position.
        - depth (int): The depth at which the score was calculated.
        - score (float): The score associated with the board position.
        - best_move (Optional[chess.Move]): The best move associated with the board position.
        """
        entry = {"depth": depth, "score": score, "best_move": best_move}
        self._table[zobrist_hash] = entry

    def probe(self, zobrist_hash: int, depth: int) -> Optional[dict]:
        """
        Retrieve an entry from the transposition table.

        Parameters:
        - zobrist_hash (int): The Zobrist hash value for the board position.
        - depth (int): The depth at which the score is needed.

        Returns:
        - Optional[dict]: The stored entry if found, or None if not found or the depth is insufficient.
        """
        entry = self._table.get(zobrist_hash)
        if entry and entry["depth"] >= depth:
            return entry
        return None
