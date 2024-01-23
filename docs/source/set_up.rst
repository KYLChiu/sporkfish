.. Sporkfish documentation setup file.


Setting up Sporkfish
====================


.. toctree::
   :maxdepth: 2
   :caption: Contents:


To quickly set up the environment, you can use docker. From a terminal in the root directory:

```
docker build -t sporkfish-devenv .
docker run -it sporkfish-devenv
```

This generates an interactive bash shell for you to run the program in.

Lichess

Check out the bot on lichess [here](https://lichess.org/@/Sporkfish)! To run the bot, create a file in the root directory named `api_token.txt`. Add your Lichess bot API token. Then run:

```
python3 main.py
```

Once you create a game via your bot account, the bot will automatically play. We currently do not support simultaneous games.

### Run Tests

To run all tests:

```
python3 -m pytest -v
```

You may also run a specific test class or function, e.g.:

```
python3 -m pytest tests/test_searcher.py::TestMvvLvvHeuristic -sv
```

### Code formatting

Before submitting your code, please run

```
isort --profile black .
black .
```
