import copy
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import chess
import stopit
from pathos.multiprocessing import ProcessPool

from ..board.board import Board
from ..evaluator import Evaluator
from ..statistics import Statistics
from ..transposition_table import TranspositionTable
from ..zobrist_hasher import ZobristHasher
from .minimax import MiniMaxVariants
from .move_ordering import MoveOrder, MvvLvaHeuristic
from .searcher import Searcher, SearchMode
from .searcher_config import SearcherConfig


class NegamaxSp(MiniMaxVariants):
    def __init__(
        self,
        evaluator: Evaluator,
        order: MoveOrder,
        config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, config)
        self.order = order

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

        Note:
            This method uses alpha-beta pruning for efficiency and includes
            move ordering using MVV-LVA.

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
            if self._null_move_pruning(depth, board, alpha, beta):
                return beta

        # Move ordering
        legal_moves = self._ordered_moves(board)

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

    def _searcher(
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

        if self._config.enable_transposition_table:
            hash_value = self._zobrist_hash.hash(board)

        legal_moves = self._ordered_moves(board)
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


# This doesn't really work yet. Don't use.
class NegaMaxLazySmp(NegamaxSp):
    def __init__(
        self,
        evaluator: Evaluator,
        order: MoveOrder,
        config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, order, config)

        self._num_processes = os.cpu_count()
        self._pool = ProcessPool(nodes=self._num_processes)

    # This doesn't really work yet. Don't use.
    def _searcher(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for negamax search with fail-soft alpha-beta pruning with lazy symmetric multiprocessing.

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

        # Let processes race down lazily and see who completes first
        # We need to add more asymmetry but a task for later
        def task(_):
            return self._searcher(board, depth, alpha, beta)

        futures = []
        for i in range(self._num_processes):  # type: ignore
            futures.append(self._pool.apipe(task, i))

        while True:
            for future in futures:
                if future.ready():
                    res: Tuple[float, chess.Move] = future.get()
                    return res
            else:
                continue  # Continue the loop if no result is ready yet

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
