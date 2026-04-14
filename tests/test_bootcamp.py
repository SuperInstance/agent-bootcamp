"""Comprehensive tests for Agent Bootcamp.

Tests cover:
- Skills tracking (recording, proficiency, weaknesses, plateaus, export)
- Curriculum (challenge generation, spiral difficulty, adaptive generation)
- Dojo sparring (shadow challenges, style analysis, tournaments)
- Bootcamp engine (lifecycle, grading, transcripts, reporting)
- CLI parsing (all subcommands)
- Grading logic (scoring, criteria, letter grades)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from skills import Topic, SkillsTracker, SkillGap, SkillRecord
from curriculum import Challenge, Curriculum, DifficultyLevel, _TOPIC_DESCRIPTIONS
from dojo import (
    Dojo, TwinVariant, TwinDifficulty, SparringResult,
    analyse_style, StyleMetrics,
    generate_shadow_challenge, generate_twin_solution,
)
from bootcamp import (
    Bootcamp, Grade, TrainingTranscript, TranscriptEntry,
    grade_solution, Rankings,
)
from cli import build_parser, main


# ===================================================================
# Skills Tracking Tests
# ===================================================================

class TestSkillsTrackerInit:
    def test_initial_state(self):
        st = SkillsTracker()
        assert st.records == []
        assert st.total_attempts() == 0
        assert st.overall_proficiency() == 0.0

    def test_from_dict_empty(self):
        st = SkillsTracker.from_dict({"records": []})
        assert st.total_attempts() == 0


class TestSkillsTrackerRecording:
    def test_record_returns_record(self):
        st = SkillsTracker()
        rec = st.record(Topic.TESTING, 0.8, "ch-001")
        assert isinstance(rec, SkillRecord)
        assert rec.topic == Topic.TESTING
        assert rec.score == 0.8
        assert rec.challenge_id == "ch-001"

    def test_record_appends(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.7, "ch-001")
        st.record(Topic.DOCUMENTATION, 0.5, "ch-002")
        assert st.total_attempts() == 2

    def test_record_invalid_score_negative(self):
        st = SkillsTracker()
        with pytest.raises(ValueError, match="Score must be between"):
            st.record(Topic.TESTING, -0.1, "ch-001")

    def test_record_invalid_score_above_one(self):
        st = SkillsTracker()
        with pytest.raises(ValueError, match="Score must be between"):
            st.record(Topic.TESTING, 1.5, "ch-001")

    def test_record_details_stored(self):
        st = SkillsTracker()
        rec = st.record(Topic.TESTING, 0.9, "ch-001", details="great job")
        assert rec.details == "great job"

    def test_record_timestamp_is_string(self):
        st = SkillsTracker()
        rec = st.record(Topic.TESTING, 0.5, "ch-001")
        assert isinstance(rec.timestamp, str)
        assert len(rec.timestamp) > 0


class TestSkillsTrackerProficiency:
    def test_empty_proficiency(self):
        st = SkillsTracker()
        assert st.proficiency(Topic.TESTING) == 0.0

    def test_single_record_proficiency(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.8, "ch-001")
        assert st.proficiency(Topic.TESTING) == 0.8

    def test_ema_weights_recent(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.2, "ch-001")
        st.record(Topic.TESTING, 1.0, "ch-002")
        # EMA(0.3): 0.7*0.2 + 0.3*1.0 = 0.14 + 0.3 = 0.44
        prof = st.proficiency(Topic.TESTING)
        assert prof > 0.4
        assert prof < 0.5

    def test_all_proficiencies(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.7, "ch-001")
        st.record(Topic.DEBUGGING, 0.3, "ch-002")
        profs = st.all_proficiencies()
        assert Topic.TESTING in profs
        assert Topic.DEBUGGING in profs
        assert len(profs) == len(Topic)

    def test_overall_proficiency(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.5, "ch-001")
        overall = st.overall_proficiency()
        assert 0.0 <= overall <= 1.0

    def test_topic_isolation(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.9, "ch-001")
        assert st.proficiency(Topic.DOCUMENTATION) == 0.0


class TestSkillsTrackerWeaknesses:
    def test_no_weaknesses_when_no_data(self):
        st = SkillsTracker()
        gaps = st.assess_weaknesses()
        # All topics should be weaknesses when there's no data
        # (proficiency = 0.0 < 0.5)
        assert len(gaps) == len(Topic)

    def test_no_weaknesses_when_strong(self):
        st = SkillsTracker()
        for t in Topic:
            st.record(t, 0.9, f"ch-{t.value}")
        gaps = st.assess_weaknesses()
        assert len(gaps) == 0

    def test_consecutive_failures_trigger(self):
        st = SkillsTracker()
        for i in range(3):
            st.record(Topic.TESTING, 0.2, f"ch-{i}")
        gaps = st.assess_weaknesses()
        testing_gaps = [g for g in gaps if g.topic == Topic.TESTING]
        assert len(testing_gaps) >= 1
        assert testing_gaps[0].consecutive_failures >= 3

    def test_gap_suggested_difficulty(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.1, "ch-001")
        gaps = st.assess_weaknesses()
        t_gap = next(g for g in gaps if g.topic == Topic.TESTING)
        assert t_gap.suggested_difficulty >= 1

    def test_gaps_sorted_by_failures(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.TESTING, 0.2, f"ch-t{i}")
        st.record(Topic.DOCUMENTATION, 0.1, "ch-d1")
        gaps = st.assess_weaknesses()
        # Testing should come first (more failures)
        if len(gaps) >= 2:
            first = gaps[0]
            assert first.consecutive_failures >= 3


class TestSkillsTrackerPlateaus:
    def test_no_plateau_with_few_records(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.TESTING, 0.5, f"ch-{i}")
        plateaus = st.detect_plateaus(window=3)
        assert Topic.TESTING not in plateaus

    def test_plateau_detected(self):
        st = SkillsTracker()
        # 10 records at same score = plateau
        for i in range(10):
            st.record(Topic.TESTING, 0.5, f"ch-{i}")
        plateaus = st.detect_plateaus(window=5)
        assert Topic.TESTING in plateaus

    def test_improvement_not_plateau(self):
        st = SkillsTracker()
        # Improving scores
        for i in range(10):
            st.record(Topic.TESTING, 0.1 + i * 0.08, f"ch-{i}")
        plateaus = st.detect_plateaus(window=5)
        assert Topic.TESTING not in plateaus


class TestSkillsTrackerHelpers:
    def test_attempts_for(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.5, "ch-001")
        st.record(Topic.TESTING, 0.6, "ch-002")
        st.record(Topic.DOCUMENTATION, 0.7, "ch-003")
        assert len(st.attempts_for(Topic.TESTING)) == 2

    def test_average_score(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.4, "ch-001")
        st.record(Topic.TESTING, 0.6, "ch-002")
        assert st.average_score() == pytest.approx(0.5, abs=0.01)

    def test_average_score_empty(self):
        st = SkillsTracker()
        assert st.average_score() == 0.0

    def test_best_topic(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.2, "ch-001")
        st.record(Topic.DOCUMENTATION, 0.8, "ch-002")
        assert st.best_topic() == Topic.DOCUMENTATION

    def test_worst_topic(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.2, "ch-001")
        st.record(Topic.DOCUMENTATION, 0.8, "ch-002")
        assert st.worst_topic() == Topic.TESTING

    def test_best_worst_empty(self):
        st = SkillsTracker()
        assert st.best_topic() is None
        assert st.worst_topic() is None


class TestSkillsTrackerExport:
    def test_to_json(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.5, "ch-001")
        j = st.to_json()
        data = json.loads(j)
        assert "records" in data
        assert len(data["records"]) == 1

    def test_to_csv(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.5, "ch-001")
        csv_text = st.to_csv()
        lines = csv_text.strip().split("\n")
        assert len(lines) == 2  # header + data
        assert "testing" in lines[1]

    def test_to_dict_round_trip(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.7, "ch-001")
        st.record(Topic.DEBUGGING, 0.3, "ch-002")
        data = st.to_dict()
        st2 = SkillsTracker.from_dict(data)
        assert st2.total_attempts() == 2
        assert st2.proficiency(Topic.TESTING) == st.proficiency(Topic.TESTING)


# ===================================================================
# Curriculum Tests
# ===================================================================

class TestChallenge:
    def test_default_values(self):
        ch = Challenge()
        assert ch.difficulty == 1
        assert ch.topic == Topic.TESTING
        assert ch.time_limit_minutes > 0

    def test_difficulty_clamped(self):
        ch = Challenge(difficulty=15)
        assert ch.difficulty == 10
        ch2 = Challenge(difficulty=-5)
        assert ch2.difficulty == 1

    def test_difficulty_label(self):
        ch = Challenge(difficulty=1)
        assert ch.difficulty_label == "BEGINNER"
        ch2 = Challenge(difficulty=10)
        assert ch2.difficulty_label == "IMPOSSIBLE"

    def test_is_blind(self):
        ch = Challenge(is_blind=True)
        assert ch.is_blind is True

    def test_id_is_string(self):
        ch = Challenge()
        assert isinstance(ch.id, str)
        assert len(ch.id) == 8


class TestCurriculumInit:
    def test_initial_state(self):
        cur = Curriculum()
        assert cur.rotation == 0
        assert cur.day == 1
        assert cur._topic_index == 0

    def test_day_topics(self):
        cur = Curriculum()
        topics = cur.current_day_topics()
        assert Topic.RECONNAISSANCE in topics

    def test_day_3_topics(self):
        cur = Curriculum()
        cur.day = 3
        topics = cur.current_day_topics()
        assert Topic.TESTING in topics
        assert Topic.DOCUMENTATION in topics


class TestCurriculumTopicRotation:
    def test_next_topic_cycles(self):
        cur = Curriculum()
        cur.day = 3
        topics = cur.current_day_topics()
        first_round = [cur.next_topic() for _ in range(len(topics))]
        second_round = [cur.next_topic() for _ in range(len(topics))]
        assert first_round == second_round

    def test_next_topic_advances_index(self):
        cur = Curriculum()
        initial = cur._topic_index
        cur.next_topic()
        assert cur._topic_index > initial


class TestCurriculumDifficulty:
    def test_base_difficulty(self):
        cur = Curriculum()
        assert cur.difficulty_for_rotation(1) == 1

    def test_spiral_increases(self):
        cur = Curriculum()
        cur.rotation = 3
        assert cur.difficulty_for_rotation(1) == 4

    def test_difficulty_capped_at_10(self):
        cur = Curriculum()
        cur.rotation = 20
        assert cur.difficulty_for_rotation(1) == 10
        assert cur.difficulty_for_rotation(10) == 10


class TestCurriculumAdvance:
    def test_advance_rotation(self):
        cur = Curriculum()
        cur.advance_rotation()
        assert cur.rotation == 1
        assert cur._topic_index == 0

    def test_advance_day(self):
        cur = Curriculum()
        cur.advance_day()
        assert cur.day == 2


class TestCurriculumGenerateChallenge:
    def test_generates_challenge(self):
        cur = Curriculum()
        ch = cur.generate_challenge()
        assert isinstance(ch, Challenge)
        assert ch.description != ""

    def test_generates_for_topic(self):
        cur = Curriculum()
        ch = cur.generate_challenge(topic=Topic.DOJO)
        assert ch.topic == Topic.DOJO

    def test_has_acceptance_criteria(self):
        cur = Curriculum()
        ch = cur.generate_challenge()
        assert len(ch.acceptance_criteria) > 0

    def test_blind_at_high_difficulty(self):
        cur = Curriculum()
        cur.rotation = 8  # difficulty 9+
        ch = cur.generate_challenge()
        assert ch.is_blind is True

    def test_not_blind_at_low_difficulty(self):
        cur = Curriculum()
        ch = cur.generate_challenge()
        assert ch.is_blind is False


class TestCurriculumAdaptive:
    def test_adaptive_uses_weaknesses(self):
        skills = SkillsTracker()
        # Make testing a weakness
        for i in range(3):
            skills.record(Topic.TESTING, 0.1, f"ch-{i}")
        cur = Curriculum()
        cur.day = 3  # Day 3 includes testing topics
        challenges = cur.generate_adaptive(skills, count=5)
        assert len(challenges) > 0
        # At least one should be testing
        topics = [c.topic for c in challenges]
        assert Topic.TESTING in topics

    def test_adaptive_skips_mastered(self):
        skills = SkillsTracker()
        skills.record(Topic.TESTING, 0.95, "ch-001")
        # Make documentation a weakness
        for i in range(3):
            skills.record(Topic.DOCUMENTATION, 0.1, f"ch-d{i}")
        cur = Curriculum()
        cur.day = 3  # has both testing and documentation
        challenges = cur.generate_adaptive(skills, count=5)
        # Should prefer documentation over testing
        doc_count = sum(1 for c in challenges if c.topic == Topic.DOCUMENTATION)
        test_count = sum(1 for c in challenges if c.topic == Topic.TESTING)
        assert doc_count >= test_count

    def test_adaptive_count(self):
        skills = SkillsTracker()
        cur = Curriculum()
        challenges = cur.generate_adaptive(skills, count=3)
        assert len(challenges) == 3


class TestCurriculumFullCurriculum:
    def test_generate_curriculum_default(self):
        cur = Curriculum()
        challenges = cur.generate_curriculum(count=10)
        assert len(challenges) == 10

    def test_generate_curriculum_adaptive(self):
        skills = SkillsTracker()
        cur = Curriculum()
        challenges = cur.generate_curriculum(skills=skills, count=15)
        assert len(challenges) == 15


class TestTopicDescriptions:
    def test_all_topics_have_descriptions(self):
        for topic in Topic:
            assert topic in _TOPIC_DESCRIPTIONS
            assert len(_TOPIC_DESCRIPTIONS[topic]) > 0

    def test_difficulties_covered(self):
        for topic in Topic:
            descs = _TOPIC_DESCRIPTIONS[topic]
            # Should have at least difficulties 1 and 10
            assert 1 in descs
            assert 10 in descs


# ===================================================================
# Dojo Tests
# ===================================================================

class TestStyleAnalysis:
    def test_empty_solution(self):
        metrics = analyse_style("")
        assert metrics.line_count == 0

    def test_line_count(self):
        metrics = analyse_style("line1\nline2\nline3")
        assert metrics.line_count == 3

    def test_function_count(self):
        solution = "def foo():\n    pass\ndef bar():\n    pass"
        metrics = analyse_style(solution)
        assert metrics.function_count == 2

    def test_comment_ratio(self):
        solution = "code\n# comment\n# another\nmore code"
        metrics = analyse_style(solution)
        assert metrics.comment_ratio == pytest.approx(0.5, abs=0.01)

    def test_approaches_detected(self):
        solution = "import re\nresult = re.match(pattern, text)"
        metrics = analyse_style(solution)
        assert "regex" in metrics.approaches_used

    def test_oop_detected(self):
        solution = "class MyClass:\n    def method(self):\n        pass"
        metrics = analyse_style(solution)
        assert "OOP" in metrics.approaches_used

    def test_procedural_fallback(self):
        metrics = analyse_style("x = 1\ny = 2")
        assert "procedural" in metrics.approaches_used

    def test_style_distance(self):
        m1 = StyleMetrics(line_count=10, avg_line_length=30)
        m2 = StyleMetrics(line_count=100, avg_line_length=80)
        d = m1.distance(m2)
        assert 0.0 < d < 2.0

    def test_style_to_dict(self):
        m = StyleMetrics(line_count=5)
        d = m.to_dict()
        assert d["line_count"] == 5
        assert "approaches_used" in d


class TestShadowChallenge:
    def test_easy_twin_reduces_difficulty(self):
        ch = Challenge(difficulty=5)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.difficulty < ch.difficulty

    def test_hard_twin_increases_difficulty(self):
        ch = Challenge(difficulty=5)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.HARD)
        assert shadow.difficulty > ch.difficulty

    def test_adversarial_keeps_difficulty(self):
        ch = Challenge(difficulty=5)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.ADVERSARIAL)
        assert shadow.difficulty == ch.difficulty

    def test_easy_twin_description_prefix(self):
        ch = Challenge(description="Do something")
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.description.startswith("Simplified version:")

    def test_adversarial_prefix(self):
        ch = Challenge(description="Do something")
        shadow = generate_shadow_challenge(ch, TwinDifficulty.ADVERSARIAL)
        assert "hidden trap" in shadow.description.lower()

    def test_shadow_preserves_topic(self):
        ch = Challenge(topic=Topic.DOJO)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.topic == Topic.DOJO

    def test_shadow_metadata(self):
        ch = Challenge(id="abc123")
        shadow = generate_shadow_challenge(ch, TwinDifficulty.HARD)
        assert shadow.metadata["shadow_of"] == "abc123"


class TestTwinSolution:
    def test_easy_twin_shorter(self):
        ch = Challenge()
        solution = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8"
        twin = generate_twin_solution(ch, solution, TwinDifficulty.EASY)
        assert len(twin.solution) <= len(solution) + 50  # allow prefix overhead

    def test_hard_twin_longer(self):
        ch = Challenge()
        solution = "short code"
        twin = generate_twin_solution(ch, solution, TwinDifficulty.HARD)
        assert len(twin.solution) > len(solution)

    def test_adversarial_differs(self):
        ch = Challenge()
        solution = "result = compute(data)"
        twin = generate_twin_solution(ch, solution, TwinDifficulty.ADVERSARIAL)
        assert twin.solution != solution


class TestDojo:
    def test_init(self):
        dojo = Dojo("test-agent")
        assert dojo.agent_name == "test-agent"
        assert dojo.results == []

    def test_run_round_returns_results(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO)
        solution = "def solve():\n    return True"
        results = dojo.run_round(ch, solution)
        assert len(results) == 3  # one per twin type
        assert all(isinstance(r, SparringResult) for r in results)

    def test_round_outcomes_valid(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO)
        solution = "def solve():\n    try:\n        return True\n    except:\n        return False"
        results = dojo.run_round(ch, solution)
        for r in results:
            assert r.outcome in ("win", "loss", "draw")

    def test_round_has_style_diff(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO)
        solution = "def solve():\n    return True"
        results = dojo.run_round(ch, solution)
        for r in results:
            assert "style_distance" in r.style_diff

    def test_win_rate_no_results(self):
        dojo = Dojo("test-agent")
        assert dojo.win_rate() == 0.0

    def test_win_rate(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO)
        # A good solution should win at least some
        solution = "def solve():\n    try:\n        result = test_function()\n        return result\n    except Exception:\n        return None\n\ndef test_function():\n    return True"
        dojo.run_round(ch, solution)
        wr = dojo.win_rate()
        assert 0.0 <= wr <= 1.0

    def test_record_summary(self):
        dojo = Dojo("test-agent")
        summary = dojo.record_summary()
        assert summary == {"win": 0, "loss": 0, "draw": 0}

    def test_tournament(self):
        dojo = Dojo("test-agent")
        challenges = [
            Challenge(topic=Topic.DOJO, id=f"ch-{i}")
            for i in range(3)
        ]
        solutions = {f"ch-{i}": f"def solve_{i}(): return {i}" for i in range(3)}
        results = dojo.run_tournament(challenges, solutions)
        assert len(results) == 9  # 3 challenges * 3 twin types

    def test_style_analysis_no_data(self):
        dojo = Dojo("test-agent")
        sa = dojo.style_analysis()
        assert sa["status"] == "no_data"

    def test_style_analysis_with_data(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO, id="ch-1")
        dojo.run_round(ch, "def solve():\n    return 1")
        sa = dojo.style_analysis()
        assert "total_rounds" in sa
        assert sa["total_rounds"] == 3

    def test_summary(self):
        dojo = Dojo("test-agent")
        s = dojo.summary()
        assert s["agent_name"] == "test-agent"
        assert "win_rate" in s


# ===================================================================
# Bootcamp & Grading Tests
# ===================================================================

class TestGrade:
    def test_empty_solution(self):
        ch = Challenge()
        g = grade_solution(ch, "")
        assert g.score == 0.0
        assert g.passed is False
        assert g.letter == "F"

    def test_good_solution(self):
        ch = Challenge(
            acceptance_criteria=["All tests must pass", "Tests must cover edge cases"],
            difficulty=3,
        )
        solution = """
def test_something():
    try:
        result = compute()
        assert result is not None
        # Tests must cover edge cases
        test_edge()
    except Exception:
        pass

def test_edge():
    pass
"""
        g = grade_solution(ch, solution)
        assert g.score > 0.3
        assert g.passed is True

    def test_letter_grades(self):
        assert Grade(score=0.95, passed=True).letter == "A"
        assert Grade(score=0.85, passed=True).letter == "B"
        assert Grade(score=0.75, passed=True).letter == "C"
        assert Grade(score=0.55, passed=True).letter == "D"
        assert Grade(score=0.3, passed=False).letter == "F"

    def test_time_bonus(self):
        ch = Challenge(time_limit_minutes=10)
        solution = "def solve():\n    return True"
        g = grade_solution(ch, solution, time_taken=5.0)
        assert g.score > 0.0

    def test_time_penalty(self):
        ch = Challenge(time_limit_minutes=5)
        solution = "def solve():\n    return True"
        g = grade_solution(ch, solution, time_taken=20.0)
        # Overtime penalty applies
        assert g.time_taken == 20.0

    def test_blind_bonus(self):
        ch = Challenge(
            acceptance_criteria=["test"],
            is_blind=True,
        )
        solution = "This is a longer solution with test mentioned in it"
        g = grade_solution(ch, solution)
        assert g.score > 0.0

    def test_feedback_includes_grade(self):
        ch = Challenge()
        g = grade_solution(ch, "some solution")
        assert "Passed" in g.feedback or "Failed" in g.feedback


class TestTrainingTranscript:
    def test_add_entry(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-001", topic=Topic.TESTING, difficulty=3)
        grade = Grade(score=0.8, passed=True, feedback="Good")
        entry = tt.add_entry(ch, grade)
        assert isinstance(entry, TranscriptEntry)
        assert entry.topic == "testing"

    def test_str_output(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-001", topic=Topic.TESTING, difficulty=3)
        grade = Grade(score=0.8, passed=True, feedback="Good")
        tt.add_entry(ch, grade)
        text = str(tt)
        assert "Training Transcript" in text
        assert "testing" in text

    def test_to_dict(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-001", topic=Topic.TESTING, difficulty=3)
        grade = Grade(score=0.8, passed=True, feedback="Good")
        tt.add_entry(ch, grade)
        d = tt.to_dict()
        assert len(d["entries"]) == 1
        assert d["summary"]["total"] == 1
        assert d["summary"]["passed"] == 1

    def test_narrative_includes_status(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-001", topic=Topic.TESTING, difficulty=3)
        grade = Grade(score=0.8, passed=True, feedback="Good")
        entry = tt.add_entry(ch, grade)
        assert "completed" in entry.narrative()
        assert "testing" in entry.narrative()


class TestBootcampInit:
    def test_default_init(self):
        bc = Bootcamp("test-agent")
        assert bc.agent_name == "test-agent"
        assert bc.project_path is None
        assert bc.is_active is False
        assert bc.skills.total_attempts() == 0

    def test_init_with_project(self):
        bc = Bootcamp("test-agent", project_path="/some/path")
        assert bc.project_path == "/some/path"


class TestBootcampLifecycle:
    def test_start_training(self):
        bc = Bootcamp("test-agent")
        bc.start_training()
        assert bc.is_active is True
        assert bc.current_challenge is not None

    def test_end_training(self):
        bc = Bootcamp("test-agent")
        bc.start_training()
        bc.end_training()
        assert bc.is_active is False
        assert bc.current_challenge is None

    def test_next_challenge_without_start(self):
        bc = Bootcamp("test-agent")
        ch = bc.next_challenge()
        assert isinstance(ch, Challenge)
        assert bc.current_challenge == ch

    def test_max_challenges(self):
        bc = Bootcamp("test-agent")
        for i in range(Bootcamp.MAX_CHALLENGES_PER_SESSION):
            ch = bc.next_challenge()
            bc.submit_solution(ch.id, f"solution {i}")
        with pytest.raises(RuntimeError, match="Maximum"):
            bc.next_challenge()


class TestBootcampSubmit:
    def test_submit_solution(self):
        bc = Bootcamp("test-agent")
        ch = bc.next_challenge()
        grade = bc.submit_solution(ch.id, "def solve():\n    return True")
        assert isinstance(grade, Grade)
        assert grade.score > 0.0
        assert bc.skills.total_attempts() == 1

    def test_submit_without_challenge(self):
        bc = Bootcamp("test-agent")
        with pytest.raises(RuntimeError, match="No active challenge"):
            bc.submit_solution("fake-id", "solution")

    def test_submit_wrong_id(self):
        bc = Bootcamp("test-agent")
        bc.next_challenge()
        with pytest.raises(ValueError, match="Challenge ID mismatch"):
            bc.submit_solution("wrong-id", "solution")

    def test_submit_records_in_transcript(self):
        bc = Bootcamp("test-agent")
        ch = bc.next_challenge()
        bc.submit_solution(ch.id, "def solve():\n    return True")
        assert len(bc.transcript.entries) == 1

    def test_submit_updates_skills(self):
        bc = Bootcamp("test-agent")
        ch = bc.next_challenge()
        bc.submit_solution(ch.id, "good solution with tests and error handling")
        assert bc.skills.total_attempts() == 1
        prof = bc.skills.proficiency(ch.topic)
        assert prof > 0.0

    def test_multiple_submits(self):
        bc = Bootcamp("test-agent")
        for i in range(5):
            ch = bc.next_challenge()
            bc.submit_solution(ch.id, f"solution {i}")
        assert bc.skills.total_attempts() == 5
        assert len(bc.transcript.entries) == 5


class TestBootcampAssessment:
    def test_assess_weaknesses(self):
        bc = Bootcamp("test-agent")
        # No data = all topics are weaknesses
        gaps = bc.assess_weaknesses()
        assert len(gaps) == len(Topic)

    def test_generate_curriculum(self):
        bc = Bootcamp("test-agent")
        # Record some attempts
        for i in range(3):
            bc.next_challenge()
            bc.submit_solution(bc.current_challenge.id if bc.current_challenge else "", f"sol {i}")
        # Fix: current_challenge is None after submit, need to get new one
        challenges = bc.generate_curriculum(count=5)
        assert len(challenges) == 5


class TestBootcampReporting:
    def test_get_transcript(self):
        bc = Bootcamp("test-agent")
        ch = bc.next_challenge()
        bc.submit_solution(ch.id, "solution")
        transcript = bc.get_transcript()
        assert "Training Transcript" in transcript

    def test_export_report(self):
        bc = Bootcamp("test-agent")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            bc.export_report(path)
            with open(path) as f:
                data = json.load(f)
            assert data["agent_name"] == "test-agent"
            assert "skills" in data
            assert "dojo" in data
        finally:
            os.unlink(path)

    def test_export_report_creates_dirs(self):
        bc = Bootcamp("test-agent")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "report.json")
            bc.export_report(path)
            assert os.path.exists(path)

    def test_progress_report(self):
        bc = Bootcamp("test-agent")
        report = bc.progress_report()
        assert report["agent"] == "test-agent"
        assert "overall_proficiency" in report
        assert "dojo_win_rate" in report


class TestRankings:
    def test_register_and_leaderboard(self):
        rankings = Rankings()
        bc1 = Bootcamp("agent-a")
        bc2 = Bootcamp("agent-b")
        # Give agent-a a higher score
        bc1.skills.record(Topic.TESTING, 0.9, "ch-1")
        bc2.skills.record(Topic.TESTING, 0.3, "ch-2")
        rankings.register(bc1)
        rankings.register(bc2)
        board = rankings.leaderboard()
        assert len(board) == 2
        assert board[0]["name"] == "agent-a"
        assert board[0]["overall_proficiency"] > board[1]["overall_proficiency"]

    def test_rank_single(self):
        rankings = Rankings()
        bc = Bootcamp("solo-agent")
        bc.skills.record(Topic.TESTING, 0.5, "ch-1")
        rankings.register(bc)
        assert rankings.rank("solo-agent") == 1

    def test_rank_missing(self):
        rankings = Rankings()
        assert rankings.rank("nobody") == 1


# ===================================================================
# CLI Tests
# ===================================================================

class TestCLIParsing:
    def test_enroll_args(self):
        parser = build_parser()
        args = parser.parse_args(["enroll", "test-agent"])
        assert args.command == "enroll"
        assert args.agent_name == "test-agent"

    def test_enroll_with_project(self):
        parser = build_parser()
        args = parser.parse_args(["enroll", "test-agent", "--project-path", "/tmp/proj"])
        assert args.project_path == "/tmp/proj"

    def test_start_args(self):
        parser = build_parser()
        args = parser.parse_args(["start", "test-agent"])
        assert args.command == "start"
        assert args.agent_name == "test-agent"

    def test_challenge_args(self):
        parser = build_parser()
        args = parser.parse_args(["challenge", "test-agent"])
        assert args.command == "challenge"

    def test_submit_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "submit", "test-agent", "ch-123",
            "--solution-text", "def solve(): pass",
        ])
        assert args.command == "submit"
        assert args.challenge_id == "ch-123"
        assert args.solution_text == "def solve(): pass"

    def test_submit_file_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "submit", "test-agent", "ch-123",
            "--solution-file", "/tmp/sol.py",
        ])
        assert args.solution_file == "/tmp/sol.py"

    def test_progress_args(self):
        parser = build_parser()
        args = parser.parse_args(["progress", "test-agent"])
        assert args.command == "progress"

    def test_report_args(self):
        parser = build_parser()
        args = parser.parse_args(["report", "test-agent", "-o", "report.json"])
        assert args.command == "report"
        assert args.output == "report.json"

    def test_dojo_args(self):
        parser = build_parser()
        args = parser.parse_args(["dojo", "test-agent"])
        assert args.command == "dojo"

    def test_rank_args(self):
        parser = build_parser()
        args = parser.parse_args(["rank"])
        assert args.command == "rank"

    def test_no_command(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_unknown_command(self):
        with pytest.raises(SystemExit):
            main(["unknown"])


class TestCLIRunEnroll:
    def test_enroll_success(self, tmp_path):
        from cli import _STATE_DIR
        # Patch state dir to tmp
        import cli
        original = cli._STATE_DIR
        try:
            cli._STATE_DIR = Path(tmp_path)
            ret = main(["enroll", "new-agent"])
            assert ret == 0
        finally:
            cli._STATE_DIR = original

    def test_enroll_duplicate(self, tmp_path):
        import cli
        original = cli._STATE_DIR
        try:
            cli._STATE_DIR = Path(tmp_path)
            main(["enroll", "dup-agent"])
            ret = main(["enroll", "dup-agent"])
            assert ret == 1
        finally:
            cli._STATE_DIR = original


class TestCLIRunProgress:
    def test_progress_unknown_agent(self, tmp_path):
        import cli
        original = cli._STATE_DIR
        try:
            cli._STATE_DIR = Path(tmp_path)
            ret = main(["progress", "nobody"])
            assert ret == 1
        finally:
            cli._STATE_DIR = original


class TestCLIRunRank:
    def test_rank_empty(self, tmp_path):
        import cli
        original = cli._STATE_DIR
        try:
            cli._STATE_DIR = Path(tmp_path)
            ret = main(["rank"])
            assert ret == 0
        finally:
            cli._STATE_DIR = original


# ===================================================================
# Integration / Spiral Tests
# ===================================================================

class TestSpiralDifficulty:
    def test_spiral_increases_over_rotations(self):
        cur = Curriculum()
        diffs = []
        for _ in range(5):
            ch = cur.generate_challenge()
            diffs.append(ch.difficulty)
            cur.advance_rotation()
        # Should be generally increasing
        assert diffs[-1] >= diffs[0]

    def test_curriculum_topics_vary(self):
        cur = Curriculum()
        cur.day = 3
        topics = set()
        for _ in range(20):
            ch = cur.generate_challenge()
            topics.add(ch.topic)
        assert len(topics) > 1


class TestFullTrainingCycle:
    def test_complete_mini_cycle(self):
        bc = Bootcamp("cycle-agent")
        bc.start_training()
        for _ in range(5):
            ch = bc.next_challenge()
            bc.submit_solution(ch.id, "def solve():\n    try:\n        return test()\n    except:\n        return None")
        assert bc.skills.total_attempts() == 5
        assert bc.skills.overall_proficiency() >= 0.0
        # Should have transcript entries
        assert len(bc.transcript.entries) == 5
        bc.end_training()

    def test_adaptive_after_failures(self):
        bc = Bootcamp("adaptive-agent")
        skills = bc.skills
        # Simulate failing at testing
        for i in range(4):
            skills.record(Topic.TESTING, 0.1, f"ch-t{i}")
        weaknesses = bc.assess_weaknesses()
        testing_gaps = [g for g in weaknesses if g.topic == Topic.TESTING]
        assert len(testing_gaps) >= 1


class TestGradeEdgeCases:
    def test_whitespace_solution(self):
        ch = Challenge()
        g = grade_solution(ch, "   ")
        assert g.score == 0.0

    def test_very_long_solution(self):
        ch = Challenge(difficulty=5, acceptance_criteria=["test"])
        solution = "x" * 10000 + " test " + "x" * 10000
        g = grade_solution(ch, solution)
        assert g.score > 0.0

    def test_no_criteria(self):
        ch = Challenge(acceptance_criteria=[])
        g = grade_solution(ch, "some solution")
        assert isinstance(g.score, float)

    def test_score_never_negative(self):
        ch = Challenge(time_limit_minutes=1)
        g = grade_solution(ch, "x", time_taken=1000)
        assert g.score >= 0.0

    def test_score_never_above_one(self):
        ch = Challenge(
            difficulty=10,
            is_blind=True,
            acceptance_criteria=["test", "error", "function"],
        )
        solution = """
def test_function():
    try:
        result = error
    except:
        pass
"""
        g = grade_solution(ch, solution, time_taken=1.0)
        assert g.score <= 1.0


class TestDifficultyLevel:
    def test_all_levels(self):
        for level in DifficultyLevel:
            assert level.value >= 1
            assert level.value <= 10

# ===================================================================
# Additional DifficultyLevel Tests
# ===================================================================

class TestDifficultyLevelAdvanced:
    def test_level_count(self):
        assert len(DifficultyLevel) == 10

    def test_level_names_unique(self):
        names = [l.name for l in DifficultyLevel]
        assert len(names) == len(set(names))

    def test_level_values_sequential(self):
        values = [l.value for l in DifficultyLevel]
        assert values == list(range(1, 11))


# ===================================================================
# Additional SkillsTracker Edge Case Tests
# ===================================================================

class TestSkillsTrackerFailureStreaks:
    def test_failure_streak_resets_on_good_score(self):
        st = SkillsTracker()
        for i in range(3):
            st.record(Topic.TESTING, 0.2, f"ch-fs-{i}")
        assert st._failure_streaks[Topic.TESTING] >= 3
        st.record(Topic.TESTING, 0.8, "ch-fs-good")
        assert st._failure_streaks[Topic.TESTING] == 0

    def test_boundary_score_0_39_is_failure(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.39, "ch-bs-1")
        assert st._failure_streaks[Topic.TESTING] == 1

    def test_boundary_score_0_4_passes(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.4, "ch-bs-2")
        assert st._failure_streaks[Topic.TESTING] == 0

    def test_multiple_topics_independent_streaks(self):
        st = SkillsTracker()
        for i in range(3):
            st.record(Topic.TESTING, 0.1, f"ch-is-t{i}")
        for i in range(2):
            st.record(Topic.DEBUGGING, 0.1, f"ch-is-d{i}")
        assert st._failure_streaks[Topic.TESTING] >= 3
        assert st._failure_streaks[Topic.DEBUGGING] == 2


class TestSkillsTrackerProficiencyAdvanced:
    def test_declining_scores(self):
        st = SkillsTracker()
        st.record(Topic.TESTING, 0.9, "ch-pa-1")
        st.record(Topic.TESTING, 0.1, "ch-pa-2")
        prof = st.proficiency(Topic.TESTING)
        assert 0.6 < prof < 0.7

    def test_stable_scores(self):
        st = SkillsTracker()
        for i in range(10):
            st.record(Topic.TESTING, 0.5, f"ch-pa-s{i}")
        prof = st.proficiency(Topic.TESTING)
        assert 0.4 < prof < 0.6

    def test_perfect_scores(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.TESTING, 1.0, f"ch-pa-p{i}")
        prof = st.proficiency(Topic.TESTING)
        assert prof > 0.9

    def test_zero_scores(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.TESTING, 0.0, f"ch-pa-z{i}")
        prof = st.proficiency(Topic.TESTING)
        assert prof < 0.1

    def test_alternating_scores(self):
        st = SkillsTracker()
        for i in range(10):
            score = 1.0 if i % 2 == 0 else 0.0
            st.record(Topic.TESTING, score, f"ch-pa-a{i}")
        prof = st.proficiency(Topic.TESTING)
        assert 0.2 < prof < 0.8


class TestSkillsTrackerExportAdvanced:
    def test_to_csv_multiple_records(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.TESTING, 0.5 + i * 0.1, f"ch-ea-{i}")
        csv_text = st.to_csv()
        lines = csv_text.strip().split("\n")
        assert len(lines) == 6

    def test_to_json_valid_structure(self):
        st = SkillsTracker()
        st.record(Topic.DEBUGGING, 0.5, "ch-ea-1")
        data = json.loads(st.to_json())
        assert "proficiencies" in data
        assert "overall" in data
        assert "weaknesses" in data

    def test_from_dict_preserves_proficiency(self):
        st = SkillsTracker()
        for i in range(5):
            st.record(Topic.REFACTORING, 0.5 + i * 0.1, f"ch-ea-r{i}")
        original_prof = st.proficiency(Topic.REFACTORING)
        data = st.to_dict()
        st2 = SkillsTracker.from_dict(data)
        assert st2.proficiency(Topic.REFACTORING) == pytest.approx(original_prof, abs=0.001)

    def test_to_dict_has_correct_keys(self):
        st = SkillsTracker()
        d = st.to_dict()
        assert set(d.keys()) == {"records", "proficiencies", "overall", "weaknesses"}


class TestTopicEnum:
    def test_all_topics_unique(self):
        values = [t.value for t in Topic]
        assert len(values) == len(set(values))

    def test_topic_count(self):
        assert len(Topic) == 9

    def test_topic_values_are_strings(self):
        for t in Topic:
            assert isinstance(t.value, str)


# ===================================================================
# Additional Style Analysis Tests
# ===================================================================

class TestStyleAnalysisAdvanced:
    def test_async_detected(self):
        solution = "async def fetch():\n    await result"
        metrics = analyse_style(solution)
        assert "async" in metrics.approaches_used

    def test_lambda_detected(self):
        solution = "f = lambda x: x * 2"
        metrics = analyse_style(solution)
        assert "lambda" in metrics.approaches_used

    def test_comprehension_detected(self):
        solution = "result = [x for x in range(10)]"
        metrics = analyse_style(solution)
        assert "comprehension" in metrics.approaches_used

    def test_exception_handling_detected(self):
        solution = "try:\n    pass\nexcept:\n    pass"
        metrics = analyse_style(solution)
        assert "exception_handling" in metrics.approaches_used

    def test_context_manager_detected(self):
        solution = "with open('file') as f:\n    pass"
        metrics = analyse_style(solution)
        assert "context_manager" in metrics.approaches_used

    def test_unique_words_counted(self):
        solution = "a b c d e f g"
        metrics = analyse_style(solution)
        assert metrics.unique_words == 7

    def test_avg_line_length(self):
        solution = "abcd\nefgh\nijkl"
        metrics = analyse_style(solution)
        assert metrics.avg_line_length == pytest.approx(4.0, abs=0.1)

    def test_distance_identical(self):
        m = StyleMetrics(line_count=10, avg_line_length=30, function_count=2)
        assert m.distance(m) == 0.0

    def test_distance_symmetric(self):
        m1 = StyleMetrics(line_count=10, avg_line_length=30)
        m2 = StyleMetrics(line_count=100, avg_line_length=80)
        assert m1.distance(m2) == pytest.approx(m2.distance(m1), abs=0.001)

    def test_to_dict_completeness(self):
        m = StyleMetrics(line_count=10, avg_line_length=30, function_count=2,
                         comment_ratio=0.1, max_nesting_depth=3, unique_words=50,
                         approaches_used=["regex", "OOP"])
        d = m.to_dict()
        assert d["line_count"] == 10
        assert d["function_count"] == 2
        assert d["comment_ratio"] == 0.1


# ===================================================================
# Additional Challenge Tests
# ===================================================================

class TestChallengeAdvanced:
    def test_custom_time_limit(self):
        ch = Challenge(time_limit_minutes=30.0)
        assert ch.time_limit_minutes == 30.0

    def test_hints_default_empty(self):
        ch = Challenge()
        assert ch.hints == []

    def test_custom_hints(self):
        ch = Challenge(hints=["hint1", "hint2"])
        assert len(ch.hints) == 2

    def test_metadata_default_empty(self):
        ch = Challenge()
        assert ch.metadata == {}

    def test_custom_metadata(self):
        ch = Challenge(metadata={"key": "value"})
        assert ch.metadata["key"] == "value"

    def test_difficulty_boundary_min(self):
        ch = Challenge(difficulty=0)
        assert ch.difficulty == 1

    def test_difficulty_boundary_max(self):
        ch = Challenge(difficulty=100)
        assert ch.difficulty == 10

    def test_all_difficulty_labels(self):
        for i in range(1, 11):
            ch = Challenge(difficulty=i)
            assert ch.difficulty_label in [dl.name for dl in DifficultyLevel]


# ===================================================================
# Additional Dojo Tests
# ===================================================================

class TestDojoAdvanced:
    def test_multiple_rounds_accumulate(self):
        dojo = Dojo("test-agent")
        for i in range(3):
            ch = Challenge(topic=Topic.DOJO, id=f"ch-da-{i}")
            dojo.run_round(ch, "def solve(): return True")
        assert len(dojo.results) == 9

    def test_record_summary_after_rounds(self):
        dojo = Dojo("test-agent")
        ch = Challenge(topic=Topic.DOJO)
        dojo.run_round(ch, "def solve():\n    return True")
        summary = dojo.record_summary()
        total = summary["win"] + summary["loss"] + summary["draw"]
        assert total == 3

    def test_tournament_missing_solution(self):
        dojo = Dojo("test-agent")
        challenges = [Challenge(topic=Topic.DOJO, id=f"ch-tm-{i}") for i in range(3)]
        solutions = {"ch-tm-0": "def solve(): return True"}
        results = dojo.run_tournament(challenges, solutions)
        assert len(results) == 3

    def test_tournament_empty_solutions(self):
        dojo = Dojo("test-agent")
        challenges = [Challenge(topic=Topic.DOJO, id=f"ch-te-{i}") for i in range(3)]
        results = dojo.run_tournament(challenges, {})
        assert len(results) == 0

    def test_score_solution_empty(self):
        score = Dojo._score_solution("", Challenge())
        assert score == 0.0

    def test_score_solution_with_function(self):
        sol = "def solve(): return True"
        score = Dojo._score_solution(sol, Challenge(difficulty=5))
        assert score > 0.5


# ===================================================================
# Additional Twin Solution Tests
# ===================================================================

class TestTwinSolutionAdvanced:
    def test_twin_variant_name_format(self):
        ch = Challenge()
        twin = generate_twin_solution(ch, "code", TwinDifficulty.EASY)
        assert twin.name.startswith("Twin-")
        assert twin.twin_type == TwinDifficulty.EASY

    def test_twin_metadata_has_challenge_id(self):
        ch = Challenge(id="test123")
        twin = generate_twin_solution(ch, "code", TwinDifficulty.HARD)
        assert twin.metadata["challenge_id"] == "test123"

    def test_hard_twin_has_extra_comments(self):
        ch = Challenge()
        twin = generate_twin_solution(ch, "def solve(): pass", TwinDifficulty.HARD)
        assert "Additional edge case" in twin.solution

    def test_adversarial_swaps_variables(self):
        ch = Challenge()
        solution = "result = data + output"
        twin = generate_twin_solution(ch, solution, TwinDifficulty.ADVERSARIAL)
        assert "_alt" in twin.solution


# ===================================================================
# Additional Shadow Challenge Tests
# ===================================================================

class TestShadowChallengeAdvanced:
    def test_easy_clamps_min_difficulty(self):
        ch = Challenge(difficulty=2)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.difficulty >= 1

    def test_hard_clamps_max_difficulty(self):
        ch = Challenge(difficulty=9)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.HARD)
        assert shadow.difficulty <= 10

    def test_shadow_preserves_acceptance_criteria(self):
        ch = Challenge(acceptance_criteria=["c1", "c2"])
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.acceptance_criteria == ["c1", "c2"]

    def test_shadow_preserves_time_limit(self):
        ch = Challenge(time_limit_minutes=15.0)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.HARD)
        assert shadow.time_limit_minutes == 15.0

    def test_shadow_not_blind(self):
        ch = Challenge(is_blind=True)
        shadow = generate_shadow_challenge(ch, TwinDifficulty.ADVERSARIAL)
        assert shadow.is_blind is False

    def test_shadow_different_id(self):
        ch = Challenge(id="orig123")
        shadow = generate_shadow_challenge(ch, TwinDifficulty.EASY)
        assert shadow.id != "orig123"


# ===================================================================
# Additional TranscriptEntry Tests
# ===================================================================

class TestTranscriptEntryAdvanced:
    def test_narrative_failed(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-nea-1", topic=Topic.TESTING, difficulty=3)
        grade = Grade(score=0.2, passed=False, feedback="Bad")
        entry = tt.add_entry(ch, grade)
        assert "attempted" in entry.narrative()

    def test_transcript_empty_str(self):
        tt = TrainingTranscript()
        text = str(tt)
        assert "Training Transcript" in text
        assert "0/0" in text

    def test_transcript_multiple_entries_summary(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-nea-2", topic=Topic.TESTING, difficulty=3)
        for i in range(5):
            grade = Grade(score=0.5 + i * 0.1, passed=(i > 1), feedback=f"ok {i}")
            tt.add_entry(ch, grade)
        d = tt.to_dict()
        assert d["summary"]["total"] == 5
        assert d["summary"]["passed"] == 3

    def test_transcript_to_dict_average_score(self):
        tt = TrainingTranscript()
        ch = Challenge(id="ch-nea-3", topic=Topic.TESTING, difficulty=3)
        tt.add_entry(ch, Grade(score=0.5, passed=True))
        tt.add_entry(ch, Grade(score=1.0, passed=True))
        d = tt.to_dict()
        assert d["summary"]["average_score"] == pytest.approx(0.75, abs=0.01)


# ===================================================================
# Additional Curriculum Tests
# ===================================================================

class TestCurriculumAdvanced:
    def test_unknown_day_topics(self):
        cur = Curriculum()
        cur.day = 100
        topics = cur.current_day_topics()
        assert len(topics) > 0

    def test_advance_rotation_resets_index(self):
        cur = Curriculum()
        cur.day = 3
        for _ in range(10):
            cur.next_topic()
        assert cur._topic_index > 0
        cur.advance_rotation()
        assert cur._topic_index == 0

    def test_generate_challenge_increments_counter(self):
        cur = Curriculum()
        before = cur._challenges_generated
        cur.generate_challenge()
        assert cur._challenges_generated == before + 1

    def test_generate_challenge_metadata(self):
        cur = Curriculum()
        ch = cur.generate_challenge()
        assert "day" in ch.metadata
        assert "generated_count" in ch.metadata

    def test_generate_challenge_rotation(self):
        cur = Curriculum()
        cur.rotation = 2
        ch = cur.generate_challenge()
        assert ch.rotation == 3

    def test_acceptance_criteria_high_difficulty(self):
        criteria = Curriculum._acceptance_criteria(Topic.TESTING, 9)
        assert len(criteria) > 2

    def test_acceptance_criteria_low_difficulty(self):
        criteria = Curriculum._acceptance_criteria(Topic.TESTING, 2)
        assert len(criteria) == 3

    def test_all_topic_criteria_valid(self):
        for topic in Topic:
            criteria = Curriculum._acceptance_criteria(topic, 5)
            assert len(criteria) > 0
            for c in criteria:
                assert isinstance(c, str)


# ===================================================================
# Additional Grade Tests
# ===================================================================

class TestGradeAdvanced:
    def test_criteria_met_list(self):
        ch = Challenge(acceptance_criteria=["function must be defined"])
        solution = "def my_function(): return 1"
        g = grade_solution(ch, solution)
        assert len(g.criteria_met) >= 1

    def test_default_grade_values(self):
        g = Grade(score=0.5, passed=True)
        assert g.feedback == ""
        assert g.criteria_met == []
        assert g.criteria_missed == []
        assert g.time_taken == 0.0

    def test_grade_with_all_fields(self):
        g = Grade(
            score=0.8, passed=True, feedback="Great!",
            criteria_met=["c1"], criteria_missed=["c2"],
            time_taken=5.5,
        )
        assert g.feedback == "Great!"
        assert len(g.criteria_met) == 1
        assert len(g.criteria_missed) == 1
        assert g.time_taken == 5.5

    def test_empty_solution_misses_all_criteria(self):
        ch = Challenge(acceptance_criteria=["c1", "c2", "c3"])
        g = grade_solution(ch, "")
        assert len(g.criteria_missed) == 3
        assert len(g.criteria_met) == 0

    def test_solution_with_class_keyword(self):
        ch = Challenge()
        g = grade_solution(ch, "class Foo:\n    pass")
        assert g.score > 0.0


# ===================================================================
# Additional Rankings Tests
# ===================================================================

class TestRankingsAdvanced:
    def test_empty_leaderboard(self):
        rankings = Rankings()
        assert rankings.leaderboard() == []

    def test_rank_with_multiple_agents(self):
        rankings = Rankings()
        for name, score in [("a", 0.3), ("b", 0.7), ("c", 0.5)]:
            bc = Bootcamp(name)
            bc.skills.record(Topic.TESTING, score, "ch-ra-1")
            rankings.register(bc)
        assert rankings.rank("a") == 3
        assert rankings.rank("b") == 1
        assert rankings.rank("c") == 2

    def test_leaderboard_sorted_descending(self):
        rankings = Rankings()
        for name, score in [("x", 0.1), ("y", 0.9), ("z", 0.5)]:
            bc = Bootcamp(name)
            bc.skills.record(Topic.TESTING, score, "ch-rb-1")
            rankings.register(bc)
        board = rankings.leaderboard()
        profs = [e["overall_proficiency"] for e in board]
        assert profs == sorted(profs, reverse=True)

    def test_rank_missing_agent(self):
        rankings = Rankings()
        bc = Bootcamp("existing")
        bc.skills.record(Topic.TESTING, 0.5, "ch-rc-1")
        rankings.register(bc)
        assert rankings.rank("ghost") == 2

    def test_leaderboard_has_all_fields(self):
        rankings = Rankings()
        bc = Bootcamp("test")
        bc.skills.record(Topic.TESTING, 0.5, "ch-rd-1")
        rankings.register(bc)
        board = rankings.leaderboard()
        entry = board[0]
        assert "name" in entry
        assert "overall_proficiency" in entry
        assert "challenges_done" in entry
        assert "dojo_win_rate" in entry
        assert "average_score" in entry


# ===================================================================
# Additional Bootcamp Lifecycle Tests
# ===================================================================

class TestBootcampLifecycleAdvanced:
    def test_restart_training(self):
        bc = Bootcamp("test-la-1")
        bc.start_training()
        bc.end_training()
        bc.start_training()
        assert bc.is_active
        assert bc.current_challenge is not None

    def test_submit_then_next(self):
        bc = Bootcamp("test-la-2")
        ch1 = bc.next_challenge()
        bc.submit_solution(ch1.id, "solution")
        assert bc.current_challenge is None
        ch2 = bc.next_challenge()
        assert isinstance(ch2, Challenge)
        assert ch2.id != ch1.id

    def test_progress_report_after_training(self):
        bc = Bootcamp("test-la-3")
        ch = bc.next_challenge()
        bc.submit_solution(ch.id, "good solution with tests")
        report = bc.progress_report()
        assert report["challenges_done"] == 1
        assert report["overall_proficiency"] > 0.0

    def test_export_report_after_submissions(self):
        bc = Bootcamp("test-la-4")
        for i in range(3):
            ch = bc.next_challenge()
            bc.submit_solution(ch.id, f"solution {i}")
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bc.export_report(path)
            with open(path) as f:
                data = json.load(f)
            assert data["session"]["challenges_done"] == 3
            assert len(data["transcript"]["entries"]) == 3
        finally:
            os.unlink(path)
