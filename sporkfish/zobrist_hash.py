import random
import chess
from . import utils


class ZobristHash:
    def __init__(self) -> None:
        """
        Initialize the Zobrist Hash object.

        Attributes:
        - _piece_hashes (dict): Dictionary to store Zobrist hash values for each piece on each square.
        - _side_hash (int): Zobrist hash value for the side to move.
        - _en_passant_hashes (list): Zobrist hash values for en passant squares.
        - _castling_hashes (list): Zobrist hash values for castling rights.
        """
        self._piece_hashes = {}
        self._side_hash = 0
        self._en_passant_hashes = [0] * 8
        self._castling_hashes = [0] * 4

        for square in range(64):
            for piece in range(12):  # 6 piece types for both colors
                self._piece_hashes[(square, piece)] = random.getrandbits(64)
        self._side_hash = random.getrandbits(64)
        for file in range(8):
            self._en_passant_hashes[file] = random.getrandbits(64)
        for castling_right in range(4):
            self._castling_hashes[castling_right] = random.getrandbits(64)

    def hash(self, board: chess.Board) -> None:
        """
        Update the Zobrist hash value for the entire board based on the current board state.

        Parameters:
        - board (chess.Board): The chess board representing the current state.
        """
        # Reset the board hash to start with a clean slate
        board_hash = 0

        # Iterate through all squares on the chess board
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                # Calculate the piece index based on piece type and color
                piece_index = hash(piece)
                board_hash ^= self._piece_hashes[(square, piece_index)]

        # XOR the side to move Zobrist hash if it's black's turn
        if board.turn == chess.BLACK:
            board_hash ^= self._side_hash

        # XOR the en passant Zobrist hash if there is an en passant square
        if board.ep_square is not None:
            ep_file = chess.square_file(board.ep_square)
            board_hash ^= self._en_passant_hashes[ep_file]

        # Iterate through castling rights and XOR the corresponding Zobrist hash if the right is present
        castling_rights = (
            board.has_kingside_castling_rights(chess.WHITE),
            board.has_queenside_castling_rights(chess.WHITE),
            board.has_kingside_castling_rights(chess.BLACK),
            board.has_queenside_castling_rights(chess.BLACK),
        )
        for i, castling_right in enumerate(castling_rights):
            if castling_right:
                board_hash ^= self._castling_hashes[i]

        return board_hash
