from typing import Dict

import chess

from sporkfish.board.board import Board


def _capture_value(
    board: Board, move: chess.Move, piece_values: Dict[chess.PieceType, float]
) -> float:
    """Material value won by making a capture move in current position."""
    if not board.is_capture(move):
        return 0.0

    captured_type = (
        chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
    )
    if captured_type is None:
        return 0.0
    return float(piece_values[captured_type])


def _best_reply_capture_gain(
    board: Board,
    target_square: chess.Square,
    piece_values: Dict[chess.PieceType, float],
) -> float:
    """Best gain side-to-move can force by recapturing on target_square.

    To keep SEE fast in search hot paths, we only follow the least valuable
    legal attacker each ply (LVA continuation), instead of branching over all
    legal captures.
    """

    chosen_move = None
    chosen_value = float("inf")
    for move in board.generate_legal_captures():
        if move.to_square != target_square:
            continue

        moving_type = board.piece_type_at(move.from_square)
        if moving_type is None:
            continue

        attacker_value = float(piece_values[moving_type])
        if attacker_value < chosen_value:
            chosen_value = attacker_value
            chosen_move = move

    # Side to move can always decline to capture.
    if chosen_move is None:
        return 0.0

    gain_now = _capture_value(board, chosen_move, piece_values)
    board.push(chosen_move)
    reply_gain = _best_reply_capture_gain(board, target_square, piece_values)
    board.pop()

    return max(0.0, gain_now - reply_gain)


def static_exchange_eval(
    board: Board, move: chess.Move, piece_values: Dict[chess.PieceType, float]
) -> float:
    """Estimate net material gain/loss of a capture sequence on the destination square.

    Positive means the initiating side wins material; negative means it likely loses
    material after best recaptures.
    """
    if not board.is_capture(move):
        return 0.0

    gain = _capture_value(board, move, piece_values)
    target_square = move.to_square

    board.push(move)
    gain -= _best_reply_capture_gain(board, target_square, piece_values)
    board.pop()

    return gain
