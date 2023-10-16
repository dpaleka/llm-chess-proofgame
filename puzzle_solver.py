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

import chess
import numpy as np
import io
import json
import chessllm
import csv
from pathlib import Path
from tqdm import tqdm

def convert_pgn_to_game(pgn_moves):
    pgn = io.StringIO(pgn_moves)
    game = chess.pgn.read_game(pgn)
    if len(game.errors) > 0:
        return None
    return game

def solve_puzzle(board, solution):
    print("Solving puzzle", board.fen(), solution)
    solution = solution.split()
    while True:
        guess_next_move = engine.get_best_move(board)
        print("Guessing", guess_next_move)
        real_next_move, *solution = solution
        if guess_next_move != real_next_move:
            try:
                board.push_san(guess_next_move)
                if board.is_checkmate():
                    # Lichess puzzles allow multiple mate-in-1 solutions
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


DATA_DIR = Path("/data/chess-data/lichess_puzzles")  

def main():

    # Create buckets
    bucket_size = 200
    buckets = [[] for _ in range(30)]
    enough_samples = 40

    # Read the data and sort into buckets
    with open(DATA_DIR / "pgn_puzzles.csv") as f:
        reader = csv.reader(f)
        print(reader.__next__())
        for puzzleid, rating, pgn, solution in tqdm(list(reader)):
            rating_bucket = int(rating) // bucket_size
            if len(buckets[rating_bucket]) < enough_samples:
                buckets[rating_bucket].append((pgn, solution))

    # Test the puzzles
    ok = [[] for _ in range(30)]
    for rating_bucket, puzzles in enumerate(buckets):
        for pgn, solution in puzzles:
            board = chess.Board()

            # Iterate over the moves and apply them to the board
            for move in convert_pgn_to_game(pgn).mainline_moves():
                board.push(move)

            is_right = solve_puzzle(board, solution)

            ok[rating_bucket].append(is_right)

    # Print and plot the results
    ratings = []
    for i, x in enumerate(ok):
        ratings.append(np.mean(x) if len(x) > 0 else np.nan)
        print(f'rating [{i*bucket_size}, {(i+1)*bucket_size})', f'acc {ratings[i]:.3f}' if len(x) > 0 else np.nan, 'n', len(x))

    if True:
        import matplotlib.pyplot as plt
        # Remove nan values and get their indices
        #ratings = [np.mean(x) for x in ok]
        non_nan_indices = [i for i, val in enumerate(ratings) if not np.isnan(val)]
        non_nan_values = [ratings[i] for i in non_nan_indices]
        
        # Create bucket ranges
        bucket_ranges = [(i*bucket_size, (i+1)*bucket_size) for i in non_nan_indices]
        bucket_labels = [f"{low}-{high}" for low, high in bucket_ranges]
        
        # Plotting
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
    api_key = open("OPENAI_API_KEY").read().strip()
    config = json.loads(open("config.json").read())
    engine = chessllm.ChessLLM(api_key, config, num_lookahead_tokens=30)
    main()

    