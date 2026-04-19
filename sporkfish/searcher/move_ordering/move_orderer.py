from typing import Any, List

import chess

from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic


class MoveOrderer:
    @staticmethod
    def order_moves(
        move_ordering_heuristic: MoveOrderHeuristic, legal_moves: Any
    ) -> List[chess.Move]:
        """
        Order the given legal moves from best to worst based on a move ordering heuristic.

        This method sorts the legal moves based on a move ordering heuristic, which aims to prioritize
        moves that are likely to lead to better positions or outcomes. The ordering can help improve
        the efficiency of the search algorithm by considering more promising moves first.

        :param move_ordering_heuristic: The move ordering heuristic used to evaluate moves.
        :type move_ordering_heuristic: MoveOrderHeuristic
        :param legal_moves: The legal moves to be ordered.
        :type legal_moves: Any
        :return: The ordered legal moves.
        :rtype: List[chess.Move]
        """
        moves = list(legal_moves)
        if not moves:
            return moves

        moves.sort(key=move_ordering_heuristic.evaluate, reverse=True)
        return moves
