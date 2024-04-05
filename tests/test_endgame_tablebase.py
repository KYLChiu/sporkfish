import pytest
from init_board_helper import board_setup
from perf_helper import run_perf_analytics

from sporkfish.board.board_factory import BoardPyChess
from sporkfish.endgame_tablebases.composite_tablebase import (
    CompositeTablebase,
    LocalTablebase,
)
from sporkfish.endgame_tablebases.endgame_tablebase_config import EndgameTablebaseConfig
from sporkfish.endgame_tablebases.lila_tablebase import LilaTablebase


def move_from_et_query(fen: str):
    board = BoardPyChess()
    board.set_fen(fen)
    et = LocalTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
    move = et.query(board)
    return move


class TestLocalTablebase:
    def _check_et_query_move_expected(
        self, test_name: str, fen: str, move_expected: bool
    ):
        move = move_from_et_query(fen)
        if move_expected:
            assert move, f"{test_name}: Expected move but none returned."
        else:
            assert not move, f"{test_name}: Didn't expect move but returned valid move."

    # Make sure an empty path doesn't crash
    def test_empty_path_tablebase(self):
        et = LocalTablebase(EndgameTablebaseConfig())
        et.query(BoardPyChess())

    @pytest.mark.parametrize(
        "test_name, fen, move_expected",
        [
            ("white_to_move_white_winning", "8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1", True),
            ("black_to_move_white_winning", "8/4k3/8/8/8/8/3BB3/3K4 b - - 0 1", False),
            (
                "black_to_move_white_winning_extra_queen",
                "8/4k3/8/8/8/8/3BB3/3K1Q2 b - - 0 1",
                False,
            ),
        ],
    )
    def test_et_query(self, test_name: str, fen: str, move_expected: bool):
        self._check_et_query_move_expected(test_name, fen, move_expected)

    def test_2nd_probe(self):
        board = BoardPyChess()
        board.set_fen("8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1")
        et = LocalTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
        move = et.query(board)
        board.push(move)
        # Play black move
        board.push(next(iter(board.legal_moves)))
        # Check there is a move returned on second probe
        # Cannot check dtz(move) > dtz(move2), this isn't public API unfortunately
        move2 = et.query(board)
        assert move2


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
        run_perf_analytics(request_fixture.node.name, move_from_et_query, fen_string)


class TestLilaEndgameTablebase:
    def test_lila_dtz_bestmove(self):
        board = BoardPyChess()
        board.set_fen("8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1")
        lila_bestmove = LilaTablebase().query(board)
        assert lila_bestmove


class TestCompositeTablebase:
    def test_composite_bestmove_empty(self):
        board = BoardPyChess()
        bestmove = CompositeTablebase().query(board)
        assert bestmove is None

    def test_composite_lila_bestmove(self):
        board = BoardPyChess()
        # We dont' have this in the local tablebase
        board.set_fen("8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1")
        lila_bestmove = CompositeTablebase(
            EndgameTablebaseConfig(endgame_tablebase_mode="LILA")
        ).query(board)
        assert lila_bestmove

    def test_composite_local_bestmove(self):
        board = BoardPyChess()
        # One step to mate
        board.set_fen("7k/8/7K/3B4/8/8/8/2B5 w - - 0 1")
        lila_bestmove = CompositeTablebase(
            EndgameTablebaseConfig(endgame_tablebase_mode="LILA")
        ).query(board)
        assert lila_bestmove
        # Check its equal to local bestmove
        local_bestmove = move_from_et_query(board.fen())
        assert lila_bestmove == local_bestmove
