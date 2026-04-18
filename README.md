# Sporkfish

[Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Prod/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)

Sporkfish is a Python-based chess engine. Chess programming techniques, although numerous, are not always well-documented. This project aims to bridge that gap by offering clear, working, and accessible code, providing a resource for developers interested in understanding and implementing chess engine algorithms.

```
  a b c d e f g h
8 ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜  8
7 ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟  7
6 · · · · · · · ·  6
5 · · · · · · · ·  5
4 · · · · · · · ·  4
3 · · · · · · · ·  3
2 ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙  2
1 ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖  1
  a b c d e f g h
```

**Move decision pipeline:**

```
            ┌─────────────────────────────────────────┐
            │              Engine.best_move           │
            └──────────┬─────────────┬────────────────┘
                       │             │
            ┌──────────▼──────┐  ┌───▼──────────────┐
            │  Opening Book   │  │ Endgame Tablebase │
            │  (PolyGlot .bin)│  │  (Syzygy .rtbw/z) │
            └──────────┬──────┘  └───┬───────────────┘
                       │  miss       │ miss
                       └──────┬──────┘
                              │
                   ┌──────────▼──────────┐
                   │   Searcher (PVS /   │
                   │   Negamax + ID)     │
                   └──────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
   ┌──────────▼───┐  ┌────────▼──────┐  ┌────▼──────────────┐
   │ Move Ordering│  │  Alpha-Beta   │  │    Evaluator      │
   │  (MVV-LVA,   │  │  (LMR, NMP,   │  │  (PeSTO tapered   │
   │  Killers,    │  │  futility,    │  │   eval + increm-  │
   │  History,    │  │  delta, TT,   │  │   ental accum.)   │
   │  Hash move)  │  │  aspiration)  │  └───────────────────┘
   └──────────────┘  └───────────────┘
```

- - - -

## Setup

See any of the following sections to quickly setup your development environment.
- [Using DevContainer with VSCode](#using-devcontainer-with-vscode)* *recommended*
- [Using DevContainer with PyCharm](#using-devcontainer-with-pycharm)
- [Using Github Codespace](#using-github-codespace)
- [Using native Docker](#using-native-docker)

### Using DevContainer with VSCode

Prerequisites:
- [VSCode](https://code.visualstudio.com/download)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

Instructions:
1. Make sure `Docker Desktop` is up and running.
2. Open up the Command Palette and run `Dev Containers: Rebuild Container`
3. The window should reload and you will see `[Dev Container]` in the URL bar as well as on the status bar bottom left of the window to indicate your setup is complete.

### Using Github Codespace

Prerequisites:
- [VSCode](https://code.visualstudio.com/download)* *optional*

Instructions:
1. In this Github repository, click on the Code dropdown, select Codespace and click `Create`.
2. Confirm codespace settings, for Machine type select `2-core` (this can be changed later if you require more power).

An active internet connection will be required for this. This will also use up your monthly allowance for Github codespace.

### Using native Docker

Prerequisites:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

After cloning the repository, from the root directory, run:

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
python3 -O main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

- - - -

## Features

### How Negamax works

Chess is a zero-sum game: whatever is good for White is equally bad for Black. **Negamax** exploits this by using a single recursive function for both sides — a node always evaluates positions from the *current player's* perspective and negates the child's score (which is from the opponent's perspective).

```
negamax(pos, depth, α, β):
    if depth == 0: return evaluate(pos)          # leaf: static eval
    for each move in ordered_moves(pos):
        pos.push(move)
        score = -negamax(pos, depth-1, -β, -α)   # flip & negate
        pos.pop()
        if score > α:
            α = score                             # raise lower bound
        if α >= β:
            return α                              # β-cutoff: prune branch
    return α
```

Traced through a 3-ply tree (depth 2, White to move at root):

```
depth 2 (White, maximise)          root  α=-∞  β=+∞
                                  /                  \
depth 1 (Black, maximise      A  α=-∞  β=+∞       B  α=-∞  β=-3
         from Black's POV)   / \                  / \
depth 0 (leaves)            a₁  a₂              b₁  b₂
                           +5   +3              -7   +9

Step-by-step:

  1. Evaluate a₁ = +5  → score = -(+5) = -5 at A, α_A = -5
  2. Evaluate a₂ = +3  → score = -(+3) = -3 at A, α_A = -3
     A returns -3  (best Black can guarantee in this sub-tree)

  3. At root: score = -(-3) = +3, α_root = +3

  4. Start node B with α=-∞, β = -(α_root) = -3
     Evaluate b₁ = -7  → score = -(-7) = +7 at B, α_B = +7
     α_B(+7) >= β_B(-3)  →  ✂ PRUNE b₂ (beta cutoff!)
     B returns +7

  5. At root: score = -(+7) = -7,  -7 < α_root(+3) → no improvement.
     Root returns +3 and picks move A.

  Result: root = +3 via move A, b₂ was never evaluated.

  ✂ = pruned (the opponent would never allow this line)
```

**Alpha-beta pruning** prunes the tree by maintaining a window `[α, β]`:
- `α` — the best score the current player is *guaranteed* so far (lower bound).
- `β` — the best score the opponent is *guaranteed* so far (upper bound).

When `α ≥ β`, the opponent would never allow this line, so the branch is cut.

In deeper trees, good move ordering means roughly half the nodes
can be pruned, effectively **doubling the searchable depth** for the same time budget.

Sporkfish enhances plain negamax with:

| Technique | Benefit |
|---|---|
| **Principal Variation Search (PVS)** | Search first move with full window; use cheap null-window for the rest |
| **Iterative Deepening** | Search depth 1→N; earlier results seed move ordering for later depths |
| **Aspiration Windows** | Narrow the root window around the previous iteration's score |
| **Null-move pruning** | Pass a turn; if still above β, prune (opponent can't recover) |
| **Futility / delta pruning** | Skip near-leaf moves that can't possibly raise α |
| **Check extensions** | Add 1 extra ply when the side to move is in check |
| **Late Move Reduction (LMR)** | Reduce depth for quiet moves ordered late (unlikely to be best) |
| **Quiescence search** | Extend on captures only until position is "quiet" before evaluating |
| **Transposition table (TT)** | Cache (Zobrist hash → score) to avoid re-searching repeated positions |
| **Move ordering** | MVV-LVA + killer moves + history heuristic + TT hash move |

- - - -

## Search features

* [Negamax with fail-soft alpha-beta pruning](https://www.cs.cornell.edu/courses/cs312/2002sp/lectures/rec21.htm)
* [Principal variation search](https://en.wikipedia.org/wiki/Principal_variation_search)
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

- - - -