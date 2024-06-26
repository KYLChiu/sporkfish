import time

from sporkfish import engine, opening_book
from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.endgame_tablebases.endgame_tablebase_config import EndgameTablebaseConfig
from sporkfish.endgame_tablebases.local_tablebase import LocalTablebase
from sporkfish.evaluator.pesto import Pesto
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory


def create_engine(depth: int) -> engine.Engine:
    evaluator = Pesto()
    search = SearcherFactory.create(SearcherConfig(depth), evaluator)
    ob = opening_book.OpeningBook()
    et = LocalTablebase(EndgameTablebaseConfig("data/endgame_tablebases"))
    eng = engine.Engine(search, ob, et)
    return eng


def test_timeout() -> None:
    board = BoardFactory.create(BoardPyChess)
    eng = create_engine(100)
    start = time.time()
    _ = eng.score(board, 1e-3)
    # Timed out, impossible that depth 100 is <1 sec
    assert time.time() - start < 1
