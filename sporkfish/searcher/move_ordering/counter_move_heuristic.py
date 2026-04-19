from typing import Dict

import chess

from sporkfish.board.board import Board
from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic


class CounterMoveHeuristic(MoveOrderHeuristic):
    """
    Counter-move heuristic for quiet move ordering.

    Stores the best known quiet reply to the opponent's previous move. At a node,
    if a move matches the recorded reply to the current ply's previous move,
    it receives a bonus and is searched earlier.
    """

    def __init__(self, board: Board, counter_move_table: Dict[chess.Move, chess.Move]):
        MoveOrderHeuristic.__init__(self)
        self._board = board
        self._counter_move_table = counter_move_table

    def evaluate(self, move: chess.Move) -> float:
        if self._board.is_capture(move) or not self._board.move_stack:
            return 0.0

        previous_move = self._board.move_stack[-1]
        return 1.0 if self._counter_move_table.get(previous_move) == move else 0.0
