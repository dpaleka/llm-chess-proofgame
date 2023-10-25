"""
 For a given FEN, we'll be using the texelutil proofgame CLI to generate a proof game.
 An example command is:
 echo "r6r/pp3pk1/5Rp1/n2pP1Q1/2pPp3/2P1P2q/PP1B3P/R5K1 w - - 0 1"" | texelutil proofgame -f -o outfile -rnd seed 2>debug 
 We'll be running multiple commands like this in parallel, so we'll need to make sure that the output files are unique.
 The general command is
 echo FEN | texelutil proofgame -f -o result_t_{thread_id}_ -rnd seed 2>debug_t_{thread_id}_

 texelutil proofgame saves the output into a list of files: if -o outfile,
 then the output files are outfile00, outfile01, outfile02, etc.
 If successfuly solved, the last one contains the proof game in this format:
 r6r/pp3pk1/5Rp1/n2pP1Q1/2pPp3/2P1P2q/PP1B3P/R5K1 w - - 0 1 legal: proof: g4 d5 f4 h5 gxh5 e5 Nh3 Bxh3 Bxh3 e4 Bd7+ Nxd7 h6 Ne5 fxe5 Rxh6 Nc3 Be7 Na4 Bc5 Nxc5 Rh8 Ne6 Qc8 Nd8 Qxd8 Kf1 Kf8 d4 c5 c3 g6 e3 c4 Bd2 Kg7 Qh5 Qd7 Qg5 Ne7 Kg1 Nc6 Rf1 Qe6 Rf6 Qh3 Kf2 Rh7 Ra1 Rhh8 Kg1 Na5
 Note that it contains the substring "legal: proof: ".

 We time out each run after TIMEOUT seconds, which means some positions won't have a proof game, 
 so the last file will not have "legal: proof: ", but rather "unknown: kernel: " or something like that.

 We need to make the game into a proper PGN.
 Example:  g4 d5 f4 h5 gxh5 e5 Nh3 Bxh3 Bxh3 e4 Bd7+ 
 goes to  1. g4 d5 2. f4 h5 3. gxh5 e5 4. Nh3 Bxh3 5. Bxh3 e4 6. Bd7+

 We also need to make sure that the PGN is valid.  We can do this by playing the game out on a chessboard, using python-chess,
 and then checking that the final position is the same as the one we started with.
"""

import os
import io
import argparse
import subprocess
import re
import chess
import chess.pgn
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from concurrent.futures import TimeoutError
import multiprocessing
import time

# Add texelutil to the PATH
TEXELUTIL_PATH = Path(".").resolve()
os.environ["PATH"] += os.pathsep + str(TEXELUTIL_PATH)


DATA_DIR = "/data/chess-data/lichess_puzzles"
SEED = 42
TEXELUTIL_RES_DIR = "./texel_temp_results"
os.makedirs(TEXELUTIL_RES_DIR, exist_ok=True)
MAX_THREADS = 64
TIMEOUT = 180  # Timeout in seconds

# List of FENs for testing whether the code works
fens_test = ["r6r/pp3pk1/5Rp1/n2pP1Q1/2pPp3/2P1P2q/PP1B3P/R5K1 w - - 0 1", 
             "r6r/pp3pk1/5Rp1/n2pP1Q1/2pPp3/2P1P2q/PP1B3P/R5K1 w - - 0 1",
             "r1b3k1/pp3Rpp/3p1b2/2pN4/2P5/5Q1P/PPP3P1/4qNK1 w - - 0 1"]

def check_contains_fen(fen, file):
    if not os.path.exists(file):
        return False
    with open(file, "r") as f:
        content = f.read()
        return content.startswith(fen)

def move_01(fen : str):
    """
    Replace the last two fields in the FEN (halfmove count for 50-move rule, full move count) with 0 and 1.
    """
    fen = fen.split()
    assert(len(fen) == 6 and fen[4].isdigit() and fen[5].isdigit())
    fen[4] = "0"
    fen[5] = "1"
    return " ".join(fen)

def run_command(fen, thread_id, force=False):
    FIRST_FILE = f"{TEXELUTIL_RES_DIR}/result_t_{thread_id}_00"
    if not force and os.path.exists(FIRST_FILE):
        if check_contains_fen(fen, FIRST_FILE):
            print(f"Thread {thread_id}: Already solved")
            return
    command = f'echo "{fen}" | texelutil proofgame -f -o {TEXELUTIL_RES_DIR}/result_t_{thread_id}_ -rnd {SEED} 2>{DATA_DIR}/logs/debug_t_{thread_id}_.log'
    try:
        subprocess.run(command, shell=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"Thread {thread_id}: Timeout expired")

def convert_to_pgn(moves):
    moves = moves.split()
    pgn = ""
    for i in range(0, len(moves), 2):
        move_number = i // 2 + 1
        pgn += f"{move_number}. {moves[i]} "
        if i + 1 < len(moves):
            pgn += f"{moves[i + 1]} "
    return pgn.strip()

def validate_pgn(pgn : str, fen : str, ignore_move_number=True):
    board = chess.Board()
    game = chess.pgn.read_game(io.StringIO(pgn))
    for move in game.mainline_moves():
        board.push(move)
    if ignore_move_number:
        fen = " ".join(fen.split()[:-2])
        return board.fen().startswith(fen)
    else:
        return board.fen() == fen

def process_output(thread_id) -> str:
    i = 0
    while os.path.exists(f"{TEXELUTIL_RES_DIR}/result_t_{thread_id}_{i:02d}"):
        i += 1
    last_file = f"{TEXELUTIL_RES_DIR}/result_t_{thread_id}_{i - 1:02d}"
    with open(last_file, "r") as f:
        content = f.read()
    match = re.search(r"legal: proof: (.*)", content)
    if match:
        moves = match.group(1)
        pgn = convert_to_pgn(moves)
        if validate_pgn(pgn, fens[thread_id]):
            print(f"Thread {thread_id}: Proof game is valid")
            return pgn
        else:
            print(f"Thread {thread_id}: Proof game is invalid")
            return None
    else:
        print(f"Thread {thread_id}: No proof game found")
        return None

def main(args):
    global fens
    if args.fens_file:
        df = pd.read_csv(args.fens_file)
        fens = df['FEN'].tolist()
    else:
        fens = fens_test

    print(f"Computing {len(fens)} proof games")
    for i in range(0, len(fens), MAX_THREADS):
        print(f"Processing {i} to {i + MAX_THREADS}")
        pool = multiprocessing.Pool(MAX_THREADS)
        with pool:
            pool.starmap(run_command, [(fen, i + thread_id) for thread_id, fen in enumerate(fens[i:i + MAX_THREADS])])
        pool.close()
        pool.join()
        # kill texelutil bc it's not closing properly
        subprocess.run("killall texelutil", shell=True)
        time.sleep(5)

    print("Processing output")
    if args.fens_file:
        for thread_id in tqdm(range(len(fens))):
            pgn = process_output(thread_id)
            if pgn:
                df.loc[thread_id, 'proofgame'] = pgn
            else:
                df.loc[thread_id, 'proofgame'] = None
        df.to_csv(args.save_filename, index=False)
    else:
        for thread_id in tqdm(range(len(fens))):
            process_output(thread_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fens_file", help="CSV file with a 'FEN' column", default=None)
    parser.add_argument("--save_filename", help="File to save the results", default="/data/chess-data/lichess_puzzles/proofgame_pgns.csv")
    args = parser.parse_args()
    main(args)


