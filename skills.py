"""Skills tracking for agent bootcamp.

Tracks proficiency per topic (0.0-1.0), history of attempts,
weakness detection, skill plateaus, and exports.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Topic(Enum):
    RECONNAISSANCE = "reconnaissance"
    FIRST_WINS = "first_wins"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    INTEGRATION = "integration"
    DEBUGGING = "debugging"
    ESTIMATION = "estimation"
    DOJO = "dojo"


@dataclass
class SkillRecord:
    """A single scored attempt at a topic."""

    topic: Topic
    score: float  # 0.0 - 1.0
    challenge_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    details: str = ""


@dataclass
class SkillGap:
    """Identified weakness in an agent's skills."""

    topic: Topic
    current_level: float
    target_level: float
    consecutive_failures: int = 0
    suggested_difficulty: int = 1


class SkillsTracker:
    """Track and analyse an agent's skill proficiency over time."""

    def __init__(self) -> None:
        self.records: list[SkillRecord] = []
        self._proficiency_cache: dict[Topic, float] | None = None
        # consecutive failure counter per topic
        self._failure_streaks: dict[Topic, int] = {t: 0 for t in Topic}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, topic: Topic, score: float, challenge_id: str, details: str = "") -> SkillRecord:
        """Record an attempt and return the created record."""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")
        rec = SkillRecord(topic=topic, score=score, challenge_id=challenge_id, details=details)
        self.records.append(rec)
        self._proficiency_cache = None  # invalidate
        # update failure streak
        if score < 0.4:
            self._failure_streaks[topic] = self._failure_streaks.get(topic, 0) + 1
        else:
            self._failure_streaks[topic] = 0
        return rec

    # ------------------------------------------------------------------
    # Proficiency
    # ------------------------------------------------------------------

    def proficiency(self, topic: Topic) -> float:
        """Return current proficiency for a topic (0.0-1.0).

        Uses an exponential moving average of recent scores so that
        improvement is visible quickly but old data decays.
        """
        topic_records = [r for r in self.records if r.topic is topic]
        if not topic_records:
            return 0.0
        # EMA with alpha = 0.3 (recent scores matter more)
        ema = topic_records[0].score
        alpha = 0.3
        for r in topic_records[1:]:
            ema = alpha * r.score + (1 - alpha) * ema
        return round(ema, 4)

    def all_proficiencies(self) -> dict[Topic, float]:
        """Return proficiency for every topic."""
        return {t: self.proficiency(t) for t in Topic}

    def overall_proficiency(self) -> float:
        """Average proficiency across all topics."""
        profs = self.all_proficiencies()
        return round(sum(profs.values()) / len(profs), 4) if profs else 0.0

    # ------------------------------------------------------------------
    # Weaknesses & plateaus
    # ------------------------------------------------------------------

    def assess_weaknesses(self) -> list[SkillGap]:
        """Identify topics where the agent is struggling.

        A weakness is flagged when:
        - proficiency < 0.5, or
        - 3+ consecutive failures on a topic
        """
        gaps: list[SkillGap] = []
        for topic in Topic:
            prof = self.proficiency(topic)
            failures = self._failure_streaks.get(topic, 0)
            is_weak = prof < 0.5 or failures >= 3
            if is_weak:
                gaps.append(
                    SkillGap(
                        topic=topic,
                        current_level=prof,
                        target_level=min(prof + 0.2, 1.0),
                        consecutive_failures=failures,
                        suggested_difficulty=max(1, int(prof * 5)),
                    )
                )
        gaps.sort(key=lambda g: g.consecutive_failures, reverse=True)
        return gaps

    def detect_plateaus(self, window: int = 5) -> list[Topic]:
        """Detect topics where the agent has stopped improving.

        Compares the average score of the last *window* attempts
        with the *window* attempts before that.
        """
        plateaus: list[Topic] = []
        for topic in Topic:
            recs = [r for r in self.records if r.topic is topic]
            if len(recs) < window * 2:
                continue
            recent = [r.score for r in recs[-window:]]
            older = [r.score for r in recs[-(window * 2):-window]]
            if abs(sum(recent) / len(recent) - sum(older) / len(older)) < 0.05:
                plateaus.append(topic)
        return plateaus

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def attempts_for(self, topic: Topic) -> list[SkillRecord]:
        return [r for r in self.records if r.topic is topic]

    def total_attempts(self) -> int:
        return len(self.records)

    def average_score(self) -> float:
        if not self.records:
            return 0.0
        return round(sum(r.score for r in self.records) / len(self.records), 4)

    def _topics_with_records(self) -> set[Topic]:
        return {r.topic for r in self.records}

    def best_topic(self) -> Topic | None:
        topics = self._topics_with_records()
        if not topics:
            return None
        return max(topics, key=lambda t: self.proficiency(t))

    def worst_topic(self) -> Topic | None:
        topics = self._topics_with_records()
        if not topics:
            return None
        return min(topics, key=lambda t: self.proficiency(t))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [
                {
                    "topic": r.topic.value,
                    "score": r.score,
                    "challenge_id": r.challenge_id,
                    "timestamp": r.timestamp,
                    "details": r.details,
                }
                for r in self.records
            ],
            "proficiencies": {t.value: v for t, v in self.all_proficiencies().items()},
            "overall": self.overall_proficiency(),
            "weaknesses": [
                {
                    "topic": g.topic.value,
                    "current_level": g.current_level,
                    "target_level": g.target_level,
                    "consecutive_failures": g.consecutive_failures,
                }
                for g in self.assess_weaknesses()
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["topic", "score", "challenge_id", "timestamp", "details"])
        for r in self.records:
            writer.writerow([r.topic.value, r.score, r.challenge_id, r.timestamp, r.details])
        return buf.getvalue()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillsTracker:
        tracker = cls()
        for rec in data.get("records", []):
            tracker.record(
                topic=Topic(rec["topic"]),
                score=rec["score"],
                challenge_id=rec["challenge_id"],
                details=rec.get("details", ""),
            )
        return tracker
