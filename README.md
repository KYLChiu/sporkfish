# Sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Prod/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)

Sporkfish is a Python-based chess engine. Chess programming techniques, although numerous, are not always well-documented. This project aims to bridge that gap by offering clear, working, and accessible code, providing a resource for developers interested in understanding and implementing chess engine algorithms.

- - - -

## Set-up

See any of the following sections to quickly setup your development environment.
- [Using DevContainer with VSCode](#using-devcontainer-with-vscode)* *recommended*
- [Using DevContainer with PyCharm](#using-devcontainer-with-pycharm)
- [Using Github Codespace](#using-github-codespace)

### Using DevContainer with VSCode

Prerequisites:
- [VSCode](https://code.visualstudio.com/download)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

Instructions:
1. Make sure `Docker Desktop` is up and running.
2. Open up the Command Palette and run `Dev Containers: Rebuild Container`
3. The window should reload and you will see `[Dev Container]` in the URL bar as well as on the status bar bottom left of the window to indicate your setup is complete.

This will setup a Docker container to run in Docker Desktop with all the necessary dependencies (python, pip, git, ...) with the correct versions.

### Using DevContainer with PyCharm

Prerequisites:
- [PyCharm](https://www.jetbrains.com/pycharm/download/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

Instructions:

#TODO - Please see jetbrains docs, PyCharm setup is similar to VSCode

https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html

### Using Github Codespace

Prerequisites:
- [VSCode](https://code.visualstudio.com/download)* *optional*

Instructions:
1. In this Github repository, click on the Code dropdown, select Codespace and click `Create`.
2. Confirm codespace settings, for Machine type select `2-core` (this can be changed later if you require more power)

This will setup a Dockeer container to run in Github with all the necessary dependencies (python, pip, git, ...) with the correct versions. An active internet connection will be required for this, and this will use up your monthly allowance for Github codespace.

### Using native Docker

To quickly set up the environment, you can use docker. From a terminal in the root directory:

```
docker pull kylchiu/sporkfish-dev:latest
docker build -t kylchiu/sporkfish-dev:latest .
docker run -it kylchiu/sporkfish-dev:latest
```

This generates an interactive bash shell for you to run the program in.

## Usage

### Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file in the root directory named `api_token.txt`. Add your Lichess bot API token. Then run:

```
python3 main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

- - - -

## Principles

* Functional library: encourage free functions whilst avoiding mutable data unless the task specifically and inherently demands it (e.g. statistics, transposition table, board state).
* Well documented: classes should always have docstrings. Where the code is complex, additional inline comments should be made.

- - - -

## Features

Search:

* [Negamax with fail-soft alpha-beta pruning](https://www.cs.cornell.edu/courses/cs312/2002sp/lectures/rec21.htm)
* [Quiescence search](https://www.chessprogramming.org/Quiescence_Search)
* [Iterative deepening](https://www.chessprogramming.org/Iterative_Deepening)
* [Null move pruning](https://www.chessprogramming.org/Null_Move_Pruning)
* [Futility pruning](https://www.chessprogramming.org/Futility_Pruning)
* [Delta pruning](https://www.chessprogramming.org/Delta_Pruning)
* [Aspiration windows](https://www.chessprogramming.org/Aspiration_Windows)
* [Transposition tables with Zobrist hashing](https://mediocrechess.blogspot.com/2007/01/guide-transposition-tables.html)
* [PolyGlot opening book](https://python-chess.readthedocs.io/en/latest/polyglot.html)
* [Syzygy endgame tablebases](https://python-chess.readthedocs.io/en/latest/syzygy.html#chess.syzygy.Tablebase)

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

- - - -

## For developers

### Run Tests

To run all tests (excluding slow tests):

```
python3 -m pytest -v
```

You may also run a specific test class or function, e.g.:

```
python3 -m pytest tests/test_searcher.py::TestMvvLvaHeuristic -sv
```

Slow tests are not run on CI. Developers should run these before raising PRs by doing (this can be very slow, so please be patient):

```
python3 -m pytest -sv --runslow
```

### Sphinx auto docstring generation (with Github Copilot and devcontainer)

This may or may not work depending if Copilot is happy on that day. ***Simply ask Copilot to generate your class with Sphinx docstrings.*** If that does not work, you could try:
1. Implement your class or function with type hints.
2. Add a template Sphinx docstring at the class level, i.e. above `__init__` function. This can be done using `Ctrl + Shift + 2` (Windows, Linux) or `Command + Shift + 2` (Mac). Add ":param:" in your string if it isn't auto generated.
3. Using the Command Pallete, select "Github Copilot: Generate Docs" while your text cursor is inside the template Sphinx docstring. ***It should auto generate Sphinx docs for the entire class/function.***

- - - -