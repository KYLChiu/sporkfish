# Sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Python/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)

Sporkfish is a Python-based chess engine. Chess programming techniques, although numerous, are not always well-documented. This project aims to bridge that gap by offering clear, working, and accessible code, providing a resource for developers interested in understanding and implementing chess engine algorithms.

## Usage

# Set up

To quickly set up the environment, you can use docker. From a terminal in the root directory:

```
docker build -t sporkfish-devenv .
docker run -it sporkfish-devenv
```

This generates an interactive bash shell for you to run the program in.

# Run Tests

To run all tests:

```
python3 -m pytest -sv
```

To run a specific file/module:

```
python3 -m pytest -sv
```

To run a specific test class:

```
python3 -m pytest tests/test_searcher.py::TestQuiescence -sv
```

To run a specific test function:

```
python3 -m pytest tests/test_searcher.py::test_pos2_perf -sv
```

### Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file in the root directory named `api_token.txt`. Add your Lichess bot API token. Then run:

```
python3 main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

## Principles

* Functional library: encourage free functions whilst avoiding mutable data unless the task specifically and inherently demands it (e.g. statistics, transposition table, board state).
* Well documented: classes should always have docstrings. Where the code is complex, additional inline comments should be made.

## Features

Search:

* [Negamax with fail-soft alpha-beta pruning](https://www.cs.cornell.edu/courses/cs312/2002sp/lectures/rec21.htm)
* [MVV-LVA move ordering](https://www.chessprogramming.org/Move_Ordering)
* [PolyGlot opening book querying](https://python-chess.readthedocs.io/en/latest/polyglot.html)
* [Quiescence search](https://www.chessprogramming.org/Quiescence_Search)
* [Transposition tables with Zobrist hashing](https://mediocrechess.blogspot.com/2007/01/guide-transposition-tables.html)

Evaluation:

* [PeSTO](https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function)

Communication:

* [UCI](https://www.chessprogramming.org/UCI)

## Resources

* [Some techniques](https://stackoverflow.com/questions/16500739/chess-high-branching-factor/16642804#16642804)
* [Engine improvement tier list](https://www.reddit.com/r/ComputerChess/comments/yln9ef/comparative_advantage_of_engine_improvements/)
* [Black Marlin](https://github.com/jnlt3/blackmarlin?tab=readme-ov-file#efficiently-updatable-neural-networks)
* [Explaining beta-cutoff](https://stackoverflow.com/questions/2533219/alpha-beta-cutoff)
