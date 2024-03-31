from sporkfish.lila_endgame_tablebase import LilaTablebase


class TestLilaEndgameTablebase:
    def test_lila_dtz_bestmove(self):
        test_fen = "8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1"
        lila_bestmove = LilaTablebase.query_bestmove(test_fen)
        if LilaTablebase.query_bestmove(test_fen) is not None:
            assert lila_bestmove
