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

import time
import chess
import chess.pgn
import io
import csv
import os
import re
import pickle
from pathlib import Path


DATA_DIR = Path("/data/chess-data/lichess_puzzles")  # Set the desired path to the data folder

def download_and_decompress(url, path):
    # Download to DATA_DIR, not here
    if not path.exists():
        path.mkdir(parents=True)

    filename = os.path.join(path, os.path.basename(url))
    if os.path.exists(filename):
        print("Already downloaded", url)
        if os.path.exists(filename.split(".zst")[0]):
            print("Already decompressed", url)
            return
        # Decompress to that folder too
        os.popen("zstd -d " + filename).read()
        return
    
    if os.path.exists(filename.split(".zst")[0]):    
        print("Already decompressed", url)
        return

    print("Downloading", url)
    os.popen("wget -O " + filename + " " + url).read()

    time.sleep(1)
    # Decompress to that folder too
    os.popen("zstd -d " + filename).read()




def generate_mapping(filename):
    mapping = {}

    # Regular expression pattern to match the game ID from the Site URL
    site_pattern = re.compile(r'\[Site "https://lichess.org/([a-zA-Z0-9]+)"]')

    # Open the file in binary mode to compute byte offsets
    with open(filename, 'rb') as f:
        line = f.readline()
        while line:
            match = site_pattern.search(line.decode('utf-8'))
            if match:
                current_game_id = match.group(1)
                mapping[current_game_id] = f.tell() - len(line)  # Get the starting byte offset of this line
            line = f.readline()

    return mapping

def fetch_game_moves(filename, game_id, offset):
    moves = []
    with open(filename, 'r') as f:
        f.seek(offset)
        pgn = f.read(10000).split("[Event")[0]
        

    return pgn

def convert_pgn_to_game(pgn_moves):
    pgn = io.StringIO(pgn_moves)
    game = chess.pgn.read_game(pgn)
    if len(game.errors) > 0:
        return None
    return game

def process_puzzles(puzzles_filename, games_filename, mapping ):
    extracted_puzzles = []

    with open(puzzles_filename, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            game_url, uci_moves = row[8], row[2].split()
            game_id = game_url.split('.org/')[1]
            move_num = int(game_url.split('#')[-1])
            game_id = game_id.split("/")[0].split("#")[0]
            rating = int(row[3])

            if game_id in mapping:
                pgn = fetch_game_moves(games_filename, game_id, mapping[game_id])
                game = convert_pgn_to_game(pgn)
                if game is None: continue

                board = game.board()

                for move in list(game.mainline_moves())[:move_num]:
                    board.push(move)

                new_board = board.copy()

                try:
                    solution = []
                    for move in uci_moves[1:]:
                        m = chess.Move.from_uci(move)
                        solution.append(new_board.san(m))
                        new_board.push(m)
                except:
                    print("Board import failed")
                    continue

                extracted_puzzles.append((row[0],
                                          rating,
                                         board,
                                         solution,
                ))
                print(len(extracted_puzzles))

    with open(os.path.join(games_filename.parent, "pgn_puzzles.csv"), "w") as f:
        writer = csv.writer(f)
        for uid, rating, board, solution in extracted_puzzles:
            writer.writerow((uid, rating,
                             str(chess.pgn.Game().from_board(board)).split("\n")[-1][:-2],
                             " ".join(solution)))






if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", "-d", help="Name of the data directory", default="/data/chess-data/lichess_puzzles")
    parser.add_argument("--batches", "-b", nargs='+', help="Name of the batch", default=["2014-06"])
    args = parser.parse_args()

    global DATA_DIR
    DATA_DIR = Path(args.data_dir)

    #batches = ["2023-05"]
    batches = args.batches

    url_puzzles="https://database.lichess.org/lichess_db_puzzle.csv.zst"
    download_and_decompress(url_puzzles, DATA_DIR)
    for batch in batches:
        archive = f"lichess_db_standard_rated_{batch}.pgn"
        path = DATA_DIR / batch
        url_games = f"https://database.lichess.org/standard/{archive}.zst"
        download_and_decompress(url_games, path)


        filename = path / archive
        mapping = generate_mapping(filename)

        with open(os.path.join(path, 'mapping.pickle'), 'wb') as f:
            pickle.dump(mapping, f)
        process_puzzles(puzzles_filename=DATA_DIR / "lichess_db_puzzle.csv", games_filename=filename, mapping=pickle.load(open(path / "mapping.pickle","rb")))

