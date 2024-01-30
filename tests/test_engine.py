import time

from sporkfish import engine, evaluator, opening_book
from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory


def create_engine(depth: int) -> engine.Engine:
    ev = evaluator.Evaluator()
    search = SearcherFactory.create(SearcherConfig(depth), ev)
    ob = opening_book.OpeningBook()
    eng = engine.Engine(search, ob)
    return eng


def test_timeout() -> None:
    board = BoardFactory.create(BoardPyChess)
    eng = create_engine(100)
    start = time.time()
    _ = eng.score(board, 1e-3)
    # Timed out, impossible that depth 100 is <1 sec
    assert time.time() - start < 1
