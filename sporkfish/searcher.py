import chess
from typing import Tuple, Optional
from pathos.multiprocessing import ProcessPool
from multiprocessing import Manager
import stopit
import os
import logging
import time
import copy
import yaml

from .configurable import Configurable
from .evaluator import Evaluator
from .statistics import Statistics
from .transposition_table import TranspositionTable
from .zobrist_hasher import ZobristHasher
from enum import Enum


class SearchMode(Enum):
    SINGLE_PROCESS = "SINGLE_PROCESS"
    LAZY_SMP = "LAZY_SMP"


# _manager = Manager()
# We explicitly do not lock these and let race conditions happen
# Locks are too slow, need to consider atomic maps / values later
# This might cause underestimation of statistics.
# _dict = _manager.dict()
# _stats = _manager.Value("i", 0)

_dict: dict = dict()
_stats = 0


class SearcherConfig(Configurable):
    """Configuration class for the searcher.

    :param max_depth: Maximum depth for the search (default: 5).
    :type max_depth: int
    :param mode: Search mode (default: SearchMode.SINGLE_PROCESS).
    :type mode: SearchMode
    :param enable_transposition_table: Enable transposition table (default: True).
    :type enable_transposition_table: bool
    """

    def __init__(
        self,
        max_depth: int = 5,
        mode: SearchMode = SearchMode.SINGLE_PROCESS,
        enable_transposition_table: bool = False,
    ) -> None:
        self.max_depth = max_depth
        # TODO: register the constructor function in yaml loader instead.
        self.mode = mode if isinstance(mode, SearchMode) else SearchMode(mode)
        self.enable_transposition_table = enable_transposition_table


class Searcher:
    """
    Dynamic best move searching class.
    """

    def __init__(
        self, evaluator: Evaluator, config: SearcherConfig = SearcherConfig()
    ) -> None:
        """
        Initialize the Searcher instance with mutable statistics.

        :param evaluator: The chess board evaluator.
        :type evaluator: evaluator.Evaluator
        :param max_depth: The maximum search depth for the minimax algorithm.
                         Default is 5.
        :type max_depth: int
        :param config: Config to use for searching.
        :type mode: SearcherConfig
        :return: None
        """

        self._evaluator = evaluator
        self._config = config

        self._statistics = Statistics(_stats)

        if self._config.enable_transposition_table:
            self._zobrist_hash = ZobristHasher()
            self._transposition_table = TranspositionTable(_dict)
            logging.info("Enabled transposition table in search.")
        else:
            logging.info("Disabled transposition table in search.")

        if self._config.mode == SearchMode.LAZY_SMP:
            self._num_processes = os.cpu_count()
            self._pool = ProcessPool(nodes=self._num_processes)

    @property
    def evaluator(self) -> Evaluator:
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
        value = -float("inf")

        # Probe the transposition table for an existing entry
        if self._config.enable_transposition_table:
            hash_value = self._zobrist_hash.hash(board)
            tt_entry = self._transposition_table.probe(hash_value, depth)
            if tt_entry:
                return tt_entry["score"]  # type: ignore

        self._statistics.increment()

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

        if self._config.enable_transposition_table:
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
        best_move = chess.Move.null()
        self._statistics.increment()

        if self._config.enable_transposition_table:
            hash_value = self._zobrist_hash.hash(board)

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (self._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

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

    # This doesn't really work yet. Don't use.
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
        self, board: chess.Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Finds the best move (and associated score) via negamax and iterative deepening.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The best score and move based on the search.
        :param timeout: Time in seconds until we stop the search, returning the best depth if we timeout.
        :type timeout: Optional[float]
        :rtype: Tuple[float, chess.Move]
        """
        logging.info(f"Begin search for FEN {board.fen()}")

        @stopit.threading_timeoutable(
            default=(float("-inf"), chess.Move.null(), 0.0, 1)
        )
        def do_search_with_info(
            board_to_search: chess.Board,
            depth: int,
            start_time: float,
            alpha: float,
            beta: float,
        ) -> Tuple[float, chess.Move, float, int]:
            try:
                if self._config.mode is SearchMode.SINGLE_PROCESS:
                    score, move = self._negamax_sp(board_to_search, depth, alpha, beta)
                elif self._config.mode is SearchMode.LAZY_SMP:
                    score, move = self._negamax_lazy_smp(
                        board_to_search, depth, alpha, beta
                    )
                else:
                    raise TypeError("Invalid enum type given for SearchMode.")

                elapsed = time.time() - start_time
                fields = {
                    "depth": depth,
                    # time in ms
                    "time": int(1000 * elapsed),
                    "nodes": self._statistics.nodes_visited,
                    "nps": int(self._statistics.nodes_visited / elapsed)
                    if elapsed > 0
                    else 0,
                    "score cp": int(score)
                    if score not in {float("inf"), -float("inf")}
                    else float("nan"),
                    "pv": move,  # Incorrect but will do for now
                }
                info_str = " ".join(f"{k} {v}" for k, v in fields.items())
                logging.info(f"info {info_str}")
                return score, move, elapsed, 0
            except stopit.utils.TimeoutException:
                return float("-inf"), chess.Move.null(), 0.0, 1
            except Exception:
                raise

        time_left = timeout

        score = -float("inf")
        move = chess.Move.null()

        # Iterative deepening
        for depth in range(1, self._config.max_depth + 1):
            new_board = copy.deepcopy(board)

            alpha = -float("inf")
            beta = float("inf")

            self._statistics.reset()
            start_time = time.time()

            new_score, new_move, elapsed, error_code = do_search_with_info(
                timeout=time_left,
                board_to_search=new_board,
                depth=depth,
                start_time=start_time,
                alpha=alpha,
                beta=beta,
            )

            # Timed out, return best move from previous depth.
            if error_code:
                logging.warning(
                    f"Search for position {board.fen()} timed out after {timeout:.1f} seconds, returning best move from depth {depth - 1}."
                )
                break
            # Else move onto next depth, unless we have no more time already.
            else:
                score, move = new_score, new_move
                if time_left is not None:
                    time_left -= elapsed
                    if time_left <= 0:  # type: ignore
                        break

        logging.info(f"End search for FEN {board.fen()}.")

        return score, move
