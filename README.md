# sporkfish

[![Actions Status](https://github.com/KYLChiu/sporkfish/workflows/Python/badge.svg)](https://github.com/KYLChiu/sporkfish/actions)


Sporkfish is a Python-based chess engine. Within the realm of chess programming, the abundance of resources can be overwhelming. This repository's primary objective is to provide code that is both readable and well organised, demystifying techniques that may be perceived as esoteric or challenging to grasp.

## Usage

### Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! It currently plays at approximately **1400** lichess rating (a beginner/intermediate club player). To set up your own bot, follow the instructions at [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot) API. The executable can be created using [PyInstaller](https://pypi.org/project/pyinstaller/):

```
pip install -r requirements.txt
pyinstaller -F main.py --add-data "data/*:data" --distpath <path/to/lichess-bot/engines>
```

### UCI Engine

```
pip install -r requirements.txt
python main.py
```

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

## Work in progress

* [NNUE evaluation](https://www.chessprogramming.org/NNUE)
* Running on AWS as a systemd process, automating the bot on lichess

## Things to consider for future

* Speed (Numba / CUDA / SIMD)
* Parallelisation