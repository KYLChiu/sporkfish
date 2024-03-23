#/bin/bash

# Run pip install
python3 -m ensurepip --upgrade
python3 -m pip install -r requirements.txt

# Install pre-commit and pre-push
# https://github.blog/2022-04-12-git-security-vulnerability-announced/
# This doesn't concern us as we own the repository...
git config --global --add safe.directory $(pwd)
python3 -m pre-commit install --hook-type pre-commit
python3 -m pre-commit install --hook-type pre-push

exit 0
