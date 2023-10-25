"""
Three csv files.
pgn:  has header uid,rating,FEN,solution
Proofgame_pgn: uid,rating,FEN,solution,proofgame
Original_pgn: has header uid,rating,pgn,solution

Create a new one with header uid,rating,pgn,proofgame,solution.
Do not include columns where proofgame is None.
"""

import pandas as pd
import argparse
import os

def merge_files(data_dir, pgn_file, proofgame_file, original_file, output_file):
    # Load the csv files
    pgn = pd.read_csv(os.path.join(data_dir, pgn_file))
    proofgame_pgn = pd.read_csv(os.path.join(data_dir, proofgame_file))
    original_pgn = pd.read_csv(os.path.join(data_dir, original_file))
    # original pgn may not have a header
    if 'uid' not in original_pgn.columns:
        original_pgn.columns = ['uid', 'rating', 'pgn', 'solution']

    # Merge the dataframes
    merged_df = pd.merge(original_pgn, proofgame_pgn[['uid', 'proofgame']], on='uid', how='inner')

    # Drop rows where proofgame is None
    merged_df = merged_df[merged_df['proofgame'].notna()]

    # Write the merged dataframe to a new csv file
    # reorder so it's uid, rating, pgn, proofgame, solution
    merged_df = merged_df[['uid', 'rating', 'pgn', 'proofgame', 'solution']]
    merged_df.to_csv(output_file, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", "-d", default="/data/chess-data/lichess_puzzles/", help="Directory containing the data files. Can be / if you want to use full paths")
    parser.add_argument("--pgn_file", "-p", default="fen_puzzles.csv", help="Name of the pgn file")
    parser.add_argument("--proofgame_file", "-pg", default="proofgame_pgns.csv", help="Name of the proofgame file")
    parser.add_argument("--original_file", "-o", default="pgn_puzzles.csv", help="Name of the original pgn file")
    parser.add_argument("--output", "-out", default="/data/chess-data/lichess_puzzles/pairs.csv", help="Name of the output file")
    args = parser.parse_args()

    merge_files(args.data_dir, args.pgn_file, args.proofgame_file, args.original_file, output_file=args.output)
