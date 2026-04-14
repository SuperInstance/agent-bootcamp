#!/usr/bin/env python3
"""CLI interface for Agent Bootcamp.

Subcommands:
  enroll   <agent_name>  — Register a new agent for training
  start                  — Begin training session
  challenge              — Show/accept current challenge
  submit                 — Submit a solution
  progress               — Show training progress
  report                 — Generate full training report
  dojo                   — Enter dojo sparring mode
  rank                   — Show agent rankings
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bootcamp import Bootcamp, Rankings


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

_STATE_DIR = Path.home() / ".agent-bootcamp"


def _state_path(agent_name: str) -> Path:
    return _STATE_DIR / f"{agent_name}.json"


def _save_state(bc: Bootcamp) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    bc.export_report(str(_state_path(bc.agent_name)))


def _load_state(agent_name: str) -> Bootcamp | None:
    path = _state_path(agent_name)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    bc = Bootcamp(agent_name, data.get("project_path"))
    # Restore skills
    from skills import SkillsTracker
    bc.skills = SkillsTracker.from_dict(data.get("skills", {}))
    # Restore curriculum
    from curriculum import Curriculum
    cur_data = data.get("curriculum", {})
    bc.curriculum.day = cur_data.get("day", 1)
    bc.curriculum.rotation = cur_data.get("rotation", 0)
    bc.curriculum._challenges_generated = cur_data.get("challenges_generated", 0)
    # Restore session
    bc._challenges_done = data.get("session", {}).get("challenges_done", 0)
    return bc


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_enroll(args: argparse.Namespace) -> int:
    """Register a new agent."""
    agent_name = args.agent_name
    path = _state_path(agent_name)
    if path.exists():
        print(f"Agent '{agent_name}' is already enrolled.")
        return 1

    bc = Bootcamp(agent_name, args.project_path)
    _save_state(bc)
    print(f"Enrolled agent '{agent_name}' for training.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Begin training session."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    bc.start_training()
    challenge = bc.current_challenge
    if challenge:
        print(f"Training started for '{args.agent_name}'")
        print(f"Day {bc.curriculum.day}, Rotation {bc.curriculum.rotation + 1}")
        print(f"\nCurrent challenge [{challenge.id}]:")
        print(f"  Topic:     {challenge.topic.value}")
        print(f"  Difficulty: {challenge.difficulty} ({challenge.difficulty_label})")
        print(f"  Time limit: {challenge.time_limit_minutes} min")
        print(f"  Blind:      {'yes' if challenge.is_blind else 'no'}")
        print(f"\n  {challenge.description}")
        if challenge.acceptance_criteria:
            print(f"\n  Acceptance criteria:")
            for c in challenge.acceptance_criteria:
                print(f"    - {c}")
    _save_state(bc)
    return 0


def cmd_challenge(args: argparse.Namespace) -> int:
    """Show/accept current challenge."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    if bc.current_challenge is None:
        try:
            challenge = bc.next_challenge()
            _save_state(bc)
        except RuntimeError as e:
            print(f"Error: {e}")
            return 1
    else:
        challenge = bc.current_challenge

    print(f"Challenge [{challenge.id}]:")
    print(f"  Topic:      {challenge.topic.value}")
    print(f"  Difficulty: {challenge.difficulty} ({challenge.difficulty_label})")
    print(f"  Time limit: {challenge.time_limit_minutes} min")
    print(f"  Blind:      {'yes' if challenge.is_blind else 'no'}")
    print(f"\n  {challenge.description}")
    if challenge.acceptance_criteria:
        print(f"\n  Acceptance criteria:")
        for c in challenge.acceptance_criteria:
            print(f"    - {c}")
    if challenge.hints:
        print(f"\n  Hints:")
        for h in challenge.hints:
            print(f"    - {h}")

    print(f"\n  Submit with: cli.py submit {args.agent_name} {challenge.id} <solution_file>")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    """Submit a solution."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    challenge_id = args.challenge_id
    if args.solution_file:
        try:
            with open(args.solution_file) as f:
                solution = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.solution_file}")
            return 1
    elif args.solution_text:
        solution = args.solution_text
    else:
        print("Provide --solution-file or --solution-text")
        return 1

    try:
        grade = bc.submit_solution(challenge_id, solution)
        _save_state(bc)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    print(f"Grade: {grade.letter} ({grade.score:.1%})")
    print(f"Passed: {'yes' if grade.passed else 'no'}")
    print(f"Feedback: {grade.feedback}")
    if grade.criteria_met:
        print(f"Criteria met: {', '.join(grade.criteria_met)}")
    if grade.criteria_missed:
        print(f"Criteria missed: {', '.join(grade.criteria_missed)}")

    # Auto-advance to next challenge
    try:
        next_ch = bc.next_challenge()
        _save_state(bc)
        print(f"\nNext challenge [{next_ch.id}]: {next_ch.description[:80]}...")
    except RuntimeError:
        print("\nSession complete (max challenges reached).")

    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    """Show training progress."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    report = bc.progress_report()
    print(f"Agent: {report['agent']}")
    print(f"Day: {report['day']}, Rotation: {report['rotation']}")
    print(f"Challenges done: {report['challenges_done']}")
    print(f"Overall proficiency: {report['overall_proficiency']:.1%}")
    print(f"Dojo win rate: {report['dojo_win_rate']:.1%}")

    profs = bc.skills.all_proficiencies()
    print(f"\nSkill proficiencies:")
    for topic, prof in sorted(profs.items(), key=lambda x: x[1], reverse=True):
        bar_len = int(prof * 20)
        bar = "#" * bar_len + "-" * (20 - bar_len)
        print(f"  {topic.value:20s} [{bar}] {prof:.1%}")

    weaknesses = report["weaknesses"]
    if weaknesses:
        print(f"\nWeaknesses:")
        for w in weaknesses:
            print(f"  - {w['topic']}: {w['level']:.1%}")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate full training report."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    if args.output:
        bc.export_report(args.output)
        print(f"Report saved to: {args.output}")
    else:
        report = json.dumps(
            bc.progress_report(), indent=2, default=str
        )
        print(report)
    return 0


def cmd_dojo(args: argparse.Namespace) -> int:
    """Enter dojo sparring mode."""
    bc = _load_state(args.agent_name)
    if bc is None:
        print(f"Agent '{args.agent_name}' not found. Run 'enroll' first.")
        return 1

    solution = ""
    if args.solution_file:
        try:
            with open(args.solution_file) as f:
                solution = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.solution_file}")
            return 1
    elif args.solution_text:
        solution = args.solution_text
    else:
        solution = "# Sample solution\ndef solve():\n    return True"

    # Generate a dojo challenge
    from skills import Topic
    challenge = bc.curriculum.generate_challenge(topic=Topic.DOJO)

    print(f"Dojo sparring for '{args.agent_name}'")
    print(f"Challenge [{challenge.id}]: {challenge.description[:80]}...")
    print(f"\nRunning sparring rounds...")

    results = bc.dojo.run_round(challenge, solution)
    _save_state(bc)

    for r in results:
        icon = {"win": "+", "loss": "-", "draw": "="}.get(r.outcome, "?")
        print(
            f"  [{icon}] vs {r.twin.name}: "
            f"agent={r.agent_score:.2f} twin={r.twin_score:.2f}"
        )

    summary = bc.dojo.summary()
    print(f"\nDojo summary:")
    print(f"  Record: {summary['record']}")
    print(f"  Win rate: {summary['win_rate']:.1%}")
    style = summary.get("style_analysis", {})
    print(f"  Style: {style.get('assessment', 'N/A')}")

    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    """Show agent rankings."""
    rankings = Rankings()

    if not _STATE_DIR.exists():
        print("No agents enrolled yet.")
        return 0

    for state_file in _STATE_DIR.glob("*.json"):
        agent_name = state_file.stem
        bc = _load_state(agent_name)
        if bc is not None:
            rankings.register(bc)

    board = rankings.leaderboard()
    if not board:
        print("No agents found.")
        return 0

    print("Leaderboard:")
    print(f"  {'Rank':<6}{'Agent':<30}{'Proficiency':<15}{'Challenges':<12}{'Dojo WR'}")
    print(f"  {'-'*6}{'-'*30}{'-'*15}{'-'*12}{'-'*10}")
    for i, entry in enumerate(board, 1):
        print(
            f"  {i:<6}{entry['name']:<30}"
            f"{entry['overall_proficiency']:<15.1%}"
            f"{entry['challenges_done']:<12}"
            f"{entry['dojo_win_rate']:.1%}"
        )
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-bootcamp",
        description="Spiral training system for git-agents",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # enroll
    p_enroll = sub.add_parser("enroll", help="Register a new agent")
    p_enroll.add_argument("agent_name", help="Name of the agent")
    p_enroll.add_argument("--project-path", default=None, help="Path to project")

    # start
    p_start = sub.add_parser("start", help="Begin training session")
    p_start.add_argument("agent_name", help="Name of the agent")

    # challenge
    p_ch = sub.add_parser("challenge", help="Show/accept current challenge")
    p_ch.add_argument("agent_name", help="Name of the agent")

    # submit
    p_sub = sub.add_parser("submit", help="Submit a solution")
    p_sub.add_argument("agent_name", help="Name of the agent")
    p_sub.add_argument("challenge_id", help="Challenge ID")
    p_sub.add_argument("--solution-file", default=None, help="Path to solution file")
    p_sub.add_argument("--solution-text", default=None, help="Solution text")

    # progress
    p_prog = sub.add_parser("progress", help="Show training progress")
    p_prog.add_argument("agent_name", help="Name of the agent")

    # report
    p_rep = sub.add_parser("report", help="Generate training report")
    p_rep.add_argument("agent_name", help="Name of the agent")
    p_rep.add_argument("--output", "-o", default=None, help="Output file path")

    # dojo
    p_dojo = sub.add_parser("dojo", help="Enter dojo sparring mode")
    p_dojo.add_argument("agent_name", help="Name of the agent")
    p_dojo.add_argument("--solution-file", default=None, help="Path to solution file")
    p_dojo.add_argument("--solution-text", default=None, help="Solution text")

    # rank
    p_rank = sub.add_parser("rank", help="Show agent rankings")
    p_rank.add_argument("agent_name", nargs="?", default=None, help="Optional: specific agent")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "enroll": cmd_enroll,
        "start": cmd_start,
        "challenge": cmd_challenge,
        "submit": cmd_submit,
        "progress": cmd_progress,
        "report": cmd_report,
        "dojo": cmd_dojo,
        "rank": cmd_rank,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
