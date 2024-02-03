import chess

from sporkfish.endgame_tablebase import EndgameTablebase, EndgameTablebaseConfig


def et_query(fen: str, expected_move: bool):
    board = chess.Board()
    board.set_fen(fen)
    et = EndgameTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
    move = et.query(board)
    if expected_move:
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
