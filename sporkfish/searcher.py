import chess
from typing import Tuple
from pathos.multiprocessing import ProcessPool
from multiprocessing import Manager
import os

from . import evaluator
from . import statistics
from . import transposition_table
from . import zobrist_hash


class Searcher:
    """
    Move searching class.

    Attributes:
    - evaluator (Evaluator): The chess board evaluator.
    - max_depth (int): The maximum search depth for the minimax algorithm.
    """

    _manager = Manager()
    _dct = _manager.dict()

    def __init__(self, evaluator: evaluator.Evaluator, max_depth: int = 5) -> None:
        """
        Initialize the Searcher instance with mutable statistics

        :param evaluator: The chess board evaluator.
        :type evaluator: evaluator.Evaluator
        :param max_depth: The maximum search depth for the minimax algorithm.
                         Default is 5.
        :type max_depth: int
        :return: None
        """

        self._evaluator = evaluator
        self._max_depth = max_depth
        self._statistics = statistics.Statistics()
        self._zorbist_hash = zobrist_hash.ZobristHash()

        self._transposition_table = transposition_table.TranspositionTable(
            Searcher._dct
        )
        self._pool = ProcessPool(nodes=os.cpu_count())

    def _mvv_lva_heuristic(self, board: chess.Board, move: chess.Move) -> int:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value for a capturing move based on the value of the captured piece.

        Parameters:
            board (chess.Board): The chess board.
            move (chess.Move): The capturing move.

        Returns:
            int: The heuristic value of the capturing move based on the value of the captured piece.
        """
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 200,
        }

        captured_piece = board.piece_at(move.to_square)
        moving_piece = board.piece_at(move.from_square)

        if (
            captured_piece is not None
            and moving_piece is not None
            and board.is_capture(move)
        ):
            return piece_values.get(captured_piece.piece_type) - piece_values.get(
                moving_piece.piece_type
            )
        else:
            return 0

    def _quiescence(
        self, board: chess.Board, depth: int, alpha: float, beta: float
    ) -> float:
        """
        Quiescence search to help the horizon effect (improving checking of tactical possibilities).

        Parameters:
            board (chess.Board): The chess board.
            alpha (float): The lower bound of the search window.
            beta (float): The upper bound of the search window.
            depth (int): max recursion limit

        Returns:
            int: The evaluated score after quiescence search.
        """
        stand_pat = self._evaluator.evaluate(board)
        if depth == 0:
            return stand_pat

        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        for move in (move for move in board.legal_moves if board.is_capture(move)):
            board.push(move)
            score = -self._quiescence(board, depth - 1, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> float:
        """
        Perform negamax search with alpha-beta pruning.

        Args:
            board: The current state of the chess board.
            depth: The remaining depth to search.
            alpha: The alpha value for alpha-beta pruning.
            beta: The beta value for alpha-beta pruning.

        Returns:
            The evaluation score of the current board position.

        Note:
            This method uses alpha-beta pruning for efficiency and includes
            move ordering using MVV-LVA.

        """
        self._statistics.increment()
        value = -float("inf")

        # Probe the transposition table for an existing entry
        hash_value = self._zorbist_hash.hash(board)
        tt_entry = self._transposition_table.probe(hash_value, depth)
        if tt_entry:
            return tt_entry["score"]

        # Base case: devolve to quiescence search
        # We currently only expect max 4 captures to reach a quiet position
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta)

        # Move ordering via MVV-LVA to encourage aggressive pruning
        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (self._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

        for move in legal_moves:
            # Depth-first search
            board.push(move)
            child_value = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            value = max(value, child_value)
            alpha = max(alpha, value)
            if alpha >= beta:
                self._transposition_table.store(hash, depth, value)
                break

        return value

    def _negamax_mp(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Negamax search with fail-soft alpha-beta pruning with top (root) level multiprocessing.

        :param board: The current chess board position.
        :type board: chess.Board
        :param depth: The current search depth.
        :type depth: int
        :param alpha: Alpha value for alpha-beta pruning.
        :type alpha: float
        :param beta: Beta value for alpha-beta pruning.
        :type beta: float
        :return: Tuple containing the best move and its value.
        :rtype: Tuple[float, chess.Move]
        """

        value = -float("inf")

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (self._mvv_lva_heuristic(board, move)),
            reverse=True,
        )

        best_move = legal_moves[0]

        def gen_board(move: chess.Move):
            new_board = board.copy()
            new_board.push(move)
            return new_board

        results = self._pool.map(
            lambda move: -self._negamax(gen_board(move), depth - 1, -beta, -alpha),
            legal_moves,
        )
        idx, value = max(enumerate(results), key=lambda x: x[1])
        best_move = legal_moves[idx]
        return value, best_move

    def search(self, board: chess.Board) -> chess.Move:
        """
        Perform a chess move search.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The recommended move based on the search.
        :rtype: chess.Move
        """
        self._statistics.reset()
        alpha = -float("inf")
        beta = float("inf")

        # TODO: add iterative deepening
        _, move = self._negamax_mp(board, self._max_depth, alpha, beta)
        return move
