import argparse
import copy
import csv
import logging
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import chess
import chess.pgn
import yaml
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from init_board_helper import board_setup

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.evaluator.evaluator_config import EvaluatorConfig
from sporkfish.evaluator.evaluator_factory import EvaluatorFactory
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory


def _set_nested(d: Dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    cur = d
    for key in keys[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[keys[-1]] = value


def _parse_override(entry: str) -> Tuple[str, Any]:
    if "=" not in entry:
        raise ValueError(f"Override must be key=value, got: {entry}")
    key, raw = entry.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Override key cannot be empty: {entry}")
    return key, yaml.safe_load(raw)


def _score_to_elo(score: float) -> float:
    if score <= 0.0:
        return float("-inf")
    if score >= 1.0:
        return float("inf")
    return -400.0 * math.log10((1.0 / score) - 1.0)


def _safe_uci(move: chess.Move) -> str:
    return move.uci() if move != chess.Move.null() else "0000"


@dataclass(frozen=True)
class RunnerCfg:
    label: str
    evaluator_cfg: Dict[str, Any]
    searcher_cfg: Dict[str, Any]


@dataclass(frozen=True)
class GameResult:
    game_index: int
    opening_fen: str
    candidate_white: bool
    result: str
    candidate_points: float
    plies: int


DEFAULT_OPENINGS = [
    chess.STARTING_FEN,
    board_setup["white"]["open"],
    board_setup["black"]["open"],
    board_setup["white"]["mid"],
    board_setup["black"]["mid"],
]


def _build_runner_cfg(
    label: str,
    base: Dict[str, Any],
    overrides: Iterable[str],
) -> RunnerCfg:
    cfg = copy.deepcopy(base)
    for override in overrides:
        key, value = _parse_override(override)
        _set_nested(cfg, key, value)

    evaluator_cfg = cfg.get("EvaluatorConfig")
    searcher_cfg = cfg.get("SearcherConfig")
    if not isinstance(evaluator_cfg, dict) or not isinstance(searcher_cfg, dict):
        raise ValueError(
            "Config must contain EvaluatorConfig and SearcherConfig mappings"
        )

    return RunnerCfg(label, evaluator_cfg, searcher_cfg)


def _new_searcher(cfg: RunnerCfg):
    evaluator = EvaluatorFactory.create(EvaluatorConfig.from_dict(cfg.evaluator_cfg))
    return SearcherFactory.create(SearcherConfig.from_dict(cfg.searcher_cfg), evaluator)


def _play_single_game(
    game_index: int,
    opening_fen: str,
    candidate_white: bool,
    baseline_cfg: RunnerCfg,
    candidate_cfg: RunnerCfg,
    move_time_s: float,
    max_plies: int,
    out_pgn: Path | None,
) -> GameResult:
    board = BoardFactory.create(BoardPyChess)
    board.set_fen(opening_fen)

    white_searcher = _new_searcher(candidate_cfg if candidate_white else baseline_cfg)
    black_searcher = _new_searcher(baseline_cfg if candidate_white else candidate_cfg)

    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < max_plies:
        searcher = white_searcher if board.turn == chess.WHITE else black_searcher
        _, move = searcher.search(board, timeout=move_time_s)

        if move == chess.Move.null() or move not in board.legal_moves:
            move = next(iter(board.legal_moves), chess.Move.null())
            if move == chess.Move.null():
                break

        board.push(move)
        plies += 1

    if not board.is_game_over(claim_draw=True):
        result = "1/2-1/2"
    else:
        outcome = board.outcome(claim_draw=True)
        result = outcome.result() if outcome is not None else "1/2-1/2"

    candidate_points = {
        "1-0": 1.0 if candidate_white else 0.0,
        "0-1": 0.0 if candidate_white else 1.0,
        "1/2-1/2": 0.5,
    }[result]

    if out_pgn is not None:
        game = chess.pgn.Game.from_board(board)
        game.headers["Event"] = "Sporkfish Selfplay"
        game.headers["Round"] = str(game_index)
        game.headers["White"] = (
            candidate_cfg.label if candidate_white else baseline_cfg.label
        )
        game.headers["Black"] = (
            baseline_cfg.label if candidate_white else candidate_cfg.label
        )
        game.headers["Result"] = result
        game.headers["FEN"] = opening_fen
        game.headers["TimeControl"] = f"{move_time_s}/move"

        with out_pgn.open("a", encoding="utf-8") as fh:
            print(game, file=fh, end="\n\n")

    return GameResult(
        game_index=game_index,
        opening_fen=opening_fen,
        candidate_white=candidate_white,
        result=result,
        candidate_points=candidate_points,
        plies=plies,
    )


def run_match(
    base_config_path: Path,
    games: int,
    move_time_s: float,
    max_plies: int,
    baseline_overrides: List[str],
    candidate_overrides: List[str],
    out_dir: Path,
    seed: int,
    openings: List[str] | None,
    show_progress: bool = True,
) -> int:
    with base_config_path.open("r", encoding="utf-8") as fh:
        base_cfg: Dict[str, Any] = yaml.safe_load(fh)

    baseline_cfg = _build_runner_cfg("baseline", base_cfg, baseline_overrides)
    candidate_cfg = _build_runner_cfg("candidate", base_cfg, candidate_overrides)

    openings_to_use = openings or DEFAULT_OPENINGS
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "selfplay_summary.csv"
    out_pgn = out_dir / "selfplay_games.pgn"

    if out_csv.exists():
        out_csv.unlink()
    if out_pgn.exists():
        out_pgn.unlink()

    rng = random.Random(seed)
    results: List[GameResult] = []

    game_iter = range(games)
    if show_progress:
        game_iter = tqdm(game_iter, total=games, desc="Self-play", unit="game")

    for i in game_iter:
        opening_fen = openings_to_use[i % len(openings_to_use)]
        candidate_white = i % 2 == 0
        if i >= len(openings_to_use):
            opening_fen = rng.choice(openings_to_use)

        res = _play_single_game(
            game_index=i + 1,
            opening_fen=opening_fen,
            candidate_white=candidate_white,
            baseline_cfg=baseline_cfg,
            candidate_cfg=candidate_cfg,
            move_time_s=move_time_s,
            max_plies=max_plies,
            out_pgn=out_pgn,
        )
        results.append(res)

    wins = sum(1 for r in results if r.candidate_points == 1.0)
    draws = sum(1 for r in results if r.candidate_points == 0.5)
    losses = sum(1 for r in results if r.candidate_points == 0.0)
    total_points = wins + 0.5 * draws
    score = total_points / games if games else 0.0
    elo = _score_to_elo(score)

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "game",
                "candidate_white",
                "result",
                "candidate_points",
                "plies",
                "opening_fen",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.game_index,
                    r.candidate_white,
                    r.result,
                    r.candidate_points,
                    r.plies,
                    r.opening_fen,
                ]
            )

    print(
        f"games={games} wins={wins} draws={draws} losses={losses} "
        f"score={score:.3f} elo={elo:.1f}"
    )
    print(f"csv={out_csv}")
    print(f"pgn={out_pgn}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline vs candidate self-play")
    parser.add_argument("--config", default="config.yml", help="Base config YAML path")
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--move-time", type=float, default=0.15)
    parser.add_argument("--max-plies", type=int, default=160)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--baseline-override",
        action="append",
        default=[],
        help=(
            "Override for baseline in key=value form, e.g. "
            "SearcherConfig.move_order_config.killer_moves_weight=1.0"
        ),
    )
    parser.add_argument(
        "--candidate-override",
        action="append",
        default=[],
        help=(
            "Override for candidate in key=value form, e.g. "
            "SearcherConfig.move_order_config.killer_moves_weight=1.5"
        ),
    )
    parser.add_argument(
        "--opening-fen",
        action="append",
        default=None,
        help="Optional opening FEN. Can be specified multiple times.",
    )
    parser.add_argument("--out-dir", default="perf/selfplay")
    parser.add_argument(
        "--log-level",
        default="ERROR",
        help="Python logging level (DEBUG, INFO, WARNING, ERROR). Default: ERROR",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar output.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    logging.getLogger().setLevel(
        getattr(logging, str(args.log_level).upper(), logging.ERROR)
    )
    return run_match(
        base_config_path=Path(args.config),
        games=args.games,
        move_time_s=args.move_time,
        max_plies=args.max_plies,
        baseline_overrides=args.baseline_override,
        candidate_overrides=args.candidate_override,
        out_dir=Path(args.out_dir),
        seed=args.seed,
        openings=args.opening_fen,
        show_progress=not args.no_progress,
    )


if __name__ == "__main__":
    raise SystemExit(main())
