# Sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Prod/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)

Sporkfish is a Python-based chess engine. Chess programming techniques, although numerous, are not always well-documented. This project aims to bridge that gap by offering clear, working, and accessible code, providing a resource for developers interested in understanding and implementing chess engine algorithms.

- - - -

## Usage

### Set up

As a general case `Using DevContainer with VSCode` or `Using Github Codespace`

Install: 
- [VSCode](https://code.visualstudio.com/download)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

#### Using DevContainer with VSCode 

1. Make sure Docker Desktop is up and running.
2. Open up the Command Palette and run `Dev Containers: Rebuild Container` 
3. A warning might pop up saying `Not all host requirements in devcontainer.json are met by the Docker daemon.`, disregard this and continue. 
4. The window should reload and you will see [Dev Container] in the URL bar as well as on the status bar bottom right of the window to indicate your setup is complete. 

This will setup a Docker container to run in Docker Desktop with all the neceessary dependencies (python, pip, git, ...) with the correct versions. 

\* Please exit out of the container to commit your git changes for now as the ssh keys aare not being mounted to the container. This will be fixed soon. 

#### Using Github Codespace

You do not need to install Docker Desktop with this option. 

1. In this Github repository, click on the Code dropdown, select Codespace and click `Create`. 
2. Continue through all prompts using default options. 

This will setup a Docker container to run in Github instead of Docker Desktop. All else being equal, but an active internet connection will be required for this, and this will use up your monthly allowance for Github codespace. 

#### Using DevContainer without VSCode

You do not need to install VSCode with this option.

#TODO

### Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file in the root directory named `api_token.txt`. Add your Lichess bot API token. Then run:

```
python3 main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

### Run Tests

To run all tests (excluding slow tests):

```
python3 -m pytest -v
```

You may also run a specific test class or function, e.g.:

```
python3 -m pytest tests/test_searcher.py::TestMvvLvvHeuristic -sv
```

Slow tests are not run on CI. Developers should run these before raising PRs by doing (this can be very slow, so please be patient):

```
python3 -m pytest -sv --runslow
```

### Code formatting

Before submitting your code, please run

```
isort --profile black .
black .
```

- - - -

## Principles

* Functional library: encourage free functions whilst avoiding mutable data unless the task specifically and inherently demands it (e.g. statistics, transposition table, board state).
* Well documented: classes should always have docstrings. Where the code is complex, additional inline comments should be made.

- - - -

## Features

Search:

* [Negamax with fail-soft alpha-beta pruning](https://www.cs.cornell.edu/courses/cs312/2002sp/lectures/rec21.htm)
* [PolyGlot opening book querying](https://python-chess.readthedocs.io/en/latest/polyglot.html)
* [Quiescence search](https://www.chessprogramming.org/Quiescence_Search)
* [Iterative deepening](https://www.chessprogramming.org/Iterative_Deepening)
* [Null move pruning](https://www.chessprogramming.org/Null_Move_Pruning)
* [Delta pruning](https://www.chessprogramming.org/Delta_Pruning)
* [Aspiration windows](https://www.chessprogramming.org/Aspiration_Windows)
* [Transposition tables with Zobrist hashing](https://mediocrechess.blogspot.com/2007/01/guide-transposition-tables.html)

Move ordering:

* [MVV-LVA move ordering](https://www.chessprogramming.org/Move_Ordering)

Evaluation:

* [PeSTO](https://www.chessprogramming.org/PeSTO%27s_Evaluation_Function)

Communication:

* [UCI](https://www.chessprogramming.org/UCI)

- - - -

## Resources

### Engines

* [cpw-engine](https://github.com/nescitus/cpw-engine)
* [Black Marlin](https://github.com/jnlt3/blackmarlin?tab=readme-ov-file#efficiently-updatable-neural-networks)
* [Theodora](https://github.com/yigitkucuk/Theodora/blob/main/main.py)
* [black_numba](https://github.com/Avo-k/black_numba)

### References

* [Some techniques](https://stackoverflow.com/questions/16500739/chess-high-branching-factor/16642804#16642804)
* [Engine improvement tier list](https://www.reddit.com/r/ComputerChess/comments/yln9ef/comparative_advantage_of_engine_improvements/)
* [Explaining beta-cutoff](https://stackoverflow.com/questions/2533219/alpha-beta-cutoff)

### Video (Youtube) Resources - beginner friendly

* Gentle introduction to how to set up a chess bot by [Sebastian Lague](https://www.youtube.com/watch?v=U4ogK0MIzqk)
* How to improve a chess bot by [Sebastian Lague](https://www.youtube.com/watch?v=_vqlIPDR2TU)
* Introduction to Minimax and Alpha-Beta Pruning:
  * by [Sebastian Lague](https://www.youtube.com/watch?v=l-hh51ncgDI)
  * by [MIT OpenCourseWare](https://www.youtube.com/watch?v=STjW3eH0Cik)
* Iterative Deepening Search:
  * by [John Levine](https://www.youtube.com/watch?v=Y85ECk_H3h4) - in context of DFS
  * by [Chess Programming](https://www.youtube.com/watch?v=awZxXMJ-h0Y) - in the context of chess programming
