"""
There is a file made using this code:
    with open(os.path.join(DATA_DIR, "FILE.csv"), "w") as f:
        writer = csv.writer(f)
        for uid, rating, board, solution in extracted_puzzles:
            writer.writerow((uid, rating,
                             str(chess.pgn.Game().from_board(board)).split("\n")[-1][:-2],
                             " ".join(solution)))

Make a file with the following format: uid, rating, fen, solution. Label the columns "uid", "rating", "FEN", "solution".
Use argparse to input the file name and the output file name.
"""

import csv
import os
import io
import argparse
from tqdm import tqdm
import chess.pgn

def pgn_to_fen(input_file, output_file, num_entries=None):
    with open(input_file, "r") as f_in, open(output_file, "w") as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        # write header
        writer.writerow(("uid", "rating", "FEN", "solution"))
        for i, row in tqdm(enumerate(reader)):
            if num_entries is not None and i >= num_entries:
                break
            uid, rating, pgn, solution = row
            game = chess.pgn.read_game(io.StringIO(pgn))
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            fen = board.fen()

            writer.writerow((uid, rating, fen, solution))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", "-i", help="Name of the input file", default="/data/chess-data/lichess_puzzles/pgn_puzzles.csv")
    parser.add_argument("--output_file", "-o", help="Name of the output file", default="/data/chess-data/lichess_puzzles/fen_puzzles.csv")
    parser.add_argument("--num_entries", "-n", type=int, help="Number of entries to process", default=None)

    args = parser.parse_args()

    pgn_to_fen(args.input_file, args.output_file, args.num_entries)
