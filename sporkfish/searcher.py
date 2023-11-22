import chess
from typing import Tuple
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
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
        self._transposition_table = transposition_table.TranspositionTable()
        self._killer_moves = {}

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
        }

        captured_piece = board.piece_at(move.to_square)
        if captured_piece is not None and board.is_capture(move):
            return piece_values.get(captured_piece.piece_type, 0)
        else:
            return 0

    def _killer_heuristic(self, move: chess.Move) -> int:
        return -self._killer_moves.get(move, 0)

    def _quiescence_search(
        self, board: chess.Board, depth: int, alpha: float, beta: float
    ) -> float:
        """
        Perform a quiescence search to improve the evaluation in non-capturing positions.

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
            score = -self._quiescence_search(board, depth - 1, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def _task(self, board, depth, alpha, beta):
        self._statistics.increment()
        value = -float("inf")
        best_move = None

        # Probe the transposition table for an existing entry
        hash = self._zorbist_hash.hash(board)
        tt_entry = self._transposition_table.probe(hash, depth)
        if tt_entry:
            return tt_entry["score"]

        # Base case: devolve to static evaluation via quiescence search
        if depth == 0:
            return self._quiescence_search(board, self._max_depth // 3, alpha, beta)

        # Move ordering via MVV-LVA and killer heuristic to encourage aggressive pruning
        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (
                self._mvv_lva_heuristic(board, move),
                self._killer_heuristic(move),
            ),
            reverse=True,
        )

        for move in legal_moves:
            # Depth first search
            board.push(move)
            child_value = -self._task(board, depth - 1, -beta, -alpha)
            board.pop()

            value = max(value, child_value)
            alpha = max(alpha, value)
            if alpha >= beta:
                self._transposition_table.store(hash, depth, value, best_move)
                self._killer_moves[best_move] = depth
                break

        return value

    def _negamax_search(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Negamax search with fail-soft alpha-beta pruning.

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
        best_move = None

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (
                self._mvv_lva_heuristic(board, move),
                self._killer_heuristic(move),
            ),
            reverse=True,
        )

        for move in legal_moves:
            board.push(move)
            child_value = -self._task(board, depth - 1, -beta, -alpha)
            board.pop()

            if child_value > value:
                value = child_value
                best_move = move

        return value, best_move

        # with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        #     results = []
        #     for move in legal_moves:
        #         new_board = board.copy()
        #         new_board.push(move)
        #         results.append(
        #             -executor.submit(
        #                 self._task, new_board, depth - 1, -beta, -alpha
        #             ).result()
        #         )

        #     idx, value = max(enumerate(results), key=lambda x: x[1])
        #     best_move = legal_moves[idx]
        #     return value, best_move

    def search(self, board: chess.Board) -> chess.Move:
        """
        Perform a chess move search.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The recommended move based on the search.
        :rtype: chess.Move
        """
        self._statistics.reset()
        best_move = None
        best_value = -float("inf")
        alpha = -float("inf")
        beta = float("inf")

        # Iterative deepening
        # for depth in range(1, self._max_depth + 1):
        value, move = self._negamax_search(board, self._max_depth, alpha, beta)
        if value > best_value:
            best_value = value
            best_move = move

        print(f"Nodes per second: {self._statistics.nodes_per_second()}")
        print(f"Total nodes visited: {self._statistics.nodes()}")
        return best_move
