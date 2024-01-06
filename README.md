# sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Python/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)


Sporkfish is a Python-based chess engine. Within the realm of chess programming, the abundance of resources can be overwhelming. This repository's primary objective is to provide code that is both readable and well organised, demystifying techniques that may be perceived as esoteric or challenging to grasp.

## Usage

### Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file called `api_token.txt` containing your Lichess bot API token. Then run:
```
python3 main.py
```
Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

The code is also pypy compatible, i.e. you can instead use:
```
pypy3 main.py
```

### UCI Engine

Change main.py flag to "UCI" and run as usual.

## Features
Search:
* [Negamax with fail-soft alpha-beta pruning](https://www.cs.cornell.edu/courses/cs312/2002sp/lectures/rec21.htm)
* [MVV-LVA move ordering](https://www.chessprogramming.org/Move_Ordering)
* [PolyGlot opening book querying](https://python-chess.readthedocs.io/en/latest/polyglot.html)
* [Quiescence search](https://www.chessprogramming.org/Quiescence_Search)
* [Transposition tables with Zorbist hashing](https://mediocrechess.blogspot.com/2007/01/guide-transposition-tables.html)

Evaluation:
* [PeSTO](https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function)

Communication:
* [UCI](https://www.chessprogramming.org/UCI)

Resources:
* [Some techniques](https://stackoverflow.com/questions/16500739/chess-high-branching-factor/16642804#16642804)
* [Black Marlin](https://github.com/jnlt3/blackmarlin?tab=readme-ov-file#efficiently-updatable-neural-networks)
* [Explaining beta-cutoff](https://stackoverflow.com/questions/2533219/alpha-beta-cutoff)
