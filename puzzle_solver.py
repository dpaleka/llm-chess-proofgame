## Copyright (C) 2023, Nicholas Carlini <nicholas@carlini.com>.
## Copyright (C) 2023, Daniel Paleka <daniel.paleka@inf.ethz.ch>.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import chess
import numpy as np
import io
import csv
from pathlib import Path
from tqdm import tqdm
import chessllm
import matplotlib.pyplot as plt

def convert_pgn_to_game(pgn_moves):
    pgn = io.StringIO(pgn_moves)
    game = chess.pgn.read_game(pgn)
    if len(game.errors) > 0:
        return None
    return game

def solve_puzzle(board, solution, engine):
    solution = solution.split()
    while True:
        guess_next_move = engine.get_best_move(board)
        real_next_move, *solution = solution
        if guess_next_move != real_next_move:
            try:
                board.push_san(guess_next_move)
                if board.is_checkmate():
                    return True
            except:
                pass
            return False
        board.push_san(guess_next_move)
        if len(solution) > 0:
            opponent_move, *solution = solution
            board.push_san(opponent_move)
        else:
            break
    return True

def plot_acc(engine, file_name, bucket_size, enough_samples):

    buckets = {i*bucket_size: [] for i in range(15)}

    import pandas as pd
    with open(file_name) as f:
        df = pd.read_csv(f)
        # add column names
        df.columns = ['uid', 'rating', 'pgn', 'solution']
        for i, row in tqdm(df.iterrows()):
            rating_bucket = int(row['rating']) // bucket_size * bucket_size
            if len(buckets[rating_bucket]) < enough_samples:
                buckets[rating_bucket].append((row['pgn'], row['solution']))

    for k, v in buckets.items():
        print(f'rating [{k}, {k + bucket_size})', 'n', len(v))

    ok = [[] for _ in range(15)]
    for rating_bucket, puzzles in buckets.items():
        for pgn, solution in puzzles:
            board = chess.Board()
            for move in convert_pgn_to_game(pgn).mainline_moves():
                board.push(move)
            is_right = solve_puzzle(board, solution, engine)
            ok[rating_bucket//bucket_size].append(is_right)

    ratings = []
    for i, x in enumerate(ok):
        ratings.append(np.mean(x) if len(x) > 0 else np.nan)
        print(f'rating [{i*bucket_size}, {(i+1)*bucket_size})', f'acc {ratings[i]:.3f}' if len(x) > 0 else np.nan, 'n', len(x))

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", "-d", default="/data/chess-data/lichess_puzzles", help="Path to the data directory")
    parser.add_argument("--file_name", "-f", default="pgn_puzzles.csv", help="Name of the input file")
    parser.add_argument("--no_cache", dest="use_cache", action="store_false", help="Don't use cache for ChessLLM")
    parser.add_argument("--bucket_size", "-b", type=int, default=200, help="Size of the rating bucket")
    parser.add_argument("--enough_samples", "-e", type=int, default=10, help="Minimum number of samples required in a bucket")
    parser.add_argument("--model", default="gpt-3.5-turbo-instruct", help="Model name")
    args = parser.parse_args()

    api_key = open("OPENAI_API_KEY").read().strip()
    engine = chessllm.ChessLLM(api_key, config={"temperature": 0, "num_lookahead_tokens": 30}, 
                               model=args.model,
                               use_cache=args.use_cache)
    file_name = Path(args.data_dir) / args.file_name
    plot_acc(engine, file_name, args.bucket_size, args.enough_samples)
