"""Dojo sparring system.

Generates shadow challenges where the agent faces variants of its
own solutions, tracks win/loss/draw, and analyses coding style.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from curriculum import Challenge
from skills import Topic


# ---------------------------------------------------------------------------
# Twin / Variant definitions
# ---------------------------------------------------------------------------

class TwinDifficulty(Enum):
    EASY = "easy"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


@dataclass
class TwinVariant:
    """A variant of a solution for sparring.

    Twin variants are generated from the agent's own solution using
    deterministic transformations. Each variant has a difficulty
    type (EASY, HARD, ADVERSARIAL) and a unique name.
    """

    name: str
    twin_type: TwinDifficulty
    solution: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SparringResult:
    """Result of a single sparring round."""

    challenge_id: str
    agent_solution: str
    twin: TwinVariant
    outcome: str  # "win", "loss", "draw"
    agent_score: float
    twin_score: float
    notes: str = ""
    style_diff: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Style analysis
# ---------------------------------------------------------------------------

@dataclass
class StyleMetrics:
    """Quantified style characteristics of a solution."""

    line_count: int = 0
    avg_line_length: float = 0.0
    function_count: int = 0
    comment_ratio: float = 0.0
    max_nesting_depth: int = 0
    unique_words: int = 0
    approaches_used: list[str] = field(default_factory=list)

    def distance(self, other: StyleMetrics) -> float:
        """Euclidean-style distance between two style vectors."""
        d = 0.0
        d += abs(self.line_count - other.line_count) / max(self.line_count + other.line_count, 1)
        d += abs(self.avg_line_length - other.avg_line_length) / max(self.avg_line_length + other.avg_line_length, 1)
        d += abs(self.function_count - other.function_count) / max(self.function_count + other.function_count, 1)
        d += abs(self.comment_ratio - other.comment_ratio)
        d += abs(self.max_nesting_depth - other.max_nesting_depth) / 10
        return round(d, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_count": self.line_count,
            "avg_line_length": self.avg_line_length,
            "function_count": self.function_count,
            "comment_ratio": self.comment_ratio,
            "max_nesting_depth": self.max_nesting_depth,
            "unique_words": self.unique_words,
            "approaches_used": self.approaches_used,
        }


def analyse_style(solution: str) -> StyleMetrics:
    """Extract style metrics from a code solution string."""
    lines = solution.splitlines()
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    comment_lines = [l for l in lines if l.strip().startswith("#")]

    metrics = StyleMetrics()
    metrics.line_count = len(lines)
    metrics.avg_line_length = (
        sum(len(l) for l in lines) / len(lines) if lines else 0.0
    )
    metrics.comment_ratio = (
        len(comment_lines) / len(lines) if lines else 0.0
    )

    # Count function definitions (rough heuristic)
    metrics.function_count = sum(
        1 for l in code_lines if "def " in l or "fn " in l or "func " in l
    )

    # Max nesting depth
    depth = 0
    max_depth = 0
    for line in code_lines:
        stripped = line.strip()
        if stripped.endswith(":") or stripped.endswith("{"):
            depth += 1
            max_depth = max(max_depth, depth)
        indent_change = (len(line) - len(line.lstrip()))
        # rough: every 4 spaces = one level (reset on dedent)
    metrics.max_nesting_depth = max_depth

    # Unique words
    words = set()
    for line in code_lines:
        words.update(line.split())
    metrics.unique_words = len(words)

    # Detect approaches
    approaches: list[str] = []
    sol_lower = solution.lower()
    if "regex" in sol_lower or "re." in sol_lower:
        approaches.append("regex")
    if "class " in sol_lower:
        approaches.append("OOP")
    if "list comprehension" in sol_lower or "[x for" in sol_lower:
        approaches.append("comprehension")
    if "lambda" in sol_lower:
        approaches.append("lambda")
    if "async " in sol_lower:
        approaches.append("async")
    if "try:" in sol_lower or "except" in sol_lower:
        approaches.append("exception_handling")
    if "with " in sol_lower:
        approaches.append("context_manager")
    if not approaches:
        approaches.append("procedural")
    metrics.approaches_used = approaches

    return metrics


# ---------------------------------------------------------------------------
# Shadow challenge generation
# ---------------------------------------------------------------------------

def generate_shadow_challenge(
    original_challenge: Challenge,
    twin_type: TwinDifficulty = TwinDifficulty.EASY,
) -> Challenge:
    """Create a variant of a challenge for sparring.

    Easy twin: same topic, difficulty - 2.
    Hard twin: same topic, difficulty + 2.
    Adversarial: swapped constraints, misleading description prefix.
    """
    diff = original_challenge.difficulty
    if twin_type == TwinDifficulty.EASY:
        new_diff = max(1, diff - 2)
        desc_prefix = "Simplified version: "
    elif twin_type == TwinDifficulty.HARD:
        new_diff = min(10, diff + 2)
        desc_prefix = "Harder variant: "
    else:  # adversarial
        new_diff = diff
        desc_prefix = "Note: the obvious approach has a hidden trap. "

    return Challenge(
        topic=original_challenge.topic,
        difficulty=new_diff,
        rotation=original_challenge.rotation,
        description=desc_prefix + original_challenge.description,
        acceptance_criteria=list(original_challenge.acceptance_criteria),
        time_limit_minutes=original_challenge.time_limit_minutes,
        is_blind=False,
        metadata={
            "shadow_of": original_challenge.id,
            "twin_type": twin_type.value,
        },
    )


def generate_twin_solution(
    challenge: Challenge,
    agent_solution: str,
    twin_type: TwinDifficulty,
) -> TwinVariant:
    """Generate a twin variant of the agent's solution.

    In a real system this would call an LLM. Here we simulate
    by producing deterministic variations of the solution text.
    """
    # Deterministic but varied transformation based on type
    rng = random.Random(hash(challenge.id + twin_type.value + agent_solution[:50]))
    name_suffix = twin_type.value[:4].upper()
    twin_name = f"Twin-{name_suffix}-{challenge.id[:4]}"

    if twin_type == TwinDifficulty.EASY:
        # Shorten, simplify
        lines = agent_solution.splitlines()
        modified = "\n".join(lines[: max(3, len(lines) // 2)])
        solution = f"# Simplified approach\n{modified}"
    elif twin_type == TwinDifficulty.HARD:
        # Add complexity
        lines = agent_solution.splitlines()
        extra = "\n".join(f"# Additional edge case {i}" for i in range(rng.randint(3, 8)))
        solution = f"# Extended solution\n{agent_solution}\n{extra}"
    else:
        # Adversarial: swap some variable names, add misleading comments
        words_to_swap = ["result", "data", "output", "value", "item"]
        modified = agent_solution
        for word in words_to_swap:
            if word in modified:
                replacement = word + "_alt"
                modified = modified.replace(word, replacement, 1)
        solution = f"# Alternative approach\n{modified}"

    return TwinVariant(
        name=twin_name,
        twin_type=twin_type,
        solution=solution,
        metadata={"challenge_id": challenge.id},
    )


# ---------------------------------------------------------------------------
# Dojo (main sparring system)
# ---------------------------------------------------------------------------

class Dojo:
    """Manages sparring sessions between an agent and twin variants."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.results: list[SparringResult] = []
        self.twin_types = list(TwinDifficulty)

    def run_round(
        self,
        challenge: Challenge,
        agent_solution: str,
    ) -> list[SparringResult]:
        """Run a sparring round: agent vs all twin types."""
        round_results: list[SparringResult] = []

        for twin_type in self.twin_types:
            shadow = generate_shadow_challenge(challenge, twin_type)
            twin = generate_twin_solution(shadow, agent_solution, twin_type)

            # Score both solutions (simulated grading)
            agent_score = self._score_solution(agent_solution, challenge)
            twin_score = self._score_solution(twin.solution, shadow)

            if agent_score > twin_score + 0.05:
                outcome = "win"
            elif twin_score > agent_score + 0.05:
                outcome = "loss"
            else:
                outcome = "draw"

            # Style analysis
            agent_style = analyse_style(agent_solution)
            twin_style = analyse_style(twin.solution)
            style_diff = {
                "approach_difference": list(
                    set(agent_style.approaches_used) ^ set(twin_style.approaches_used)
                ),
                "style_distance": agent_style.distance(twin_style),
            }

            result = SparringResult(
                challenge_id=challenge.id,
                agent_solution=agent_solution,
                twin=twin,
                outcome=outcome,
                agent_score=agent_score,
                twin_score=twin_score,
                notes=f"Agent vs {twin.name}: {outcome}",
                style_diff=style_diff,
            )
            round_results.append(result)

        self.results.extend(round_results)
        return round_results

    def run_tournament(
        self,
        challenges: list[Challenge],
        solutions: dict[str, str],  # challenge_id -> solution
    ) -> list[SparringResult]:
        """Run a round-robin tournament over multiple challenges."""
        all_results: list[SparringResult] = []
        for challenge in challenges:
            sol = solutions.get(challenge.id, "")
            if sol:
                all_results.extend(self.run_round(challenge, sol))
        return all_results

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def win_rate(self) -> float:
        if not self.results:
            return 0.0
        wins = sum(1 for r in self.results if r.outcome == "win")
        return round(wins / len(self.results), 4)

    def record_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {"win": 0, "loss": 0, "draw": 0}
        for r in self.results:
            summary[r.outcome] = summary.get(r.outcome, 0) + 1
        return summary

    def style_analysis(self) -> dict[str, Any]:
        """Analyse whether the agent tends to use the same approach."""
        if not self.results:
            return {"status": "no_data"}

        approaches_seen: list[list[str]] = []
        for r in self.results:
            style = analyse_style(r.agent_solution)
            approaches_seen.append(sorted(style.approaches_used))

        # Count unique approach sets
        unique_sets = len(set(tuple(a) for a in approaches_seen))
        total = len(approaches_seen)

        return {
            "total_rounds": total,
            "unique_approach_combos": unique_sets,
            "approach_diversity": round(unique_sets / max(total, 1), 4),
            "assessment": (
                "highly_diverse" if unique_sets / max(total, 1) > 0.7
                else "somewhat_diverse" if unique_sets > 1
                else "monoculture"
            ),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "total_rounds": len(self.results),
            "record": self.record_summary(),
            "win_rate": self.win_rate(),
            "style_analysis": self.style_analysis(),
        }

    # ------------------------------------------------------------------
    # Internal scoring (simulated)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_solution(solution: str, challenge: Challenge) -> float:
        """Simulated scoring of a solution.

        In a real system this would run tests, lint, etc.
        Here we use heuristics on the solution text.
        """
        if not solution.strip():
            return 0.0

        score = 0.5  # base

        # Longer solutions that aren't just comments are generally better
        code_chars = len(solution) - sum(1 for c in solution if c == '#')
        score += min(code_chars / 500, 0.2)

        # Has function definitions
        if "def " in solution or "fn " in solution or "func " in solution:
            score += 0.1

        # Has error handling
        if "try:" in solution or "except" in solution or "error" in solution.lower():
            score += 0.1

        # Has tests
        if "test" in solution.lower():
            score += 0.1

        # Difficulty bonus (harder challenges get less penalty for shorter solutions)
        score += challenge.difficulty * 0.01

        return round(min(score, 1.0), 4)
