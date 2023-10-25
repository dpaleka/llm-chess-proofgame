import chess
import numpy as np
import io
import json
import csv
from pathlib import Path
from tqdm import tqdm
from puzzle_solver import convert_pgn_to_game, solve_puzzle
import chessllm

DATA_DIR = Path("/data/chess-data/lichess_puzzles")  
FILE_NAME = DATA_DIR / "pairs.csv"

"""
Solve puzzle pairs given in FILE_NAME, and report whether the model can solve them.
Separate by rating buckets; take 40 samples from each bucket.
It has the following columns: uid,rating,pgn,proofgame,solution

Helper functions:
def solve_puzzle(board, solution) -> bool: whether model can solve the puzzle
convert_pgn_to_game(pgn_moves) -> game
"""

DATA_DIR = Path("/data/chess-data/lichess_puzzles")  
FILE_NAME = DATA_DIR / "pairs.csv"

def main(engine):
    # Create buckets
    bucket_size = 200
    buckets = {i*bucket_size: [] for i in range(30)}
    enough_samples = 10

    # Read the data and sort into buckets
    with open(FILE_NAME) as f:
        reader = csv.reader(f)
        print(reader.__next__())
        for uid, rating, pgn, proofgame, solution in tqdm(list(reader)):
            rating_bucket = int(rating) // bucket_size * bucket_size
            if len(buckets[rating_bucket]) < enough_samples:
                buckets[rating_bucket].append((pgn, proofgame, solution))

    # print how many elems in buckets
    for k, v in buckets.items():
        print(f'rating [{k}, {k + bucket_size})', 'n', len(v))

    # Test the puzzles
    ok_pgn = {i*bucket_size: [] for i in range(30)}
    ok_proofgame = {i*bucket_size: [] for i in range(30)}
    for rating_bucket, puzzles in tqdm(buckets.items()):
        for pgn, proofgame, solution in puzzles:
            board_pgn = chess.Board()
            board_proofgame = chess.Board()

            print("pgn origi", pgn)
            print("proofgame", proofgame)
            # Iterate over the moves and apply them to the board
            for move in convert_pgn_to_game(pgn).mainline_moves():
                board_pgn.push(move)
            for move in convert_pgn_to_game(proofgame).mainline_moves():
                board_proofgame.push(move)

            is_right_pgn = solve_puzzle(board_pgn, solution, engine)
            is_right_proofgame = solve_puzzle(board_proofgame, solution, engine)

            ok_pgn[rating_bucket].append(is_right_pgn)
            ok_proofgame[rating_bucket].append(is_right_proofgame)

    # Compare the results
    for i in range(30):
        bucket_start = i * bucket_size
        if len(ok_pgn[bucket_start]) > 0 and len(ok_proofgame[bucket_start]) > 0:
            pgn_acc = np.mean(ok_pgn[bucket_start])
            proofgame_acc = np.mean(ok_proofgame[bucket_start])
            print(f'rating [{bucket_start}, {bucket_start + bucket_size})', f'pgn acc {pgn_acc:.3f}', f'proofgame acc {proofgame_acc:.3f}', 'n', len(ok_pgn[bucket_start]))

if __name__ == "__main__":
    api_key = open("OPENAI_API_KEY").read().strip()
    config = { "temperature": 0, "num_lookahead_tokens": 20 }
    engine = chessllm.ChessLLM(api_key, config, model="gpt-3.5-turbo-instruct", num_lookahead_tokens=30)
    main(engine)
