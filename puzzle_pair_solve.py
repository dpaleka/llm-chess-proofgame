import chess
import numpy as np
import io
import json
import csv
from pathlib import Path
from tqdm import tqdm
from puzzle_solver import convert_pgn_to_game, solve_puzzle
import chessllm
from matplotlib import pyplot as plt

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

def plot_acc_pairs(engine, bucket_size=200, enough_samples=10):
    # Create buckets
    buckets = {i*bucket_size: [] for i in range(30)}

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
    nonempty_buckets = [k for k, v in buckets.items() if len(v) > 0]

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
    for bucket_start in nonempty_buckets:
        if len(ok_pgn[bucket_start]) > 0 and len(ok_proofgame[bucket_start]) > 0:
            pgn_acc = np.mean(ok_pgn[bucket_start])
            proofgame_acc = np.mean(ok_proofgame[bucket_start])
            print(f'rating [{bucket_start}, {bucket_start + bucket_size})', f'pgn acc {pgn_acc:.3f}', f'proofgame acc {proofgame_acc:.3f}', 'n', len(ok_pgn[bucket_start]))
    
    # Plot both results
    """
    Some old code:
    non_nan_indices = [i for i, val in enumerate(ratings) if not np.isnan(val)]
    non_nan_values = [ratings[i] for i in non_nan_indices]
    bucket_ranges = [(i*bucket_size, (i+1)*bucket_size) for i in non_nan_indices]
    bucket_labels = [f"{low}-{high}" for low, high in bucket_ranges]
    plt.figure(figsize=(8, 4))
    plt.bar(bucket_labels, non_nan_values)
    plt.xlabel('Puzzle Rating (Elo)')
    plt.ylabel('Probability correct')
    plt.title('Ratings vs. Buckets')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    plt.savefig("/tmp/a.png", dpi=600)
    plt.savefig("accuracy.png", dpi=600)
    """

    # Plot pgn and proofgame on the same plot
    bucket_ranges = [(k, k + bucket_size) for k in nonempty_buckets]
    bucket_labels = [f"{low}-{high}" for low, high in bucket_ranges]
    pgn_acc = [np.mean(ok_pgn[bucket_start]) for bucket_start in nonempty_buckets]
    proofgame_acc = [np.mean(ok_proofgame[bucket_start]) for bucket_start in nonempty_buckets]
    plt.figure(figsize=(8, 4))
    plt.bar(bucket_labels, pgn_acc, label="pgn")
    plt.bar(bucket_labels, proofgame_acc, label="proofgame")
    plt.xlabel('Puzzle Rating (Elo)')
    plt.ylabel('Probability correct')
    plt.title('Ratings vs. Buckets')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.show()
    plt.savefig("/tmp/b.png", dpi=600)
    plt.savefig("accuracy_both.png", dpi=600)


if __name__ == "__main__":
    api_key = open("OPENAI_API_KEY").read().strip()
    config = { "temperature": 0, "num_lookahead_tokens": 30}
    engine = chessllm.ChessLLM(api_key, config, model="gpt-3.5-turbo-instruct")
    plot_acc_pairs(engine)

