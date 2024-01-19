import subprocess
import os
import chess
import chess.engine
import pytest
import PyInstaller  # for pipreqs


def test_engine_e2e():
    fp = os.path.abspath(__file__)
    dist_path = "dist"
    pyinstaller_command = f"pyinstaller main.py --distpath {dist_path} --onedir"
    subprocess.run(pyinstaller_command, shell=True)

    with chess.engine.SimpleEngine.popen_uci(
        os.path.abspath(os.path.join(fp, "../", "../", dist_path, "main/main.exe")), debug=True
    ) as engine:
        # Simulate play
        board = chess.Board()
        for _ in range(4):
            result = engine.play(board, chess.engine.Limit(time=30.0))
            assert result is not None
            board.push(chess.Move.from_uci(str(result.move)))

    # Clean up: remove the 'dist' directory
    subprocess.run(f"rm -r {dist_path}", shell=True)
    subprocess.run(f"rm main.spec", shell=True)
