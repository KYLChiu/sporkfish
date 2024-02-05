#/bin/bash

# Run pip install
pip install -r requirements.txt

# Install pre-commit and pre-push
pre-commit install --hook-type pre-commit --hook-type pre-push

exit 0
