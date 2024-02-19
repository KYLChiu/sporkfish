from sporkfish import evaluator
from sporkfish.board.board_factory import Board, BoardFactory, BoardPyChess

white_move = {
    "open": "rnbqkb1r/pppp1ppp/4pn2/8/3P1B2/8/PPP1PPPP/RN1QKBNR w KQkq - 0 3",
    "mid": "r1b2rk1/ppqn1pbp/6p1/3pp3/7B/2PB1N2/PP3PPP/R2QR1K1 w - - 0 16",
    "end": "3k4/5ppp/2q5/3p2r1/8/1Q3P2/P4P1P/3R3K w - - 0 1",
    "two_kings": "8/8/4K3/8/2k5/8/8/8 w - - 1 34",
    "two_kings_one_pawn": "8/8/4K3/2k5/2p5/8/8/8 w - - 1 34",  # black winning
    "king_queen_fork": "k7/3q4/8/K7/2N5/8/8/8 w - - 1 34",
}

black_move = {
    "open": "rnbqkb1r/pppppppp/5n2/8/3P1B2/8/PPP1PPPP/RN1QKBNR b KQkq - 2 2",
    "mid": "r1b2rk1/ppq2ppp/3bpn2/3pP3/8/2PB2B1/PP1N1PPP/R2QK2R b KQ - 0 11",
    "end": "8/8/8/8/5R2/2pk4/5K2/8 b - - 0 1",
    "two_kings": "8/8/4K3/8/2k5/8/8/8 b - - 1 34",
    "two_kings_one_pawn": "8/8/4K3/2k5/2p5/8/8/8 b - - 1 34",  # black winning
}

board_setup = {"white": white_move, "black": black_move}


def init_board(fen_string: str) -> Board:
    """
    Initialise chess board using FEN string
    https://www.dailychess.com/chess/chess-fen-viewer.php
    """
    board = BoardFactory.create(BoardPyChess)
    board.set_fen(fen_string)
    return board


def score_fen(fen_string: str) -> float:
    """
    Compute score based on a specific chess board
    """
    board = init_board(fen_string)
    ev = evaluator.Evaluator()
    return ev.evaluate(board)
