#/bin/bash

# Run pip install
python -m ensurepip --upgrade
pip install -r requirements.txt

# Install pre-commit and pre-push
# https://github.blog/2022-04-12-git-security-vulnerability-announced/
# This doesn't concern us as we own the repository...
git config --global --add safe.directory $(pwd)
pre-commit install --hook-type pre-commit
pre-commit install --hook-type pre-push

exit 0
