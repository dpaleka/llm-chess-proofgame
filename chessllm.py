#!/usr/bin/env python3

## Copyright (C) 2023, Nicholas Carlini <nicholas@carlini.com>.
## Copyright (C) 2023, Daniel Paleka <danepale@gmail.com>.
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
import chess.engine
import chess.pgn
from litellm import completion

from cachier import cachier
from cachier import set_default_params as cachier_set
import datetime
cachier_set(stale_after=datetime.timedelta(days=30), pickle_reload=False, cache_dir="/data/chess/cache")

class ChessLLM:
    def __init__(self, api_key, config, model : str = "gpt-3.5-turbo-instruct", use_cache : bool = True, **override):
        self.config = config
        self.model = model
        for k,v in override.items():
            config[k] = v
        self.use_cache = use_cache
        self.api_key = api_key


    def get_query_pgn(self, board, with_header = f"""[White "Magnus Carlsen"]\n[Black "Garry Kasparov"]\n[WhiteElo "2900"]\n[BlackElo "2800"]\n\n"""):
        pgn = str(chess.pgn.Game().from_board(board))

        if board.outcome() is None:
            pgn = pgn[:-1].strip()
        else:
            print("Game is over; no moves valid")
            return None

        if board.turn == chess.WHITE:
            if board.fullmove_number == 1:
                pgn = pgn + "\n\n1."
            else:
                pgn += ' '+str(board.fullmove_number)+"."

        with_header += pgn.split("\n\n")[1]

        return with_header

    def try_moves(self, board, next_text):
        board = board.copy()
        moves = next_text.split()
        ok_moves = []
        for move in moves:
            if '.' in move:
                continue
            try:
                board.push_san(move)
                ok_moves.append(move)
            except:
                break

        return ok_moves
    
    def get_best_move(self, board, num_tokens=None, conversation=None):
        if num_tokens is None:
            num_tokens = self.config['num_lookahead_tokens']
        assert num_tokens >= 9, "A single move might take as many as 9 tokens (3 for the number + 6 for, e.g., 'N3xg5+)."

        pgn_to_query = self.get_query_pgn(board)

        if conversation:
            conversation.send_message("player", f"Querying {self.config['model']} with ... {pgn_to_query.split(']')[-1][-90:]}")
            conversation.send_message("spectator", f"Querying {self.config['model']} with ... {pgn_to_query.split(']')[-1][-90:]}")
        
        next_text = self.make_request(pgn_to_query, num_tokens, temperature=self.config['temperature'], model=self.model, ignore_cache = not self.use_cache)
        if next_text[:2] == "-O":
            next_text = self.make_request(pgn_to_query+" ", num_tokens, temperature=self.config['temperature'], model=self.model, ignore_cache = not self.use_cache)

        if conversation:
            conversation.send_message("spectator", f"Received reply of '{next_text}'")

        next_moves = self.try_moves(board, next_text)

        if len(next_moves) == 0:
            conversation.send_message("player", "Tried to make an invalid move.")
            conversation.send_message("spectator", "Tried to make an invalid move.")
            return None

        if conversation:
            conversation.send_message("player", f"Received reply and making move {next_moves[0]}.")

        return next_moves[0]

    @cachier()
    def make_request(self, content, num_tokens, temperature, model="gpt-3.5-turbo-instruct", **kwargs):
        # kwargs are here for compatibility with local model calls through fastapi
        print("Not using cache")
        if model.startswith("BlueSunflower"):
            raise NotImplementedError("Pythia chess is not supported yet")

        response = completion(model, messages=[{"role": "user", "content": content}], **{"max_tokens": num_tokens, "temperature": temperature})
        return response["choices"][0]["message"]["content"]
