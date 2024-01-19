import time

from sporkfish import engine, evaluator, opening_book, searcher
from sporkfish.board.board_factory import BoardFactory, BoardPyChess


def create_engine(depth: int) -> engine.Engine:
    ev = evaluator.Evaluator()
    search = searcher.Searcher(ev, searcher.SearcherConfig(depth))
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
