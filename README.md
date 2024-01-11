# Sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Python/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)

Sporkfish is a Python-based chess engine. Chess programming techniques, although numerous, are not always well-documented. This project aims to bridge that gap by offering clear, working, and accessible code, providing a resource for developers interested in understanding and implementing chess engine algorithms.

## Usage

To quickly set up the environment, you can use docker. From a terminal in the root directory:

```
docker build -t sporkfish-devenv .
docker run -it sporkfish-devenv
```

This generates an interactive bash shell for you to run the program in.

### Lichess (main.py, recommended)

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file in the root directory named `api_token.txt`. Add your Lichess bot API token. Then run:
```
python3 main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

The code is also pypy compatible, i.e. you can instead use:

```
pypy3 main.py
```

### Lichess (PyInstaller)

Alternatively, to create an executable that can be run with [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot), simply use `PyInstaller`:
```
pyinstaller -F main.py --add-data "data/opening.bin:data" --distpath "<your_dist_path>"
```
This has been tested succesfully on Linux only.

### UCI Engine

Change main.py flag to "UCI" and run as usual.

## Principles

* Functional library: encourage free functions whilst avoiding mutable data unless the task specifically and inherently demands it (e.g. statistics, transposition table, board state).
* Well documented: functions should always have docstrings. Where the code complex, additional inline comments should be made.

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

## Resources
* [Some techniques](https://stackoverflow.com/questions/16500739/chess-high-branching-factor/16642804#16642804)
* [Engine improvement tier list](https://www.reddit.com/r/ComputerChess/comments/yln9ef/comparative_advantage_of_engine_improvements/)
* [Black Marlin](https://github.com/jnlt3/blackmarlin?tab=readme-ov-file#efficiently-updatable-neural-networks)
* [Explaining beta-cutoff](https://stackoverflow.com/questions/2533219/alpha-beta-cutoff)
