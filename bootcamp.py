#!/usr/bin/env python3
"""Agent Bootcamp Engine — Spiral training for git-agents.

Manages training progress, generates challenges adapted to weaknesses,
tracks skill metrics over time, and outputs training transcripts.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from curriculum import Challenge, Curriculum
from dojo import Dojo
from skills import SkillsTracker, SkillGap, Topic


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

@dataclass
class Grade:
    """Result of grading a submitted solution."""

    score: float  # 0.0 - 1.0
    passed: bool
    feedback: str = ""
    criteria_met: list[str] = field(default_factory=list)
    criteria_missed: list[str] = field(default_factory=list)
    time_taken: float = 0.0  # minutes

    @property
    def letter(self) -> str:
        if self.score >= 0.9:
            return "A"
        if self.score >= 0.8:
            return "B"
        if self.score >= 0.7:
            return "C"
        if self.score >= 0.5:
            return "D"
        return "F"


def grade_solution(
    challenge: Challenge,
    solution: str,
    time_taken: float = 0.0,
) -> Grade:
    """Grade a solution against a challenge.

    Uses heuristic analysis of the solution text.
    In production this would run actual tests.
    """
    if not solution.strip():
        return Grade(
            score=0.0,
            passed=False,
            feedback="No solution provided.",
            criteria_missed=list(challenge.acceptance_criteria),
            time_taken=time_taken,
        )

    score = 0.0
    met: list[str] = []
    missed: list[str] = []

    sol_lower = solution.lower()

    # Check acceptance criteria heuristically
    for criterion in challenge.acceptance_criteria:
        crit_lower = criterion.lower()
        # Match criterion keywords against solution
        keywords = [w for w in crit_lower.split() if len(w) > 4]
        if keywords and any(kw in sol_lower for kw in keywords):
            score += 0.15
            met.append(criterion)
        elif not keywords:
            # Generic criterion: assume met if solution is substantial
            if len(solution) > 50:
                score += 0.1
                met.append(criterion)
            else:
                missed.append(criterion)
        else:
            missed.append(criterion)

    # Solution quality heuristics
    if len(solution.strip()) > 20:
        score += 0.1

    if "def " in solution or "class " in solution or "fn " in solution:
        score += 0.1

    if "test" in sol_lower:
        score += 0.1

    if "error" in sol_lower or "except" in sol_lower or "try:" in sol_lower:
        score += 0.05

    # Time bonus/penalty
    if time_taken > 0:
        if time_taken <= challenge.time_limit_minutes:
            score += 0.05
        else:
            overtime_ratio = time_taken / challenge.time_limit_minutes
            score -= 0.05 * (overtime_ratio - 1)

    # Blind challenge bonus
    if challenge.is_blind and len(missed) == 0:
        score += 0.1

    score = round(max(0.0, min(1.0, score)), 4)
    passed = score >= 0.5

    feedback_parts = []
    if passed:
        feedback_parts.append(f"Passed with score {score:.2f}")
        if met:
            feedback_parts.append(f"Met: {', '.join(met[:3])}")
    else:
        feedback_parts.append(f"Failed with score {score:.2f}")
        if missed:
            feedback_parts.append(f"Missed: {', '.join(missed[:3])}")

    return Grade(
        score=score,
        passed=passed,
        feedback="; ".join(feedback_parts),
        criteria_met=met,
        criteria_missed=missed,
        time_taken=time_taken,
    )


# ---------------------------------------------------------------------------
# Training transcript
# ---------------------------------------------------------------------------

@dataclass
class TranscriptEntry:
    """A single entry in the training transcript (commit-narrative style)."""

    timestamp: str
    challenge_id: str
    topic: str
    difficulty: int
    grade: str  # letter grade
    score: float
    passed: bool
    notes: str = ""

    def narrative(self) -> str:
        action = "completed" if self.passed else "attempted"
        status = f"[{self.grade}] {self.score:.0%}"
        return (
            f"[{self.timestamp}] {action} {self.topic} challenge "
            f"(difficulty {self.difficulty}) {status} — {self.notes}"
        )


class TrainingTranscript:
    """Commit-narrative style training log."""

    def __init__(self) -> None:
        self.entries: list[TranscriptEntry] = []

    def add_entry(
        self,
        challenge: Challenge,
        grade: Grade,
        notes: str = "",
    ) -> TranscriptEntry:
        entry = TranscriptEntry(
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            challenge_id=challenge.id,
            topic=challenge.topic.value,
            difficulty=challenge.difficulty,
            grade=grade.letter,
            score=grade.score,
            passed=grade.passed,
            notes=notes or grade.feedback,
        )
        self.entries.append(entry)
        return entry

    def __str__(self) -> str:
        lines = [
            "=" * 60,
            "  AGENT BOOTCAMP — Training Transcript",
            "=" * 60,
            "",
        ]
        for entry in self.entries:
            lines.append(entry.narrative())
            lines.append("")

        total = len(self.entries)
        passed = sum(1 for e in self.entries if e.passed)
        avg_score = (
            sum(e.score for e in self.entries) / total if total else 0.0
        )
        lines.append("-" * 60)
        lines.append(
            f"Summary: {passed}/{total} challenges passed, "
            f"average score {avg_score:.1%}"
        )
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "challenge_id": e.challenge_id,
                    "topic": e.topic,
                    "difficulty": e.difficulty,
                    "grade": e.grade,
                    "score": e.score,
                    "passed": e.passed,
                    "notes": e.notes,
                }
                for e in self.entries
            ],
            "summary": {
                "total": len(self.entries),
                "passed": sum(1 for e in self.entries if e.passed),
                "average_score": (
                    sum(e.score for e in self.entries) / len(self.entries)
                    if self.entries
                    else 0.0
                ),
            },
        }


# ---------------------------------------------------------------------------
# Bootcamp (core engine)
# ---------------------------------------------------------------------------

class Bootcamp:
    """Core training engine managing the full bootcamp lifecycle."""

    MAX_CHALLENGES_PER_SESSION = 50

    def __init__(
        self,
        agent_name: str,
        project_path: Optional[str] = None,
    ) -> None:
        self.agent_name = agent_name
        self.project_path = project_path
        self.skills = SkillsTracker()
        self.curriculum = Curriculum()
        self.transcript = TrainingTranscript()
        self.dojo = Dojo(agent_name)
        self.current_challenge: Optional[Challenge] = None
        self._challenges_done: int = 0
        self._session_active: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_training(self) -> None:
        """Begin a new training session."""
        self._session_active = True
        self.current_challenge = None
        self.next_challenge()

    def end_training(self) -> None:
        """End the current training session."""
        self._session_active = False
        self.current_challenge = None

    @property
    def is_active(self) -> bool:
        return self._session_active

    # ------------------------------------------------------------------
    # Challenge management
    # ------------------------------------------------------------------

    def next_challenge(self) -> Challenge:
        """Generate and return the next challenge."""
        if self._challenges_done >= self.MAX_CHALLENGES_PER_SESSION:
            raise RuntimeError("Maximum challenges per session reached")

        challenge = self.curriculum.generate_challenge()
        self.current_challenge = challenge
        return challenge

    def submit_solution(
        self,
        challenge_id: str,
        solution: str,
        time_taken: float = 0.0,
    ) -> Grade:
        """Submit a solution for grading.

        Updates skills, transcript, and curriculum progression.
        """
        if self.current_challenge is None:
            raise RuntimeError("No active challenge. Call next_challenge() first.")

        if self.current_challenge.id != challenge_id:
            raise ValueError(
                f"Challenge ID mismatch: expected {self.current_challenge.id}, got {challenge_id}"
            )

        grade = grade_solution(self.current_challenge, solution, time_taken)

        # Record in skills
        self.skills.record(
            topic=self.current_challenge.topic,
            score=grade.score,
            challenge_id=challenge_id,
            details=grade.feedback,
        )

        # Record in transcript
        self.transcript.add_entry(self.current_challenge, grade)

        self._challenges_done += 1

        # Advance curriculum after each submission
        # If agent failed, try same topic again next time
        if not grade.passed:
            # Reset topic index so same topic comes up again
            self.curriculum._topic_index = max(
                0, self.curriculum._topic_index - 1
            )
        # Check for rotation advance (every N challenges in a topic cycle)
        topic_count = len(self.curriculum.current_day_topics())
        if self._challenges_done % topic_count == 0:
            self.curriculum.advance_rotation()

        # Clear current challenge
        self.current_challenge = None

        return grade

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def assess_weaknesses(self) -> list[SkillGap]:
        """Identify current skill gaps."""
        return self.skills.assess_weaknesses()

    def generate_curriculum(self, count: int = 20) -> list[Challenge]:
        """Generate an adaptive curriculum based on current skills."""
        return self.curriculum.generate_curriculum(
            skills=self.skills, count=count
        )

    def get_transcript(self) -> str:
        """Return the full training transcript as a string."""
        return str(self.transcript)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def export_report(self, path: str) -> None:
        """Export a full training report to a JSON file."""
        report = {
            "agent_name": self.agent_name,
            "project_path": self.project_path,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "skills": self.skills.to_dict(),
            "dojo": self.dojo.summary(),
            "curriculum": {
                "day": self.curriculum.day,
                "rotation": self.curriculum.rotation,
                "challenges_generated": self.curriculum._challenges_generated,
            },
            "transcript": self.transcript.to_dict(),
            "session": {
                "active": self._session_active,
                "challenges_done": self._challenges_done,
            },
        }

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, "w") as f:
            json.dump(report, f, indent=2, default=str)

    def progress_report(self) -> dict[str, Any]:
        """Return a progress summary dict."""
        return {
            "agent": self.agent_name,
            "day": self.curriculum.day,
            "rotation": self.curriculum.rotation,
            "challenges_done": self._challenges_done,
            "overall_proficiency": self.skills.overall_proficiency(),
            "weaknesses": [
                {"topic": g.topic.value, "level": g.current_level}
                for g in self.skills.assess_weaknesses()
            ],
            "dojo_win_rate": self.dojo.win_rate(),
            "transcript_summary": self.transcript.to_dict().get("summary", {}),
        }


# ---------------------------------------------------------------------------
# Rankings (for multi-agent setups)
# ---------------------------------------------------------------------------

class Rankings:
    """Track and compare multiple agents."""

    def __init__(self) -> None:
        self._agents: dict[str, Bootcamp] = {}

    def register(self, bootcamp: Bootcamp) -> None:
        self._agents[bootcamp.agent_name] = bootcamp

    def leaderboard(self) -> list[dict[str, Any]]:
        """Return agents sorted by overall proficiency."""
        entries = []
        for name, bc in self._agents.items():
            entries.append({
                "name": name,
                "overall_proficiency": bc.skills.overall_proficiency(),
                "challenges_done": bc.skills.total_attempts(),
                "dojo_win_rate": bc.dojo.win_rate(),
                "average_score": bc.skills.average_score(),
            })
        entries.sort(key=lambda e: e["overall_proficiency"], reverse=True)
        return entries

    def rank(self, agent_name: str) -> int:
        """Return 1-based rank of an agent."""
        board = self.leaderboard()
        for i, entry in enumerate(board):
            if entry["name"] == agent_name:
                return i + 1
        return len(board) + 1
