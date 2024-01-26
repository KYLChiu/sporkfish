import copy
import logging
import os
import time
from enum import Enum
from multiprocessing import Manager
from typing import Callable, Optional, Tuple

import chess
import stopit
from pathos.multiprocessing import ProcessPool

from .board.board import Board
from .configurable import Configurable
from .evaluator import Evaluator
from .statistics import Statistics
from .transposition_table import TranspositionTable
from .zobrist_hasher import ZobristHasher


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
    :param enable_null_move_pruning: Enable null-move pruning (default: True).
    :type enable_null_move_pruning: bool
    :param enable_transposition_table: Enable transposition table (default: True).
    :type enable_transposition_table: bool
    """

    def __init__(
        self,
        max_depth: int = 5,
        mode: SearchMode = SearchMode.SINGLE_PROCESS,
        enable_null_move_pruning: bool = True,
        enable_transposition_table: bool = False,
        enable_aspiration_windows: bool = True,
    ) -> None:
        self.max_depth = max_depth
        # TODO: register the constructor function in yaml loader instead.
        self.mode = mode if isinstance(mode, SearchMode) else SearchMode(mode)
        self.enable_null_move_pruning = enable_null_move_pruning
        self.enable_transposition_table = enable_transposition_table
        self.enable_aspiration_windows = enable_aspiration_windows


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
                         Def.ault is 5.
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

    def _mvv_lva_heuristic(self, board: Board, move: chess.Move) -> int:
        """
        Calculate the Most Valuable Victim - Least Valuable Aggressor heuristic value for a capturing move based on the value of the captured piece.

        Parameters:
            board (Board): The chess board.
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

    def _quiescence(self, board: Board, depth: int, alpha: float, beta: float) -> float:
        """
        Quiescence search to help the horizon effect (improving checking of tactical possibilities).

        Parameters:
            board (Board): The chess board.
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
        board: Board,
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

        # Null move pruning - reduce the search space by trying a null move,
        # then seeing if the score of the subtree search is still high enough to cause a beta cutoff
        if self._config.enable_null_move_pruning:
            # TODO: add zugzwang check
            depth_reduction_factor = 3
            in_check = board.is_check()
            if depth >= depth_reduction_factor and not in_check:
                null_move_depth = depth - depth_reduction_factor
                board.push(chess.Move.null())
                value = -self._negamax(board, null_move_depth, -beta, -alpha)
                board.pop()
                if value >= beta:
                    return beta

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

    # Aspiriation windows
    # Assumption (*): we expect the search score from depth n should be somewhat similar depth n + 1.
    # Method: set alpha = prev_depth_score - constant, beta = prev_depth_score + constant.
    # Do a search with narrower window [alpha, beta] as opposed to [-inf, inf].
    # This should cause cutoffs (if they do happen) to happen faster.
    # If the score falls within the alpha/beta bounds, our assumption (*) holds - so take that score.
    # If the score falls outside the alpha/beta windows, the score changed too much
    # i.e. our assumption (*) is false - so we do a full search to be safe.
    def _aspiration_windows_search(
        self,
        search_func: Callable[[Board, int, float, float], Tuple[float, chess.Move]],
        board_to_search: Board,
        depth: int,
        prev_score: float,
    ) -> Tuple[float, chess.Move]:
        """
        Perform an aspiration windows search.

        Aspiration windows are used to optimize the search process by narrowing the search window based on
        previous search results.

        :param search_func: A callable function representing the search algorithm.
        :type search_func: Callable[[Board, int, float, float], Tuple[float, chess.Move]]
        :param board_to_search: The chess board to search.
        :type board_to_search: Board
        :param depth: The search depth.
        :type depth: int
        :param prev_score: The score of the previous depth in a iterative deepening search.
        :type prev_score: float

        :return: A tuple containing the score and the best move found during the search.
        :rtype: Tuple[float, chess.Move]
        """
        if self._config.enable_aspiration_windows and depth > 1:
            # Aspiration window size: 50 centipawn is worth about 1/2 of a pawn in our eval function
            # We leave configuration for this to another PR
            window_size = 50
            alpha = prev_score - window_size
            beta = prev_score + window_size
            score, move = search_func(board_to_search, depth, alpha, beta)
            if score <= alpha or score >= beta:
                logging.info(
                    "Search score outside aspiration window bounds, doing a full search."
                )
                score, move = search_func(
                    board_to_search, depth, -float("inf"), float("inf")
                )
        else:
            score, move = search_func(
                board_to_search, depth, -float("inf"), float("inf")
            )
        return score, move

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
        logging.info(f"Begin search for FEN {board.fen()}")

        @stopit.threading_timeoutable(
            default=(float("-inf"), chess.Move.null(), 0.0, 1)
        )
        def do_search_with_info(
            board_to_search: Board,
            depth: int,
            start_time: float,
            prev_score: float,
        ) -> Tuple[float, chess.Move, float, int]:
            try:
                if self._config.mode is SearchMode.SINGLE_PROCESS:
                    score, move = self._aspiration_windows_search(
                        self._negamax_sp, board_to_search, depth, prev_score
                    )
                elif self._config.mode is SearchMode.LAZY_SMP:
                    score, move = self._aspiration_windows_search(
                        self._negamax_lazy_smp,
                        board_to_search,
                        depth,
                        prev_score,
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
                if move == chess.Move.null():
                    raise RuntimeError(
                        f"Null move returned in search for position {board.fen()}."
                    )
                return score, move, elapsed, 0
            except stopit.utils.TimeoutException:
                return float("-inf"), chess.Move.null(), 0.0, 1
            except Exception:
                raise

        time_left = timeout

        score = -float("inf")
        move = chess.Move.null()

        # Iterative deepening
        # This conducts a fixed-depth search for depths ranging from 1 to max_depth.
        # 1) It enables the transposition table (cache) to be easily utilized.
        # 2) If time constraints prevent a complete search, the function can return the best move found up to the previous depth.
        # 3) It facilitates the use of aspiration windows, as implemented in the _aspiration_windows_search function.
        for depth in range(1, self._config.max_depth + 1):
            new_board = copy.deepcopy(board)

            self._statistics.reset()
            start_time = time.time()

            new_score, new_move, elapsed, error_code = do_search_with_info(
                timeout=time_left,
                board_to_search=new_board,
                depth=depth,
                start_time=start_time,
                prev_score=score,
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
                alpha, beta = score, score
                if time_left is not None:
                    time_left -= elapsed
                    if time_left <= 0:  # type: ignore
                        break

        logging.info(f"End search for FEN {board.fen()}.")

        return score, move
