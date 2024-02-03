import time

from sporkfish import engine, evaluator, opening_book
from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.endgame_tablebase import EndgameTablebase, EndgameTablebaseConfig
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory
import chess

def create_engine(depth: int) -> engine.Engine:
    search = SearcherFactory.create(SearcherConfig(depth))
    ob = opening_book.OpeningBook()
    et = EndgameTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
    eng = engine.Engine(search, ob, et)
    return eng


def test_timeout() -> None:
    board = BoardFactory.create(BoardPyChess)
    eng = create_engine(100)
    start = time.time()
    _ = eng.score(board, 1e-3)
    # Timed out, impossible that depth 100 is <1 sec
    assert time.time() - start < 1


def use_endgame_tablebase(fen: str, expected_move: bool):
    engine = create_engine(1)
    board = BoardFactory.create(BoardPyChess)
    board.set_fen(fen)
    assert bool(engine._use_endgame_tablebase(board)) is expected_move

class TestEngine:
    def test_use_endgame_tablebase(self):
        use_endgame_tablebase("8/4k3/8/8/8/8/3BB3/3K4 w - - 0 1", True)
        use_endgame_tablebase('8/4k3/4ppp1/8/8/Q7/3BB3/3K4 b - - 0 1', False)
