import chess

# include when needed, slow for CI
# import torch
# import torch.nn as nn
# import torch.optim as optim


# Efficently updated neural network (NNUE)
# Does not work yet.
class NNUE(nn.Module):
    # Should be Half-kP structure
    def __init__(self):
        super(NNUE, self).__init__()
        self.fc1 = nn.Linear(2 * 64 * 64 * 5, 2 * 256)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(2 * 256, 1)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


def piece_locations_to_indices(board):
    KING_JUMP = 64
    PIECE_JUMP = 5
    COLOR_JUMP = 2
    # Maps (king, piece) to 1 if the pair exists on the board, else 0. Returns the vector.
    tensor = (
        COLOR_JUMP * 64 * KING_JUMP * PIECE_JUMP * [0]
    )  # 2 colors, 64 king position, 64 piece positions, 5 piece types
    piece_map = board.piece_map()
    kings = [
        (square, piece)
        for square, piece in piece_map.items()
        if piece.piece_type == chess.KING
    ]
    white_king, black_king = (
        (kings[0][0], kings[1][0])
        if kings[0][1].color == chess.WHITE
        else (kings[1][0], kings[0][0])
    )
    for square, piece in (
        (square, piece)
        for square, piece in piece_map.items()
        if piece.piece_type != chess.KING
    ):
        king_idx = white_king if piece.color == chess.WHITE else black_king
        if piece.color == chess.WHITE:
            tensor[
                KING_JUMP * PIECE_JUMP * king_idx
                + KING_JUMP * piece.piece_type
                + square
            ] = 1
        else:
            tensor[
                COLOR_JUMP * KING_JUMP * PIECE_JUMP * king_idx
                + KING_JUMP * piece.piece_type
                + square
            ] = 1
    return torch.tensor(tensor).to(torch.float32)
