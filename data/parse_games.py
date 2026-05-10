import chess
import chess.pgn
import json
from collections import Counter

USERNAME = "r0ck3ted"
INPUT_PGN = "raw_games.pgn"
OUTPUT_JSON = "training_pairs.json"

ALLOWED_TIME_CLASSES = {"rapid", "blitz"}

def is_usable(headers):
    """should this game should be included."""
    tc = headers.get("TimeControl", "")
    try:
        base = int(tc.split("+")[0])
    except (ValueError, IndexError):
        return False, "bad time control"
    
    if base < 180:
        return False, "bullet"
    if base > 1800:
        return False, "too slow / daily"
    
    term = headers.get("Termination", "").lower()
    if "abandoned" in term:
        return False, "abandoned"
    
    return True, "ok"

training_pairs = []
games_processed = 0
games_skipped = Counter()
moves_skipped = 0

with open(INPUT_PGN) as f:
    while True:
        game = chess.pgn.read_game(f)
        if game is None:
            break
        
        ok, reason = is_usable(game.headers)
        if not ok:
            games_skipped[reason] += 1
            continue
        
        white = game.headers.get("White", "").lower()
        black = game.headers.get("Black", "").lower()
        you_are_white = white == USERNAME.lower()
        you_are_black = black == USERNAME.lower()
        if not (you_are_white or you_are_black):
            games_skipped["not your game"] += 1
            continue
        
        games_processed += 1
        
        # Walk the moves
        board = game.board()
        for move in game.mainline_moves():
            # Whose turn is it BEFORE the move?
            white_to_move = board.turn == chess.WHITE
            your_turn = (white_to_move and you_are_white) or (not white_to_move and you_are_black)
            
            if your_turn:
                training_pairs.append({
                    "fen": board.fen(),
                    "move": move.uci(),
                    "you_were_white": you_are_white,
                })
            else:
                moves_skipped += 1
            
            board.push(move)

print(f"Games processed: {games_processed}")
print(f"Games skipped:")
for reason, n in games_skipped.most_common():
    print(f"  {reason}: {n}")
print(f"\nTraining pairs (your moves): {len(training_pairs)}")
print(f"Opponent moves skipped: {moves_skipped}")
print(f"Avg your-moves per game: {len(training_pairs) / max(games_processed, 1):.1f}")

white_pairs = sum(1 for p in training_pairs if p["you_were_white"])
print(f"Pairs where you were white: {white_pairs} ({100*white_pairs/len(training_pairs):.1f}%)")

with open(OUTPUT_JSON, "w") as f:
    json.dump(training_pairs, f)
print(f"\nSaved to {OUTPUT_JSON}")

print("\nFirst 3 training pairs:")
for p in training_pairs[:3]:
    print(f"  FEN: {p['fen']}")
    print(f"  Your move: {p['move']}  (you were {'white' if p['you_were_white'] else 'black'})")
    print()