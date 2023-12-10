import subprocess
import os
import chess
import chess.engine
import pytest
import PyInstaller  # for pipreqs


def test_engine_e2e():
    dist_path = "dist"
    pyinstaller_command = f"pyinstaller -F main.py --distpath {dist_path}"
    process = subprocess.run(
        pyinstaller_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Check the exit code
    assert (
        process.returncode == 0
    ), f"PyInstaller command failed with output: {process.stderr.decode()}"

    engine = chess.engine.SimpleEngine.popen_uci(os.path.join(dist_path, "main"))

    # Simulate play
    board = chess.Board()
    for _ in range(4):
        result = engine.play(board, chess.engine.Limit(time=30.0))
        assert result is not None
        board.push(chess.Move.from_uci(str(result.move)))

    # Clean up: remove the 'dist' directory
    subprocess.run(f"rm -r {dist_path}", shell=True)
    subprocess.run(f"rm main.spec", shell=True)

    engine.quit()
