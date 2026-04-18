from typing import Dict, Optional

import chess

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator


class Pesto(Evaluator):
    """
    A class responsible for evaluating the chess position.
    Using Piece-Square Table Only (PeSTO) evaluation at the moment, see:
    https://github.com/KYLChiu/sporkfish/issues/88

    Methods:
    - evaluate(board: Board) -> float:
        Evaluate the chess position based on material and piece-square tables.
    """

    MG_PIECE_VALUES = {
        chess.PAWN: 82.0,
        chess.KNIGHT: 337.0,
        chess.BISHOP: 365.0,
        chess.ROOK: 477.0,
        chess.QUEEN: 1025.0,
        chess.KING: 12000.0,
    }

    EG_PIECE_VALUES = {
        chess.PAWN: 94.0,
        chess.KNIGHT: 281.0,
        chess.BISHOP: 297.0,
        chess.ROOK: 512.0,
        chess.QUEEN: 936.0,
        chess.KING: 12000.0,
    }

    # Delta pruning margin for searcher, evaluator dependent
    DELTA = 200.0

    # fmt: off

    MG_PAWN = (
                82, 82, 82, 82, 82, 82, 82, 82,
                180, 216, 143, 177, 150, 208, 116, 71,
                76, 89, 108, 113, 147, 138, 107, 62,
                68, 95, 88, 103, 105, 94, 99, 59,
                55, 80, 77, 94, 99, 88, 92, 57,
                56, 78, 78, 72, 85, 85, 115, 70,
                47, 81, 62, 59, 67, 106, 120, 60,
                82, 82, 82, 82, 82, 82, 82, 82,
                )

    EG_PAWN = (
                94, 94, 94, 94, 94, 94, 94, 94,
                272, 267, 252, 228, 241, 226, 259, 281,
                188, 194, 179, 161, 150, 147, 176, 178,
                126, 118, 107, 99, 92, 98, 111, 111,
                107, 103, 91, 87, 87, 86, 97, 93,
                98, 101, 88, 95, 94, 89, 93, 86,
                107, 102, 102, 104, 107, 94, 96, 87,
                94, 94, 94, 94, 94, 94, 94, 94,
                )


    MG_KNIGHT = (
                170, 248, 303, 288, 398, 240, 322, 230,
                264, 296, 409, 373, 360, 399, 344, 320,
                290, 397, 374, 402, 421, 466, 410, 381,
                328, 354, 356, 390, 374, 406, 355, 359,
                324, 341, 353, 350, 365, 356, 358, 329,
                314, 328, 349, 347, 356, 354, 362, 321,
                308, 284, 325, 334, 336, 355, 323, 318,
                232, 316, 279, 304, 320, 309, 318, 314,
                )

    EG_KNIGHT = (
                223, 243, 268, 253, 250, 254, 218, 182,
                256, 273, 256, 279, 272, 256, 257, 229,
                257, 261, 291, 290, 280, 272, 262, 240,
                264, 284, 303, 303, 303, 292, 289, 263,
                263, 275, 297, 306, 297, 298, 285, 263,
                258, 278, 280, 296, 291, 278, 261, 259,
                239, 261, 271, 276, 279, 261, 258, 237,
                252, 230, 258, 266, 259, 263, 231, 217,
                )

    MG_BISHOP = (
                336, 369, 283, 328, 340, 323, 372, 357,
                339, 381, 347, 352, 395, 424, 383, 318,
                349, 402, 408, 405, 400, 415, 402, 363,
                361, 370, 384, 415, 402, 402, 372, 363,
                359, 378, 378, 391, 399, 377, 375, 369,
                365, 380, 380, 380, 379, 392, 383, 375,
                369, 380, 381, 365, 372, 386, 398, 366,
                332, 362, 351, 344, 352, 353, 326, 344,
                )

    EG_BISHOP = (
                283, 276, 286, 289, 290, 288, 280, 273,
                289, 293, 304, 285, 294, 284, 293, 283,
                299, 289, 297, 296, 295, 303, 297, 301,
                294, 306, 309, 306, 311, 307, 300, 299,
                291, 300, 310, 316, 304, 307, 294, 288,
                285, 294, 305, 307, 310, 300, 290, 282,
                283, 279, 290, 296, 301, 288, 282, 270,
                274, 288, 274, 292, 288, 281, 292, 280,
                )

    MG_ROOK = (
                509, 519, 509, 528, 540, 486, 508, 520,
                504, 509, 535, 539, 557, 544, 503, 521,
                472, 496, 503, 513, 494, 522, 538, 493,
                453, 466, 484, 503, 501, 512, 469, 457,
                441, 451, 465, 476, 486, 470, 483, 454,
                432, 452, 461, 460, 480, 477, 472, 444,
                433, 461, 457, 468, 476, 488, 471, 406,
                458, 464, 478, 494, 493, 484, 440, 451,
                )

    EG_ROOK = (
                525, 522, 530, 527, 524, 524, 520, 517,
                523, 525, 525, 523, 509, 515, 520, 515,
                519, 519, 519, 517, 516, 509, 507, 509,
                516, 515, 525, 513, 514, 513, 511, 514,
                515, 517, 520, 516, 507, 506, 504, 501,
                508, 512, 507, 511, 505, 500, 504, 496,
                506, 506, 512, 514, 503, 503, 501, 509,
                503, 514, 515, 511, 507, 499, 516, 492,
                )

    MG_QUEEN = (
                997, 1025, 1054, 1037, 1084, 1069, 1068, 1070,
                1001, 986, 1020, 1026, 1009, 1082, 1053, 1079,
                1012, 1008, 1032, 1033, 1054, 1081, 1072, 1082,
                998, 998, 1009, 1009, 1024, 1042, 1023, 1026,
                1016, 999, 1016, 1015, 1023, 1021, 1028, 1022,
                1011, 1027, 1014, 1023, 1020, 1027, 1039, 1030,
                990, 1017, 1036, 1027, 1033, 1040, 1022, 1026,
                1024, 1007, 1016, 1035, 1010, 1000, 994, 975,
                )

    EG_QUEEN = (
                927, 958, 958, 963, 963, 955, 946, 956,
                919, 956, 968, 977, 994, 961, 966, 936,
                916, 942, 945, 985, 983, 971, 955, 945,
                939, 958, 960, 981, 993, 976, 993, 972,
                918, 964, 955, 983, 967, 970, 975, 959,
                920, 909, 951, 942, 945, 953, 946, 941,
                914, 913, 906, 920, 920, 913, 900, 904,
                903, 908, 914, 893, 931, 904, 916, 895,
                )

    MG_KING = (
                11935, 12023, 12016, 11985, 11944, 11966, 12002, 12013,
                12029, 11999, 11980, 11993, 11992, 11996, 11962, 11971,
                11991, 12024, 12002, 11984, 11980, 12006, 12022, 11978,
                11983, 11980, 11988, 11973, 11970, 11975, 11986, 11964,
                11951, 11999, 11973, 11961, 11954, 11956, 11967, 11949,
                11986, 11986, 11978, 11954, 11956, 11970, 11985, 11973,
                12001, 12007, 11992, 11936, 11957, 11984, 12009, 12008,
                11985, 12036, 12012, 11946, 12008, 11972, 12024, 12014,
                )

    EG_KING = (
                11926, 11965, 11982, 11982, 11989, 12015, 12004, 11983,
                11988, 12017, 12014, 12017, 12017, 12038, 12023, 12011,
                12010, 12017, 12023, 12015, 12020, 12045, 12044, 12013,
                11992, 12022, 12024, 12027, 12026, 12033, 12026, 12003,
                11982, 11996, 12021, 12024, 12027, 12023, 12009, 11989,
                11981, 11997, 12011, 12021, 12023, 12016, 12007, 11991,
                11973, 11989, 12004, 12013, 12014, 12004, 11995, 11983,
                11947, 11966, 11979, 11989, 11972, 11986, 11976, 11957,
                )

    # fmt : on

    # Piece-Square tables ordered by piece_type-1 (PAWN=0 … KING=5).
    # Using tuples instead of {chess.PieceType: table} dicts eliminates enum.__hash__
    # in the hot evaluate loop — piece_type is an IntEnum so integer subtraction and
    # direct tuple indexing is much faster than a dict lookup.
    MG_PESTO = (
        MG_PAWN,
        MG_KNIGHT,
        MG_BISHOP,
        MG_ROOK,
        MG_QUEEN,
        MG_KING,
    )

    EG_PESTO = (
        EG_PAWN,
        EG_KNIGHT,
        EG_BISHOP,
        EG_ROOK,
        EG_QUEEN,
        EG_KING,
    )

    # Game-phase weights in the same order (PAWN=0, KNIGHT=1, BISHOP=1, ROOK=2, QUEEN=4, KING=0).
    PHASES = (0, 1, 1, 2, 4, 0)

    SQUARES = [i for i in range(64)]
    VERTICALLY_FLIPPED_SQUARES = [i ^ 56 for i in range(64)]

    def __init__(self) -> None:
        self._accum: Optional["PestoAccumulator"] = None

    def evaluate(self, board: Board) -> float:
        """
        Evaluate the chess position based on material and piece-square tables.

        If ``init_from_board`` has been called (i.e. the searcher is driving
        incremental updates via ``on_push``/``on_pop``), the result is O(1).
        Otherwise a full O(pieces) scan is performed as a fallback.

        :param board: The current chess board position.
        :type board: Board
        :return: The evaluation score.
        :rtype: float
        """
        if self._accum is not None:
            mg_white = self._accum.mg_white
            mg_black = self._accum.mg_black
            eg_white = self._accum.eg_white
            eg_black = self._accum.eg_black
            phase = self._accum.phase
        else:
            mg_white = mg_black = eg_white = eg_black = 0
            phase = 0
            for piece_type in chess.PIECE_TYPES:
                pt_idx = piece_type - 1
                mg_table = self.MG_PESTO[pt_idx]
                eg_table = self.EG_PESTO[pt_idx]
                phase_inc = self.PHASES[pt_idx]
                for chess_sq in board.pieces(piece_type, chess.WHITE):
                    idx = chess_sq ^ 56
                    mg_white += mg_table[idx]
                    eg_white += eg_table[idx]
                    phase += phase_inc
                for chess_sq in board.pieces(piece_type, chess.BLACK):
                    mg_black += mg_table[chess_sq]
                    eg_black += eg_table[chess_sq]
                    phase += phase_inc

        if board.turn:  # chess.WHITE
            mg_score = mg_white - mg_black
            eg_score = eg_white - eg_black
        else:           # chess.BLACK
            mg_score = mg_black - mg_white
            eg_score = eg_black - eg_white

        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        return ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

    def init_from_board(self, board: Board) -> None:
        """Initialise (or re-initialise) the incremental accumulator from the board."""
        self._accum = PestoAccumulator(board)

    def on_push(self, board: Board, move: chess.Move) -> None:
        if self._accum is not None:
            self._accum.on_push(board, move)

    def on_pop(self) -> None:
        if self._accum is not None:
            self._accum.on_pop()

    def piece_values(self) -> Dict[chess.PieceType, float]:
        """
        Return the piece values for the evaluator.

        :return: The piece values.
        :rtype: Dict[chess.PieceType, float]
        """
        return self.MG_PIECE_VALUES

    def delta(self) -> float:
        """
        Return the delta threshold for futility pruning for the evaluator.

        :return: The delta.
        :rtype: float
        """
        return self.DELTA


class PestoAccumulator:
    """
    Board-independent incremental PeSTO score tracker.

    Any board implementation can opt into O(1) evaluation by:

    1. Creating an instance in ``__init__``: ``self._pesto_accum = PestoAccumulator(self)``
    2. Calling ``on_push(board, move)`` *before* applying the move.
    3. Calling ``on_pop()`` *after* undoing the move.
    4. Calling ``init_from_board(board)`` after any wholesale position change
       (``set_fen``, ``reset``, ``set_epd``).

    :class:`Pesto` automatically uses the accumulator when ``board._pesto_accum`` exists.
    """

    __slots__ = ("mg_white", "mg_black", "eg_white", "eg_black", "phase", "_stack")

    def __init__(self, board: Board) -> None:
        self.mg_white: float = 0.0
        self.mg_black: float = 0.0
        self.eg_white: float = 0.0
        self.eg_black: float = 0.0
        self.phase: int = 0
        self._stack: list = []
        self.init_from_board(board)

    def init_from_board(self, board: Board) -> None:
        """Recompute accumulators from scratch for the current position."""
        mg_w = mg_b = eg_w = eg_b = 0.0
        phase = 0
        MG = Pesto.MG_PESTO
        EG = Pesto.EG_PESTO
        PH = Pesto.PHASES
        for pt in chess.PIECE_TYPES:
            pt_idx = pt - 1
            mg_t = MG[pt_idx]
            eg_t = EG[pt_idx]
            ph = PH[pt_idx]
            for sq in board.pieces(pt, chess.WHITE):
                mg_w += mg_t[sq ^ 56]
                eg_w += eg_t[sq ^ 56]
                phase += ph
            for sq in board.pieces(pt, chess.BLACK):
                mg_b += mg_t[sq]
                eg_b += eg_t[sq]
                phase += ph
        self.mg_white = mg_w
        self.mg_black = mg_b
        self.eg_white = eg_w
        self.eg_black = eg_b
        self.phase = phase
        self._stack.clear()

    def _update(self, sign: int, sq: int, piece: chess.Piece) -> None:
        """Add (sign=+1) or remove (sign=-1) a piece's PST contribution."""
        pt_idx = piece.piece_type - 1
        mg_delta = sign * Pesto.MG_PESTO[pt_idx][sq ^ 56 if piece.color else sq]
        eg_delta = sign * Pesto.EG_PESTO[pt_idx][sq ^ 56 if piece.color else sq]
        if piece.color:
            self.mg_white += mg_delta
            self.eg_white += eg_delta
        else:
            self.mg_black += mg_delta
            self.eg_black += eg_delta
        self.phase += sign * Pesto.PHASES[pt_idx]

    def _save(self) -> None:
        self._stack.append(
            (self.mg_white, self.mg_black, self.eg_white, self.eg_black, self.phase)
        )

    def on_push(self, board: Board, move: chess.Move) -> None:
        """
        Update accumulators for ``move``.  Must be called *before* the underlying
        board applies the move so that ``board.piece_at`` still reflects the
        pre-move state.

        Null moves (``chess.Move.null()``) push a sentinel onto the stack so that
        ``on_pop`` remains balanced, but no piece scores change.
        """
        self._save()
        if move == chess.Move.null():
            return

        from_sq = move.from_square
        to_sq = move.to_square
        moving_piece = board.piece_at(from_sq)
        captured_piece = board.piece_at(to_sq)

        self._update(-1, from_sq, moving_piece)

        if captured_piece:
            self._update(-1, to_sq, captured_piece)

        if board.is_en_passant(move):
            ep_sq = chess.square(chess.square_file(to_sq), chess.square_rank(from_sq))
            self._update(-1, ep_sq, chess.Piece(chess.PAWN, not moving_piece.color))

        dest_piece = (
            chess.Piece(move.promotion, moving_piece.color)
            if move.promotion
            else moving_piece
        )
        self._update(+1, to_sq, dest_piece)

        # Castling: king moves two files — also relocate the rook.
        if (
            moving_piece.piece_type == chess.KING
            and abs(chess.square_file(to_sq) - chess.square_file(from_sq)) == 2
        ):
            rank = chess.square_rank(from_sq)
            kingside = chess.square_file(to_sq) == 6
            rook_from = chess.square(7 if kingside else 0, rank)
            rook_to = chess.square(5 if kingside else 3, rank)
            rook = chess.Piece(chess.ROOK, moving_piece.color)
            self._update(-1, rook_from, rook)
            self._update(+1, rook_to, rook)

    def on_pop(self) -> None:
        """Restore accumulators after a move is undone.  Must be called *after* pop."""
        (
            self.mg_white,
            self.mg_black,
            self.eg_white,
            self.eg_black,
            self.phase,
        ) = self._stack.pop()
