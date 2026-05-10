import chess
import json
import numpy as np
from pathlib import Path

INPUT_JSON = "training_pairs.json"
OUTPUT_NPZ = "training_data.npz"

PIECE_TO_PLANE = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}

def encode_position(board: chess.Board, you_were_white: bool) -> np.ndarray:
    """
    Returns a (18, 8, 8) float32 tensor.
    Always oriented from YOUR perspective: your pieces on planes 0-5, opponent on 6-11.
    """
    if not you_were_white:
        board = board.mirror()
    
    planes = np.zeros((18, 8, 8), dtype=np.float32)
    
    for square, piece in board.piece_map().items():
        # square is 0-63 (a1=0, h8=63 in python-chess); convert to (rank, file)
        rank = square // 8
        file = square % 8
        plane_offset = 0 if piece.color == chess.WHITE else 6
        planes[plane_offset + PIECE_TO_PLANE[piece.piece_type], rank, file] = 1.0
    
    if board.turn == chess.WHITE:
        planes[12, :, :] = 1.0
    
    # Planes 13-16: castling rights
    if board.has_kingside_castling_rights(chess.WHITE):
        planes[13, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.WHITE):
        planes[14, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.BLACK):
        planes[15, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.BLACK):
        planes[16, :, :] = 1.0
    
    if board.ep_square is not None:
        rank = board.ep_square // 8
        file = board.ep_square % 8
        planes[17, rank, file] = 1.0
    
    return planes


def encode_move(move: chess.Move, you_were_white: bool) -> int:
    """
    Returns an integer 0-4095 representing the move as from-square * 64 + to-square.
    Mirrors the move if you were black, to match the mirrored board.
    """
    from_sq = move.from_square
    to_sq = move.to_square
    
    if not you_were_white:
        from_sq = chess.square_mirror(from_sq)
        to_sq = chess.square_mirror(to_sq)
    
    return from_sq * 64 + to_sq


print("Loading training pairs...")
with open(INPUT_JSON) as f:
    pairs = json.load(f)
print(f"  {len(pairs)} pairs loaded")

N = len(pairs)
X = np.zeros((N, 18, 8, 8), dtype=np.float32)
y = np.zeros(N, dtype=np.int32)

print("Encoding positions...")
for i, p in enumerate(pairs):
    if i % 5000 == 0:
        print(f"  {i}/{N}")
    
    board = chess.Board(p["fen"])
    move = chess.Move.from_uci(p["move"])
    
    X[i] = encode_position(board, p["you_were_white"])
    y[i] = encode_move(move, p["you_were_white"])

print(f"\nFinal shapes: X={X.shape}, y={y.shape}")
print(f"X dtype: {X.dtype}, y dtype: {y.dtype}")
print(f"X memory: {X.nbytes / 1e6:.1f} MB")

# Sanity checks
print(f"\nUnique moves seen: {len(np.unique(y))} / 4096 possible")
print(f"Most common move index: {np.bincount(y).argmax()}")
most_common_idx = int(np.bincount(y).argmax())
from_sq = most_common_idx // 64
to_sq = most_common_idx % 64
print(f"  → from {chess.square_name(from_sq)} to {chess.square_name(to_sq)}")
print(f"  → played {np.bincount(y).max()} times")

# Save
np.savez_compressed(OUTPUT_NPZ, X=X, y=y)
print(f"\nSaved to {OUTPUT_NPZ}")

# Verify roundtrip on first sample
print("\n--- Verification of first sample ---")
print(f"FEN: {pairs[0]['fen']}")
print(f"Move: {pairs[0]['move']}")
print(f"You were white: {pairs[0]['you_were_white']}")
print(f"Encoded move index: {y[0]}")
print(f"Plane 12 (your turn): {'all 1s' if X[0, 12, 0, 0] == 1.0 else 'all 0s'}")
print(f"Total piece planes sum (should be ~32 at start): {X[0, 0:12].sum():.0f}")