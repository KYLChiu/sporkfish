import chess

import sporkfish.communicator_uci as communicator_uci
import sporkfish.engine as engine
import sporkfish.evaluator as evaluator
import sporkfish.searcher as searcher
import sporkfish.opening_book as opening_book
import sporkfish.utils as utils

if __name__ == "__main__":
    # Config should eventually go in engine_config
    depth = 4
    board = chess.Board()
    evaluator = evaluator.Evaluator()
    searcher = searcher.Searcher(evaluator, depth)
    opening_book = opening_book.OpeningBook()
    engine = engine.Engine(searcher, opening_book)

    @utils.run_with_except_msg
    def run():
        communicator_uci.CommunicatorUCI().communicate_loop(board, engine)

    run()
