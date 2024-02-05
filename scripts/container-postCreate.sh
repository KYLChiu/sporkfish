#/bin/bash

# Run pip install
pip install -r requirements.txt

# Hack...?
git config --global --add safe.directory $(pwd)

# Install pre-commit and pre-push
pre-commit install --hook-type pre-commit
pre-commit install --hook-type pre-push

exit 0
