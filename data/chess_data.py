import requests
import chess.pgn
import io
from collections import Counter

USERNAME = "r0ck3ted"
HEADERS = {"User-Agent": "vincent-chess (contact: 44vincentlin@gmail.com)"}

archives_url = f"https://api.chess.com/pub/player/{USERNAME}/games/archives"
archives = requests.get(archives_url, headers=HEADERS).json()["archives"]

all_games_pgn = []

for url in archives:
    monthly_data = requests.get(url, headers=HEADERS).json()
    for game in monthly_data["games"]:
        if "pgn" in game:
            all_games_pgn.append(game)


time_classes = Counter()
my_games = 0
my_wins = 0
usable_games = 0

for g in all_games_pgn:
    category = g.get("time_class", "error")
    time_classes[category] += 1

    tc = category

    white = g.get("white", {}).get("username", "").lower()
    black = g.get("black", {}).get("username", "").lower()
    white_check = white == USERNAME.lower()
    black_check = black == USERNAME.lower()
    if not (white_check or black_check):
        continue
    my_games += 1

    you_are_white = white_check

    your_side = g.get("white", {}) if you_are_white else g.get("black", {})
    your_result = your_side.get("result", "")
    if your_result == "win":
        my_wins += 1

    if tc in ("rapid", "blitz") and your_result in (
        "win",
        "checkmated",
        "resigned",
        "timeout",
        "agreed",
        "stalemate",
        "repetition",
        "insufficient",
        "50move",
        "timevsinsufficient",
    ):
        usable_games += 1

print(f"\nGames where I played: {my_games}")
print(f"Wins: {my_wins} ({100*my_wins/max(my_games,1):.1f}%)")
print(f"\nBy time control:")
for tc, n in time_classes.most_common():
    print(f"  {tc}: {n}")
print(f"\nUsable (rapid/blitz, normal finish): {usable_games}")

with open("raw_games.pgn", "w") as f:
    for g in all_games_pgn:
        f.write(g["pgn"] + "\n\n")
print(f"\nSaved {len(all_games_pgn)} games to raw_games.pgn")


