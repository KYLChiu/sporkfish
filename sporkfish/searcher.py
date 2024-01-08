import chess
from typing import Tuple
from pathos.multiprocessing import ProcessPool
from multiprocessing import Manager
import os
import logging

from .evaluator import Evaluator
from .statistics import Statistics
from .transposition_table import TranspositionTable
from .zobrist_hash import ZobristHash
from enum import Enum, auto


class SearchMode(Enum):
    SINGLE_PROCESS = auto()
    LAZY_SMP = auto()


class Searcher:
    """
    Dynamic best move searching class.
    """

    _manager = Manager()
    _dict = _manager.dict()
    _value = _manager.Value("i", 0)

    def __init__(
        self,
        evaluator: Evaluator,
        max_depth: int = 5,
        mode: SearchMode = SearchMode.SINGLE_PROCESS,
    ) -> None:
        """
        Initialize the Searcher instance with mutable statistics.

        :param evaluator: The chess board evaluator.
        :type evaluator: evaluator.Evaluator
        :param max_depth: The maximum search depth for the minimax algorithm.
                         Default is 5.
        :type max_depth: int
        :param node: Search type to use (e.g negamax single process or lazy SMP)
        :type mode: SearchMode
        :return: None
        """

        self._evaluator = evaluator
        self._max_depth = max_depth
        self._zorbist_hash = ZobristHash()
        self._statistics = Statistics(Searcher._value)
        self._transposition_table = TranspositionTable(Searcher._dict)
        self._mode = mode
        if self._mode is SearchMode.LAZY_SMP:
            self._pool = ProcessPool()

    @property
    def evaluator(self):
        return self._evaluator

    def _mvv_lva_heuristic(self, board: chess.Board, move: chess.Move) -> int:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value for a capturing move based on the value of the captured piece.

        Parameters:
            board (chess.Board): The chess board.
            move (chess.Move): The capturing move.

        Returns:
            int: The heuristic value of the capturing move based on the value of the captured piece.
        """
        # Columns: attacker P, N, B, R, Q, K
        MVV_LVA = [
            [15, 14, 13, 12, 11, 10],  # victim P
            [25, 24, 23, 22, 21, 10],  # victim N
            [35, 34, 33, 32, 31, 30],  # victim B
            [45, 44, 43, 42, 41, 40],  # victim R
            [55, 54, 53, 52, 51, 50],  # victim Q
            [0, 0, 0, 0, 0, 0],  # victim K
        ]

        captured_piece = board.piece_at(move.to_square)
        moving_piece = board.piece_at(move.from_square)

        if (
            captured_piece is not None
            and moving_piece is not None
            and board.is_capture(move)
        ):
            return MVV_LVA[captured_piece.piece_type - 1][moving_piece.piece_type - 1]
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

        self._statistics.increment()

        stand_pat = self._evaluator.evaluate(board)
        if depth == 0:
            return stand_pat

        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        legal_moves = sorted(
            (move for move in board.legal_moves if board.is_capture(move)),
            key=lambda move: (self._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

        for move in legal_moves:
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
        Negamax implementation alpha-beta pruning. For non-root nodes.

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
        # This is not ideal, but otherwise the search becomes incredibly slow
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta)

        # Move ordering via MVV-LVA to encourage aggressive pruning
        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (self._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

        for move in legal_moves:
            board.push(move)
            child_value = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            value = max(value, child_value)
            alpha = max(alpha, value)

            if alpha >= beta:
                break

        self._transposition_table.store(hash_value, depth, value)

        return value

    def _negamax_sp(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for negamax search with fail-soft alpha-beta pruning, single process.

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

        hash_value = self._zorbist_hash.hash(board)

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (self._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

        # Guarantee a move if available
        best_move = legal_moves[0] if len(legal_moves) > 0 else None
        if not best_move:
            return value, None

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

        self._transposition_table.store(hash_value, depth, value)

        return value, best_move

    def _negamax_lazy_smp(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for negamax search with fail-soft alpha-beta pruning with lazy symmetric multiprocessing.

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

        # Let processes race down lazily and see who completes first
        # We need to add more asymmetry but a task for later
        task = lambda _: self._negamax_sp(board, depth, alpha, beta)
        futures = []
        for i in range(os.cpu_count() // 2):
            futures.append(self._pool.apipe(task, i))

        while True:
            for future in futures:
                if future.ready():
                    return future.get()
            else:
                continue  # Continue the loop if no result is ready yet

    def search(self, board: chess.Board) -> Tuple[float, chess.Move]:
        """
        Perform a chess move search.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The best score and move based on the search.
        :rtype: Tuple[float, chess.Move]
        """
        self._statistics.reset()
        alpha = -float("inf")
        beta = float("inf")

        # TODO: add iterative deepening
        if self._mode is SearchMode.SINGLE_PROCESS:
            score, move = self._negamax_sp(board, self._max_depth, alpha, beta)
        elif self._mode is SearchMode.LAZY_SMP:
            score, move = self._negamax_lazy_smp(board, self._max_depth, alpha, beta)
        else:
            raise TypeError("Invalid enum type given for SearchMode.")

        fields = {
            "depth": self._max_depth,
            "time": round(1000 * self._statistics.start_time),
            "nodes": self._statistics.nodes_visited.value,
            "nps": int(self._statistics.nodes_per_second()),
            "score cp": int(score)
            if score not in {float("inf"), -float("inf")}
            else float("nan"),
            "pv": move,  # Incorrect but will do for now
        }
        info_str = " ".join(f"{k} {v}" for k, v in fields.items())
        logging.info(f"info {info_str}")

        return score, move
