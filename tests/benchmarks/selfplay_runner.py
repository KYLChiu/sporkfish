import argparse
import copy
import csv
import datetime
import json
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
from scipy.special import betainc
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from init_board_helper import board_setup

from sporkfish.board.board_bitboard import BoardBitboard
from sporkfish.board.board_factory import BoardFactory
from sporkfish.board.board_py_chess import BoardPyChess
from sporkfish.evaluator.evaluator_config import EvaluatorConfig
from sporkfish.evaluator.evaluator_factory import EvaluatorFactory
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory


def _set_nested(d: Dict[str, Any], path: str, value: Any) -> None:
    """Set a value in a nested dictionary using dot-separated path notation.

    Useful for setting config values like "SearcherConfig.max_depth=7".

    Args:
        d: Dictionary to modify
        path: Dot-separated path, e.g., "SearcherConfig.move_order_config.weight"
        value: Value to set at the path

    Examples:
        _set_nested(cfg, "SearcherConfig.max_depth", 8)
        # cfg["SearcherConfig"]["max_depth"] = 8
    """
    keys = path.split(".")
    cur = d
    for key in keys[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[keys[-1]] = value


def _parse_override(entry: str) -> Tuple[str, Any]:
    """Parse a config override string in the format 'key=value'.

    Automatically parses the value as YAML to handle numbers, booleans, etc.

    Args:
        entry: String in format "key=value", e.g., "SearcherConfig.max_depth=7"

    Returns:
        Tuple of (key, parsed_value)

    Raises:
        ValueError: If entry is not in "key=value" format or key is empty
    """
    if "=" not in entry:
        raise ValueError(f"Override must be key=value, got: {entry}")
    key, raw = entry.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Override key cannot be empty: {entry}")
    return key, yaml.safe_load(raw)


def _score_to_elo(score: float) -> float:
    """Convert win rate (0.0 to 1.0) to Elo difference using the standard formula.

    The formula is: Elo = -400 * log10((1/score) - 1)
    This is the inverse of the standard Elo expectancy function.

    Args:
        score: Win rate as a fraction (e.g., 0.5 = 50% = 0 Elo, 0.55 approx +34 Elo)

    Returns:
        Elo difference. Returns ±inf for degenerate cases (score=0 or 1).

    Examples:
        score=0.5 -> Elo=0 (baseline performance)
        score=0.8 -> Elo approx +241 (candidate much stronger)
        score=0.2 -> Elo approx -241 (candidate much weaker)
    """
    if score <= 0.0:
        return float("-inf")
    if score >= 1.0:
        return float("inf")
    return -400.0 * math.log10((1.0 / score) - 1.0)


def _bayesian_los(wins: int, losses: int, draws: int) -> float:
    """Calculate Bayesian Likelihood of Superiority (LOS).

    LOS estimates the probability that the candidate is actually stronger than the baseline,
    given the observed game results. This uses a Beta distribution model where:
    - Prior: Both engines equally strong (Beta(1, 1) = Uniform)
    - Likelihood: Observed wins/losses are binomial outcomes
    - Posterior: Beta(wins + 1, losses + 1)

    The LOS is the probability that the true win rate > 50%, computed as:
    P(candidate stronger) = 1 - CDF_Beta(0.5 | wins+1, losses+1)

    Args:
        wins: Number of games candidate won (as candidate perspective)
        losses: Number of games candidate lost (as candidate perspective)
        draws: Number of draws (ignored in this calculation)

    Returns:
        Probability in [0, 1]. LOS > 0.95 (~95% confidence) is typically considered
        significant for accepting the candidate as an improvement.

    Examples:
        6 wins, 0 losses, 4 draws -> LOS approx 0.98 (98% likely to be stronger)
        5 wins, 5 losses, 0 draws -> LOS approx 0.50 (equally matched)
    """
    # Beta CDF at 0.5 with shape parameters (wins+1, losses+1)
    # betainc computes the regularized incomplete beta function
    # which is the CDF of the Beta distribution
    return 1.0 - betainc(wins + 1, losses + 1, 0.5)


def _wilson_ci_score(
    wins: int, losses: int, draws: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval for win rate.

    The Wilson interval is more accurate than the normal approximation, especially
    for small sample sizes or extreme scores. It properly handles edge cases.

    The interval is computed using:
        CI = (p + z^2/(2n) +/- z*sqrt(p(1-p)/n + z^2/(4n^2))) / (1 + z^2/n)

    where:
    - p = (wins + 0.5*draws) / n (empirical score)
    - z = critical value (1.96 for 95% confidence)
    - n = total number of games

    Args:
        wins: Number of games candidate won
        losses: Number of games candidate lost
        draws: Number of draws (counted as 0.5 for each side)
        confidence: Confidence level, typically 0.95 (95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) for the win rate in [0, 1]

    Examples:
        6W, 0L, 4D (n=10): CI approx (0.52, 0.96) for 95%
        The true win rate has 95% probability of being in this range
    """
    n = wins + losses + draws

    # Handle edge cases
    if n == 0:
        return 0.5, 0.5

    # Score treating draws as 0.5 points each
    p = (wins + 0.5 * draws) / n

    # Critical z-value for two-tailed confidence interval
    # 0.95 confidence -> 1.96; 0.90 confidence -> 1.645
    z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_map.get(confidence, 1.96)

    # Wilson score interval computation
    z_sq = z * z
    denominator = 1.0 + z_sq / n
    center = (p + z_sq / (2.0 * n)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / n + z_sq / (4.0 * n * n)) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return lower, upper


def _safe_uci(move: chess.Move) -> str:
    """Convert a chess move to UCI notation, or '0000' for null moves.

    Args:
        move: A chess.Move object

    Returns:
        String in UCI format (e.g., 'e2e4'), or '0000' for null/no move
    """
    return move.uci() if move != chess.Move.null() else "0000"


@dataclass(frozen=True)
class RunnerCfg:
    """Configuration for a chess engine in self-play.

    Attributes:
        label: Human-readable name (e.g., "baseline", "candidate")
        evaluator_cfg: Evaluator configuration dictionary
        searcher_cfg: Searcher configuration dictionary
    """

    label: str
    evaluator_cfg: Dict[str, Any]
    searcher_cfg: Dict[str, Any]


@dataclass(frozen=True)
class GameResult:
    """Result of a single game in self-play.

    Attributes:
        game_index: 1-based game number
        opening_fen: Starting position FEN
        candidate_white: Whether candidate played white (True) or black (False)
        result: PGN result string: "1-0", "0-1", or "1/2-1/2"
        candidate_points: Score from candidate's perspective: 1.0 (win), 0.5 (draw), 0.0 (loss)
        plies: Total half-moves played (ply 0 = starting position)
    """

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

_BOARD_TYPES = {
    "bitboard": BoardBitboard,
    "pychess": BoardPyChess,
}


def _resolve_board_type(board_type: str):
    key = board_type.strip().lower()
    if key not in _BOARD_TYPES:
        choices = ", ".join(sorted(_BOARD_TYPES.keys()))
        raise ValueError(f"Unsupported board type: {board_type}. Choices: {choices}")
    return _BOARD_TYPES[key]


def _build_runner_cfg(
    label: str,
    base: Dict[str, Any],
    overrides: Iterable[str],
) -> RunnerCfg:
    """Build a RunnerCfg by applying overrides to a base configuration.

    This creates a fresh copy of the base config and applies the overrides,
    allowing different engine variants to be compared without modifying the original.

    Args:
        label: Name for this configuration (e.g., "baseline")
        base: Base configuration dictionary (typically from YAML)
        overrides: Iterable of override strings, each in format "key.path=value"

    Returns:
        RunnerCfg with the evaluated config dictionaries

    Raises:
        ValueError: If EvaluatorConfig or SearcherConfig missing from base config
    """
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
    """Create a new searcher instance from a RunnerCfg.

    Instantiates both the evaluator and searcher based on the configuration,
    wiring them together for a complete search engine.

    Args:
        cfg: RunnerCfg with evaluator and searcher configurations

    Returns:
        Configured searcher ready to analyze positions
    """
    evaluator = EvaluatorFactory.create(EvaluatorConfig.from_dict(cfg.evaluator_cfg))
    return SearcherFactory.create(SearcherConfig.from_dict(cfg.searcher_cfg), evaluator)


def _play_single_game(
    game_index: int,
    opening_fen: str,
    candidate_white: bool,
    baseline_cfg: RunnerCfg,
    candidate_cfg: RunnerCfg,
    board_cls,
    move_time_s: float,
    max_plies: int,
    out_pgn: Path | None,
) -> GameResult:
    """Play a single game between baseline and candidate engines.

    The engines alternate making moves under time control until the game ends
    (checkmate, stalemate, 3-fold repetition, 50-move rule, or max plies reached).
    Results are recorded from the candidate's perspective.

    Args:
        game_index: 1-based game number for identification
        opening_fen: Starting position in FEN notation
        candidate_white: Whether candidate plays white (True) or black (False)
        baseline_cfg: Configuration for baseline engine
        candidate_cfg: Configuration for candidate engine
        move_time_s: Time budget per move in seconds
        max_plies: Maximum half-moves before draw (prevents infinite games)
        out_pgn: Optional path to append PGN output. If None, PGN is not saved.

    Returns:
        GameResult with final position and outcome
    """
    board = BoardFactory.create(board_cls)
    board.set_fen(opening_fen)

    # Determine which searcher plays which color
    white_searcher = _new_searcher(candidate_cfg if candidate_white else baseline_cfg)
    black_searcher = _new_searcher(baseline_cfg if candidate_white else candidate_cfg)

    # Play moves until game is over or max plies reached
    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < max_plies:
        # Select searcher based on whose turn it is
        searcher = white_searcher if board.turn == chess.WHITE else black_searcher
        _, move = searcher.search(board, timeout=move_time_s)

        # Fallback to first legal move if search returned null move (timeout or error)
        if move == chess.Move.null() or move not in board.legal_moves:
            move = next(iter(board.legal_moves), chess.Move.null())
            if move == chess.Move.null():
                # No legal moves and not checkmate/stalemate - shouldn't happen
                break

        board.push(move)
        plies += 1

    # Determine final result
    if not board.is_game_over(claim_draw=True):
        result = "1/2-1/2"
    else:
        outcome = board.outcome(claim_draw=True)
        result = outcome.result() if outcome is not None else "1/2-1/2"

    # Convert result to candidate's score (1.0 = win, 0.5 = draw, 0.0 = loss)
    candidate_points = {
        "1-0": 1.0 if candidate_white else 0.0,
        "0-1": 0.0 if candidate_white else 1.0,
        "1/2-1/2": 0.5,
    }[result]

    # Save PGN if requested
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
    runner_overrides: List[str] | None = None,
    enforce_gate: bool = False,
    min_los: float = 0.95,
    min_elo_ci_lower: float = 0.0,
    run_id: str | None = None,
    show_progress: bool = True,
) -> int:
    """Run a complete self-play match and estimate Elo difference.

    This orchestrates the entire evaluation:
    1. Loads base configuration from YAML
    2. Applies baseline and candidate overrides
    3. Plays requested number of games with alternating colors
    4. Calculates empirical score, Elo estimate, and Bayesian statistics
    5. Writes results to CSV and PGN files

    The Bayesian analysis includes:
    - LOS (Likelihood of Superiority): Probability candidate is stronger
    - Wilson CI: 95% confidence interval on the true win rate and Elo difference

    Args:
        base_config_path: Path to base config YAML file
        games: Number of games to play
        move_time_s: Time per move in seconds
        max_plies: Maximum half-moves per game
        baseline_overrides: Configuration overrides for baseline (e.g., ["SearcherConfig.max_depth=7"])
        candidate_overrides: Configuration overrides for candidate
        out_dir: Output directory for CSV and PGN files
        seed: Random seed for reproducible opening selection
        openings: List of opening FENs. If None, uses 5 default positions
        show_progress: Whether to display progress bar

    Returns:
        Exit code (0 = success)
    """
    with base_config_path.open("r", encoding="utf-8") as fh:
        base_cfg: Dict[str, Any] = yaml.safe_load(fh)

    # Generic runner-level overrides (applies to match harness settings such as
    # board backend, unlike baseline/candidate overrides which target engine cfgs).
    for override in runner_overrides or []:
        key, value = _parse_override(override)
        _set_nested(base_cfg, key, value)

    board_cfg = base_cfg.get("BoardConfig", {})
    if not isinstance(board_cfg, dict):
        board_cfg = {}

    board_type = str(
        base_cfg.get("board_type", board_cfg.get("board_type", "bitboard"))
    )

    baseline_cfg = _build_runner_cfg("baseline", base_cfg, baseline_overrides)
    candidate_cfg = _build_runner_cfg("candidate", base_cfg, candidate_overrides)
    board_cls = _resolve_board_type(board_type)

    openings_to_use = openings or DEFAULT_OPENINGS
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "selfplay_summary.csv"
    out_pgn = out_dir / "selfplay_games.pgn"
    out_json = out_dir / "selfplay_metrics.json"

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
        # Use default openings cyclically, then random selection
        opening_fen = openings_to_use[i % len(openings_to_use)]
        candidate_white = i % 2 == 0  # Alternate colors
        if i >= len(openings_to_use):
            opening_fen = rng.choice(openings_to_use)

        res = _play_single_game(
            game_index=i + 1,
            opening_fen=opening_fen,
            candidate_white=candidate_white,
            baseline_cfg=baseline_cfg,
            candidate_cfg=candidate_cfg,
            board_cls=board_cls,
            move_time_s=move_time_s,
            max_plies=max_plies,
            out_pgn=out_pgn,
        )
        results.append(res)

    # Count game outcomes for the candidate engine
    wins = sum(1 for r in results if r.candidate_points == 1.0)
    draws = sum(1 for r in results if r.candidate_points == 0.5)
    losses = sum(1 for r in results if r.candidate_points == 0.0)

    # Calculate empirical score: (wins + 0.5*draws) / total_games
    # This represents the fraction of points scored by the candidate
    total_points = wins + 0.5 * draws
    score = total_points / games if games else 0.0

    # Convert score to Elo difference using standard formula
    elo = _score_to_elo(score)

    # Calculate Bayesian statistics for significance testing
    # LOS: Likelihood of Superiority - probability candidate is actually stronger
    los = _bayesian_los(wins, losses, draws)

    # Wilson confidence interval for the true win rate
    # E.g., if CI is [0.52, 0.96], the true win rate has 95% probability of being in that range
    ci_lower_score, ci_upper_score = _wilson_ci_score(
        wins, losses, draws, confidence=0.95
    )

    # Convert score confidence bounds to Elo confidence bounds
    # Handle edge cases to avoid log(0) or log(inf)
    if ci_lower_score > 0.0 and ci_lower_score < 1.0:
        elo_ci_lower = _score_to_elo(ci_lower_score)
    else:
        elo_ci_lower = -400.0 if ci_lower_score <= 0.0 else 400.0

    if ci_upper_score > 0.0 and ci_upper_score < 1.0:
        elo_ci_upper = _score_to_elo(ci_upper_score)
    else:
        elo_ci_upper = 400.0 if ci_upper_score >= 1.0 else -400.0

    # Write game results to CSV for analysis
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

    # Print detailed match statistics
    print()
    print("=" * 80)
    print("MATCH RESULTS")
    print("=" * 80)
    print(f"Games:        {games}")
    print(f"Candidate:    {wins}W {draws}D {losses}L")
    print(f"Score:        {score:.1%}")
    print(f"Elo Estimate: {elo:+.1f}")
    print()
    print("95% CONFIDENCE INTERVALS (Wilson)")
    print(f"Score CI:     [{ci_lower_score:.1%}, {ci_upper_score:.1%}]")
    print(f"Elo CI:       [{elo_ci_lower:+.1f}, {elo_ci_upper:+.1f}]")
    print()
    print("BAYESIAN STATISTICS")
    print(f"LOS:          {los:.1%}")
    if los > 0.95:
        print("              ✓ Significant improvement (p < 0.05)")
    elif los > 0.90:
        print("              ≈ Suggestive of improvement (p < 0.10)")
    else:
        print("              ✗ Not significant at p < 0.05 threshold")
    print()
    print("OUTPUT FILES")
    print(f"Board Type:   {board_type.lower()}")
    print(f"CSV:          {out_csv}")
    print(f"PGN:          {out_pgn}")

    gate_passed = bool(los >= min_los and elo_ci_lower >= min_elo_ci_lower)
    decision = "pass" if gate_passed else "fail"
    created_at_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    effective_run_id = run_id or created_at_utc.strftime("%Y%m%dT%H%M%SZ")
    if enforce_gate:
        print()
        print("QUALITY GATE")
        print(f"Enabled:      yes")
        print(
            f"Thresholds:   LOS >= {min_los:.1%}, Elo CI lower >= {min_elo_ci_lower:+.1f}"
        )
        print(f"Status:       {'PASS' if gate_passed else 'FAIL'}")
    else:
        print()
        print("QUALITY GATE")
        print("Enabled:      no")
        print(f"Would pass:   {'yes' if gate_passed else 'no'}")

    summary_payload = {
        "decision": decision,
        "games": int(games),
        "wins": int(wins),
        "draws": int(draws),
        "losses": int(losses),
        "score": float(score),
        "elo": float(elo),
        "score_ci_lower": float(ci_lower_score),
        "score_ci_upper": float(ci_upper_score),
        "elo_ci_lower": float(elo_ci_lower),
        "elo_ci_upper": float(elo_ci_upper),
        "los": float(los),
        "board_type": board_type.lower(),
        "thresholds": {
            "enforce_gate": bool(enforce_gate),
            "min_los": float(min_los),
            "min_elo_ci_lower": float(min_elo_ci_lower),
            "gate_passed": bool(gate_passed),
        },
        "run": {
            "run_id": str(effective_run_id),
            "created_at_utc": created_at_utc.isoformat().replace("+00:00", "Z"),
            "config_path": str(base_config_path),
            "seed": int(seed),
            "games": int(games),
            "move_time_s": float(move_time_s),
            "max_plies": int(max_plies),
            "opening_count": int(len(openings_to_use)),
            "baseline_overrides": list(baseline_overrides),
            "candidate_overrides": list(candidate_overrides),
            "runner_overrides": list(runner_overrides or []),
        },
        "paths": {
            "csv": str(out_csv),
            "pgn": str(out_pgn),
        },
    }
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"JSON:         {out_json}")
    print(f"Run ID:       {effective_run_id}")
    print("=" * 80)
    print()
    return 1 if enforce_gate and not gate_passed else 0


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the selfplay runner.

    Returns:
        Parsed arguments including game count, time controls, configuration overrides,
        output directory, and logging settings.
    """
    parser = argparse.ArgumentParser(
        description="Run baseline vs candidate self-play with Elo estimation and Bayesian analysis",
        epilog="""
Examples:
  # 40 games comparing two move orderings
  %(prog)s --games 40 --move-time 0.15 \\
    --baseline-override "SearcherConfig.move_order_config.killer_moves_weight=1.0" \\
    --candidate-override "SearcherConfig.move_order_config.killer_moves_weight=1.5"

  # Quick 10-game smoke test with reduced time
  %(prog)s --games 10 --move-time 0.05 --out-dir perf/smoke_test
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Base config YAML path (default: config.yml)",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=40,
        help="Number of games to play (default: 40). Larger numbers give more accurate Elo estimates.",
    )
    parser.add_argument(
        "--move-time",
        type=float,
        default=0.15,
        help="Time per move in seconds (default: 0.15). Shorter for quick tests, longer for accuracy.",
    )
    parser.add_argument(
        "--max-plies",
        type=int,
        default=160,
        help="Maximum plies per game before draw (default: 160, approximately 80 moves)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for reproducible opening selection (default: 7)",
    )
    parser.add_argument(
        "--baseline-override",
        action="append",
        default=[],
        help=(
            "Override for baseline config in key=value form. Repeat to set multiple values. "
            "Example: SearcherConfig.move_order_config.killer_moves_weight=1.0"
        ),
    )
    parser.add_argument(
        "--candidate-override",
        action="append",
        default=[],
        help=(
            "Override for candidate config in key=value form. Repeat to set multiple values. "
            "Example: SearcherConfig.move_order_config.killer_moves_weight=1.5"
        ),
    )
    parser.add_argument(
        "--opening-fen",
        action="append",
        default=None,
        help=(
            "Specify custom opening positions by FEN. Repeat to use multiple openings. "
            "If omitted, uses default 5 opening positions."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="perf/selfplay",
        help="Output directory for CSV and PGN results (default: perf/selfplay)",
    )
    parser.add_argument(
        "--runner-override",
        action="append",
        default=[],
        help=(
            "Generic match-harness override in key=value form (repeatable). "
            "Examples: board_type=pychess or BoardConfig.board_type=bitboard"
        ),
    )
    parser.add_argument(
        "--enforce-gate",
        action="store_true",
        help=(
            "Fail with nonzero exit code if quality gate is not met. "
            "Gate conditions: LOS >= --min-los and Elo CI lower bound >= --min-elo-ci-lower."
        ),
    )
    parser.add_argument(
        "--min-los",
        type=float,
        default=0.95,
        help="Minimum LOS threshold for gate pass (default: 0.95).",
    )
    parser.add_argument(
        "--min-elo-ci-lower",
        type=float,
        default=0.0,
        help="Minimum lower bound of Elo CI for gate pass (default: 0.0).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help=(
            "Optional run identifier for JSON artifact correlation across CI/PR runs. "
            "If omitted, defaults to UTC timestamp like 20260419T123456Z."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="ERROR",
        help="Python logging level: DEBUG, INFO, WARNING, ERROR (default: ERROR)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar during game playing.",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the selfplay runner.

    Parses command-line arguments and runs the match with appropriate logging level.

    Returns:
        Exit code (0 = success)
    """
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
        runner_overrides=args.runner_override,
        enforce_gate=args.enforce_gate,
        min_los=args.min_los,
        min_elo_ci_lower=args.min_elo_ci_lower,
        run_id=args.run_id,
        show_progress=not args.no_progress,
    )


if __name__ == "__main__":
    raise SystemExit(main())
