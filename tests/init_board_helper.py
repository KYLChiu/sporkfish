import chess

white_move = {"open": "8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35",
              "mid": "8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35",
              "end": "8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35",
              "two_kings": "8/8/3kK3/8/8/8/8/8 w - - 1 34"}

black_move = {"open": "6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34",
              "mid": "6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34",
              "end": "6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34",
              "two_kings": "8/8/3kK3/8/8/8/8/8 b - - 1 34"}

board_setup = {"white": white_move,
               "black": black_move}


def init_board(fen_string: str):
    board = chess.Board()
    board.set_fen(fen_string)
    return board
