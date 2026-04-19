from typing import Dict, Optional

import chess

from sporkfish.board.board import Board
from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic
from sporkfish.searcher.see import static_exchange_eval


class MvvLvaHeuristic(MoveOrderHeuristic):
    """
    Most Valuable Victim - Least Valuable Aggressor (MVV-LVA) move ordering.

    Prioritises captures that win the most material: capturing a queen with a
    pawn scores higher than capturing a pawn with a queen.  The table encodes
    victim x attacker scores so the comparison is a single array lookup with no
    arithmetic at query time.

    King captures are assigned 0 (the king can never legally be captured).
    Scores are integers in [10, 55]; higher = more desirable.
    """

    # Columns: attacker P, N, B, R, Q, K
    _MVV_LVA = [
        [15, 14, 13, 12, 11, 10],  # victim P
        [25, 24, 23, 22, 21, 20],  # victim N
        [35, 34, 33, 32, 31, 30],  # victim B
        [45, 44, 43, 42, 41, 40],  # victim R
        [55, 54, 53, 52, 51, 50],  # victim Q
        [0, 0, 0, 0, 0, 0],  # victim K
    ]

    def __init__(
        self,
        board: Board,
        piece_values: Optional[Dict[chess.PieceType, float]] = None,
    ) -> None:
        MoveOrderHeuristic.__init__(self)
        self._board = board
        self._piece_values = piece_values

    def evaluate(self, move: chess.Move) -> float:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value
        for a capturing move based on the value of the captured piece.

        :param move: The move to be evaluated.
        :type move: chess.Move
        :return: A floating-point value representing the MVV-LVA evaluation of the move.
        :rtype: float
        """

        if (
            self._board.is_capture(move)
            and (captured_type := self._board.piece_type_at(move.to_square))
            and (moving_type := self._board.piece_type_at(move.from_square))
        ):
            mvv_lva = MvvLvaHeuristic._MVV_LVA[captured_type - 1][moving_type - 1]
            if self._piece_values is None:
                return mvv_lva

            # SEE dominates ordering between winning/losing captures.
            see = static_exchange_eval(self._board, move, self._piece_values)
            return see * 100.0 + mvv_lva
        else:
            return 0
