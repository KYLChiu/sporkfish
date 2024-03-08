from typing import Dict

import chess

from ...board.board import Board
from .move_order_heuristic import MoveOrderHeuristic


class HistoryHeuristic(MoveOrderHeuristic):
    def __init__(self, board: Board, history_table: Dict[chess.Move, int]) -> None:
        super().__init__(self)
        self._board = board
        self._history_table = history_table

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate the history heuristic for a move. The heuristic score is based
        on how often a move has historically led to alpha-beta cutoffs. Moves
        with more cutoffs in the past receive a higher score.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: An integer value representing the history score of the move.
        :rtype: int
        """
        return (
            self._history_table.get(move, 0) if not self._board.is_capture(move) else 0
        )
