#!/bin/bash

source="./engines"
dest="../lichess-bot/engines"

# Create the ./engines folder
if [ ! -d "$source" ]; then
    mkdir -p "$source"
    echo "Source created: $source"
fi

# Install
echo "Installing into path $source"
pyinstaller -F main.py --add-data "data/opening.bin:data" --distpath "$source" > /dev/null 2>&1

# Remove and re-create destination
rm -r "$dest"
echo "Destination removed: $dest"
mkdir $dest

# Copy
if [ -d "$dest" ]; then
    cp -r "$source"/* "$dest"
    echo "Contents copied to destination: $dest"
else
    echo "Destination directory does not exist: $dest"
fi

# Remove source files and directory
rm -r "$source"
echo "Source removed: $source"
rm main.spec
rm -r build

# Run the bot
cd ../lichess-bot/
source ./venv/bin/activate
python3 lichess-bot.py -v