from typing import Optional, Tuple

import chess

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.searcher.minimax import MiniMaxVariants
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.statistics import NodeTypes, PruningTypes, TranspositionTable
from sporkfish.zobrist_hasher import ZobristStateInfo


class PVSSp(MiniMaxVariants):
    def __init__(
        self,
        evaluator: Evaluator,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, searcher_config)

    def _pvs(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        zobrist_state: Optional[ZobristStateInfo],
    ) -> float:
        """
        Principal Variation Search implementation with alpha-beta pruning. For non-root nodes.

        :param board: The current state of the chess board.
        :type board: Board
        :param depth: The remaining depth to search.
        :type depth: int
        :param alpha: The alpha value for alpha-beta pruning.
        :type alpha: float
        :param beta: The beta value for alpha-beta pruning.
        :type beta: float
        :param zobrist_state: The Zobrist hash state information.
        :type zobrist_state: Optional[ZobristStateInfo]

        :returns: The evaluation score of the current board position.
        :rtype: float
        """
        value = -float("inf")

        # Base case: devolve to quiescence search
        # We currently only expect max 4 captures to reach a quiet (non-capturing) position
        # This is not ideal, but otherwise the search becomes incredibly slow
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta, zobrist_state)

        # Probe the transposition table for an existing entry
        if zobrist_state and (
            tt_entry := self._transposition_table.probe(
                zobrist_state.zobrist_hash, depth
            )
        ):
            self._statistics.increment_visited(TranspositionTable.TRANSPOSITITON_TABLE)
            return tt_entry["score"]  # type: ignore

        self._statistics.increment_visited(NodeTypes.NEGAMAX)

        # Null move pruning - reduce the search space by trying a null move,
        # then seeing if the score of the subtree search is still high enough to cause a beta cutoff
        if self._searcher_config.enable_null_move_pruning and self._null_move_pruning(
            board, depth, alpha, beta, self._pvs
        ):
            self._statistics.increment_visited(PruningTypes.NULL_MOVE)
            return beta

        # Move ordering
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        # Recursive search with alpha-beta pruning
        for idx, move in enumerate(legal_moves):
            # Get captures for futility pruning or transposition table
            # Get piece at previous from_square for transposition table
            # This needs to be done prior to changing the board state
            previous_piece_from_square = (
                board.piece_at(move.from_square) if zobrist_state else None
            )
            capture = (
                board.is_capture(move)
                if self._searcher_config.enable_futility_pruning or zobrist_state
                else False
            )
            captured_piece = (
                board.piece_at(move.to_square) if zobrist_state and capture else None
            )

            board.push(move)

            # Futility pruning
            if self._searcher_config.enable_futility_pruning and self._futility_pruning(
                board, depth, capture, move, alpha
            ):
                board.pop()
                self._statistics.increment_visited(PruningTypes.FUTILITY)
                continue

            # Update the Zobrist hash
            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    previous_piece_from_square,  # type: ignore
                    captured_piece,
                )
                if zobrist_state
                else None
            )

            # If it's the first move, we do a full window search
            if idx == 0:
                child_value = -self._pvs(
                    board, depth - 1, -beta, -alpha, child_zobrist_state
                )
            # Otherwise, we do a null window search first
            # If the value is within the bounds, we do a full window search
            else:
                child_value = -self._pvs(
                    board, depth - 1, -alpha - 1, -alpha, child_zobrist_state
                )
                if alpha < child_value < beta:
                    child_value = -self._pvs(
                        board, depth - 1, -beta, -alpha, child_zobrist_state
                    )

            board.pop()

            value = max(value, child_value)
            alpha = max(alpha, value)

            if alpha >= beta:
                self._update_killer_moves(move, depth)
                break

        if zobrist_state:
            self._transposition_table.store(zobrist_state.zobrist_hash, depth, value)

        return value

    def _start_search_from_root(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for principal variation search with fail-soft alpha-beta pruning, single process.

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
        self._statistics.increment_visited(NodeTypes.NEGAMAX)

        zobrist_state = (
            self._zobrist_hash.full_zobrist_hash(board)
            if self._searcher_config.enable_transposition_table
            else None
        )
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        for idx, move in enumerate(legal_moves):
            # Get piece at from_square and captures for transposition table
            # This needs to be done prior to changing the board state
            previous_piece_from_square = (
                board.piece_at(move.to_square) if zobrist_state else None
            )
            captured_piece = (
                board.piece_at(move.to_square)
                if zobrist_state and board.is_capture(move)
                else None
            )

            board.push(move)

            # Update the Zobrist hash
            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    previous_piece_from_square,  # type: ignore
                    captured_piece,
                )
                if zobrist_state
                else None
            )

            # If it's the first move, we do a full window search
            if idx == 0:
                child_value = -self._pvs(
                    board, depth - 1, -beta, -alpha, child_zobrist_state
                )
            # Otherwise, we do a null window search first
            # If the value is within the bounds, we do a full window search
            else:
                child_value = -self._pvs(
                    board, depth - 1, -alpha - 1, -alpha, child_zobrist_state
                )
                if alpha < child_value < beta:
                    child_value = -self._pvs(
                        board, depth - 1, -beta, -alpha, child_zobrist_state
                    )

            board.pop()

            if value < child_value:
                value = child_value
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                self._update_killer_moves(move, depth)
                self._statistics.increment_visited(PruningTypes.ALPHA_BETA)
                break

        if zobrist_state:
            self._transposition_table.store(zobrist_state.zobrist_hash, depth, value)

        return value, best_move

    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Finds the best move (and associated score) via PVS and iterative deepening.

        :param board: The current chess board position.
        :type board: Board
        :return: The best score and move based on the search.
        :param timeout: Time in seconds until we stop the search, returning the best depth if we timeout.
        :type timeout: Optional[float]
        :rtype: Tuple[float, Move]
        """
        score, move = self._iterative_deepening_search(board, timeout)
        return score, move
