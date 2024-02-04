import chess
import pytest
from init_board_helper import board_setup
from perf_helper import run_perf_analytics

from sporkfish.endgame_tablebase import EndgameTablebase, EndgameTablebaseConfig


def et_query(fen: str):
    board = chess.Board()
    board.set_fen(fen)
    et = EndgameTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
    move = et.query(board)
    return move


def et_query_expected(fen: str, move_expected: bool):
    move = et_query(fen)
    if move_expected:
        assert move, "Expected move but none returned."
    else:
        assert not move, "Didn't expect move but returned valid move."


class TestEndgameTablebase:
    def test_et_query_white_to_move_white_winning(self):
        et_query("8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1", True)

    def test_et_query_black_to_move_white_winning(self):
        et_query("8/4k3/8/8/8/8/3BB3/3K4 b - - 0 1", False)

    def test_et_query_black_to_move_white_winning_extra_queen(self):
        et_query("8/4k3/8/8/8/8/3BB3/3K1Q2 b - - 0 1", False)


@pytest.mark.parametrize(
    "fen_string",
    [
        "8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1",
        "8/4k3/8/8/8/8/3BB3/3K4 b - - 0 1",
        "8/4k3/8/8/8/8/3BB3/3K1Q2 b - - 0 1",
        board_setup["black"]["open"],
        board_setup["black"]["mid"],
        board_setup["black"]["end"],
    ],
)
class TestEndgameTablebasePerformance:
    @pytest.fixture
    def request_fixture(self, request):
        return request

    def test_et_query_perf(self, request_fixture, fen_string):
        run_perf_analytics(request_fixture.node.name, et_query, fen_string)
