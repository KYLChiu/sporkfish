from typing import List

import chess

from ...board.board import Board
from .move_order_heuristic import MoveOrderHeuristic


class KillerMoveHeuristic(MoveOrderHeuristic):
    def __init__(self, max_depth: int) -> None:
        # Store up to two killer moves for each depth
        # Null moves are never legal so will never compare equal to any legal move
        # Better to use inbuilt "null" move over None
        self._killer_moves: List[List[chess.Move]] = [
            [chess.Move.null(), chess.Move.null()] for _ in range(max_depth + 1)
        ]

    def add_killer_move(self, move: chess.Move, depth: int) -> None:
        """
        Add a move to the killer moves list for a given depth, ensuring it's not already present.
        If the move is new, it replaces the oldest killer move.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :param depth: The current depth at which the move ordering is considered.
        :type depth: int
        """
        if move not in self._killer_moves[depth]:
            # Shift the existing killer moves down and add the new one at the front
            self._killer_moves[depth].pop()
            self._killer_moves[depth].insert(0, move)

    def evaluate(self, board: Board, move: chess.Move, depth: int) -> float:
        """
        Calculate the killer move heursitic, i.e. if a move caused a beta cutoff
        in previous runs, it is stored and given a higher score on future move
        ordering evaluations.

        :param board: The current state of the chess board.
        :type board: Board
        :param move: The move to be evaluated.
        :type move: chess.Move
        :param depth: The current depth at which the move ordering is considered.
        :type depth: int
        :return: A floating-point value representing the killer evaluation of the move.
        :rtype: float
        """
        return 1 if move in self._killer_moves[depth] else 0

    @property
    def killer_moves_matrix(self) -> List[List[chess.Move]]:
        return self._killer_moves
