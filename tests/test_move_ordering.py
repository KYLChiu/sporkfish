import chess
import pytest
from init_board_helper import board_setup, init_board

from sporkfish.searcher.move_ordering.composite_heuristic import (
    CompositeHeuristic,
)
from sporkfish.searcher.move_ordering.killer_move_heuristic import KillerMoveHeuristic
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.move_ordering.mvv_lva_heuristic import MvvLvaHeuristic
from sporkfish.searcher.move_ordering.history_heuristic import HistoryHeuristic

@pytest.mark.parametrize(
    ("fen_string", "move_scores"),
    [
        (board_setup["white"]["can_capture_queen"], [0, 50, 52]),
    ],
)
class TestMvvLvaHeuristic:
    def test_ordered_moves_end_game(
        self, fen_string: str, move_scores: list[int]
    ) -> None:
        board = init_board(fen_string)

        all_moves = board.legal_moves
        num_moves = len(move_scores)
        assert len(list(all_moves)) == num_moves

        for i, move in enumerate(all_moves):
            mo = MvvLvaHeuristic(board)
            score = mo.evaluate(move)
            assert score == move_scores[i]

    def test_sorting_legal_moves(self, fen_string: str, move_scores: list[int]) -> None:
        board = init_board(fen_string)

        mo_heuristic = MvvLvaHeuristic(board)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        num_moves = len(move_scores)
        for i, move in enumerate(legal_moves):
            score = mo_heuristic.evaluate(move)
            assert score == move_scores[num_moves - i - 1]


class TestKillerMoveHeuristic:
    def test_ordered_moves_end_game(self) -> None:
        board = init_board(board_setup["white"]["king_queen_fork"])

        all_moves = board.legal_moves
        killer_moves = [
            [chess.Move.null(), chess.Move.null()],
            [chess.Move.from_uci("c4b6"), chess.Move.null()],
        ]
        mo_heuristic = KillerMoveHeuristic(board, killer_moves, 1)

        for move in enumerate(all_moves):
            score = mo_heuristic.evaluate(move)
            assert score == (1 if move == chess.Move.from_uci("c4b6") else 0)

    def test_sorting_legal_moves(self) -> None:
        board = init_board(board_setup["white"]["king_queen_fork"])
        killer_moves = [
            [chess.Move.null(), chess.Move.null()],
            [chess.Move.from_uci("c4b6"), chess.Move.null()],
        ]
        mo_heuristic = KillerMoveHeuristic(board, killer_moves, 1)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        for i, move in enumerate(legal_moves):
            score = mo_heuristic.evaluate(move)
            assert score == (1 if i == 0 else 0)

class TestHistoryHeuristic:
    def test_history_heuristic(self) -> None:
        board = init_board(board_setup["white"]["king_queen_fork"])
        history_table = {
            chess.Move.from_uci("c4b6"): 10
        }
        mo_heuristic = HistoryHeuristic(board, history_table)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        for i, move in enumerate(legal_moves):
            score = mo_heuristic.evaluate(move)
            assert score == (10 if i == 0 else 0)

class TestCompositeHeuristic:
    def test_consistent_mvv_lva(self):
        board = init_board(board_setup["white"]["can_capture_queen"])

        base_heuristic = MvvLvaHeuristic(board)
        composite_heuristic = CompositeHeuristic(board, [[]], {}, 0)

        base_legal_moves = MoveOrderer.order_moves(base_heuristic, board.legal_moves)
        composite_legal_moves = MoveOrderer.order_moves(
            composite_heuristic, board.legal_moves
        )

        assert base_legal_moves == composite_legal_moves

    def test_consistent_killer(self):
        board = init_board(board_setup["white"]["king_queen_fork"])
        killer_moves = [
            [chess.Move.null(), chess.Move.null()],
            [chess.Move.from_uci("c4b6"), chess.Move.null()],
        ]
        base_heuristic = KillerMoveHeuristic(board, killer_moves, 1)
        composite_heuristic = CompositeHeuristic(board, killer_moves, {}, 1)

        base_legal_moves = MoveOrderer.order_moves(base_heuristic, board.legal_moves)
        composite_legal_moves = MoveOrderer.order_moves(
            composite_heuristic, board.legal_moves
        )

        assert base_legal_moves == composite_legal_moves

    def test_combined_score(self):
        """
        We test there are 3 positive scores in the list:
        - One for a fake/mock killer move
        - Two captures (MVV-LVA)
        """
        board = init_board(board_setup["white"]["can_capture_queen"])
        killer_moves = [
            [chess.Move.null(), chess.Move.null()],
            [chess.Move.from_uci("h2h3"), chess.Move.null()],
        ]
        composite_heuristic = CompositeHeuristic(board, killer_moves,{}, 1)

        pos_scores = sum(
            1 for move in board.legal_moves if composite_heuristic.evaluate(move) > 0
        )
        assert pos_scores == 3, "There should be 3 positive scores"

    def test_config(self):
        board = init_board(board_setup["white"]["can_capture_queen"])
        killer_moves = [
            [chess.Move.null(), chess.Move.null()],
            [chess.Move.null(), chess.Move.null()],
        ]
        composite_heuristic = CompositeHeuristic(board, killer_moves, {}, 1)

        for value in composite_heuristic._move_order_weights.values():
            assert isinstance(value, float)
