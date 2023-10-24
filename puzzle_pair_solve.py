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
It has the following columns: uid,rating,pgn,proofgame,solution.

Helper functions:
def solve_puzzle(board, solution) -> bool: whether model can solve the puzzle
convert_pgn_to_game(pgn_moves) -> game
"""


def main():
    raise NotImplementedError("This script is not finished")


if __name__ == "__main__":
    api_key = open("OPENAI_API_KEY").read().strip()
    config = json.loads(open("config.json").read())
    engine = chessllm.ChessLLM(api_key, config, num_lookahead_tokens=30)
    main()