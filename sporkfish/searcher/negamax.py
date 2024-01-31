from typing import Optional, Tuple

import chess

from ..board.board import Board
from ..evaluator import Evaluator
from .minimax import MiniMaxVariants
from .move_ordering import MoveOrder
from .searcher_config import SearcherConfig


class NegamaxSp(MiniMaxVariants):
    def __init__(
        self,
        evaluator: Evaluator,
        move_order: MoveOrder,
        config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, move_order, config)

    def _negamax(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> float:
        """
        Negamax implementation with alpha-beta pruning. For non-root nodes.

        Args:
            board: The current state of the chess board.
            depth: The remaining depth to search.
            alpha: The alpha value for alpha-beta pruning.
            beta: The beta value for alpha-beta pruning.

        Returns:
            The evaluation score of the current board position.
        """
        value = -float("inf")

        # Probe the transposition table for an existing entry
        if self._config.enable_transposition_table:
            hash_value = self._zobrist_hash.hash(board)
            tt_entry = self._transposition_table.probe(hash_value, depth)
            if tt_entry:
                return tt_entry["score"]  # type: ignore

        self._statistics.increment()

        # Base case: devolve to quiescence search
        # We currently only expect max 4 captures to reach a quiet (non-capturing) position
        # This is not ideal, but otherwise the search becomes incredibly slow
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta)

        # Null move pruning - reduce the search space by trying a null move,
        # then seeing if the score of the subtree search is still high enough to cause a beta cutoff
        if self._config.enable_null_move_pruning:
            if self._null_move_pruning(board, depth, alpha, beta):
                return beta

        # Move ordering
        legal_moves = self._ordered_moves(board, board.legal_moves)

        # recursive search with alpha-beta pruning
        for move in legal_moves:
            board.push(move)
            child_value = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            value = max(value, child_value)
            alpha = max(alpha, value)

            if alpha >= beta:
                break

        if self._config.enable_transposition_table:
            self._transposition_table.store(hash_value, depth, value)

        return value

    def _null_move_pruning(
        self, board: Board, depth: int, alpha: float, beta: float
    ) -> bool:
        """
        Null move pruning - reduce the search space by trying a null move,
        then seeing if the score of the subtree search is still high enough to cause a beta cutoff
        """
        # TODO: add zugzwang check
        # Will make depth_reduction_factor configurable later
        depth_reduction_factor = 3
        in_check = board.is_check()
        if depth >= depth_reduction_factor and not in_check:
            null_move_depth = depth - depth_reduction_factor
            board.push(chess.Move.null())
            value = -self._negamax(board, null_move_depth, -beta, -alpha)
            board.pop()
            if value >= beta:
                return True
        return False

    def _start_search_from_root(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for negamax search with fail-soft alpha-beta pruning, single process.

        :param board: The current chess board position.
        :type board: Board
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
        best_move = chess.Move.null()
        self._statistics.increment()

        legal_moves = self._ordered_moves(board, board.legal_moves)
        for move in legal_moves:
            board.push(move)
            child_value = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            if value < child_value:
                value = child_value
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                break

        if self._config.enable_transposition_table:
            hash_value = self._zobrist_hash.hash(board)
            self._transposition_table.store(hash_value, depth, value)

        return value, best_move

    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Finds the best move (and associated score) via negamax and iterative deepening.

        :param board: The current chess board position.
        :type board: Board
        :return: The best score and move based on the search.
        :param timeout: Time in seconds until we stop the search, returning the best depth if we timeout.
        :type timeout: Optional[float]
        :rtype: Tuple[float, Move]
        """

        score, move = self._iterative_deepening(board, timeout)
        return score, move
