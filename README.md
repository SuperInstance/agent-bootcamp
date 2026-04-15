# Agent Bootcamp — Spiral Training for Git-Agents

> *Part of the Cocapn Fleet · Git-Agent Standard v2.0 Compliant*
> *Captain: Casey Digennaro (SuperInstance) · Maintainer: Oracle1 (Lighthouse Keeper)*

---

## Overview

**Agent Bootcamp** is a spiral-based training system that transforms git-agents from prompted novices into genuinely skilled operatives. Unlike conventional approaches that rely on static system prompts ("you are good at X"), this bootcamp forces agents to **build, test, and refine their own application code** — producing real skills rather than wishful descriptions.

The system is a vessel in the **Cocapn fleet**, designed to be pointed at any git repository. It scans the project for weaknesses, generates adaptive challenges that escalate in difficulty, and maintains a full training transcript. Agents learn by doing: writing tests, debugging broken code, refactoring complexity, estimating task duration, and sparring against shadow variants of themselves in the Dojo.

### Core Philosophy

```
System prompt: "You are good at estimating task duration"
                    ↓ vs ↓
Bootcamp skill: task_estimator.py — 200 iterations of calibration against real data
```

A system prompt is a wish. A real skill is **code the agent has written, tested, and refined** that makes a task faster and more reliable. The bootcamp's sole purpose is to create the pressure that forces the agent to build that code.

### Key Capabilities

- **Spiral curriculum** — topics rotate with escalating difficulty; the spiral tightens as the agent improves
- **Adaptive challenge generation** — challenges are synthesized from actual project weak spots (untested functions, dead code, missing error handling)
- **Blind testing** — agents submit work without seeing acceptance criteria or verification results, proving genuine competence
- **Dojo sparring** — agents fight shadow variants (easy, hard, adversarial) of their own solutions
- **Task estimation engine** — agents build their own calibration tools, learning to predict duration from experience
- **Multi-agent rankings** — leaderboards track proficiency across the entire fleet
- **Full training transcripts** — commit-narrative style logs capture every challenge, grade, and growth milestone

---

## Repository Structure

```
agent-bootcamp/
├── bootcamp.py          # Core training engine (lifecycle, grading, transcripts, rankings)
├── curriculum.py        # Challenge generation, topic pools, spiral difficulty, adaptive logic
├── dojo.py              # Sparring system (shadow challenges, style analysis, tournaments)
├── skills.py            # Skills tracking (proficiency EMA, weakness detection, plateaus, export)
├── cli.py               # CLI interface (enroll, start, challenge, submit, progress, report, dojo, rank)
├── tests/
│   └── test_bootcamp.py # Comprehensive test suite (1200+ lines, 90+ test cases)
├── pyproject.toml       # Python project config (v0.1.0, Python ≥3.10)
├── CHARTER.md           # Fleet charter (mission, captain, maintainer)
├── STATE.md             # Operational status tracking
├── DOCKSIDE-EXAM.md     # Fleet certification checklist (7/7 seaworthy standard)
├── BOOTCAMP.md          # Original bootcamp design document
├── LICENSE              # License
├── callsign1.jpg        # Vessel callsign
└── README.md            # This file
```

---

## Curriculum & Training Phases

The bootcamp progresses through **5+ days** of structured training, with each day introducing more complex challenges. After the initial phases, the spiral continues indefinitely with escalating difficulty.

### Phase 1 — Day 1: Reconnaissance (Know Your Project)

The agent reads the project it has been assigned to. It maps every file, every function, every dependency. The challenge: find 3 things that could break. Write them up. No code yet — just understanding.

**Difficulty range:** BEGINNER (1) → EASY (2)

| Level | Challenge Example |
|-------|------------------|
| 1 | Map all Python files and list their public functions |
| 2 | Analyse the dependency graph; identify which modules import which |
| 3 | Identify 3 areas of highest risk in the codebase |
| 4 | Create a full project map: files, functions, call-graph, dependencies |
| 5 | Write a risk assessment report ranking every module by fragility score |

### Phase 2 — Day 2: First Challenges (Easy Wins)

Simple tasks in the project's domain. Fix a typo. Add a missing test. Write a docstring. The agent succeeds easily. Confidence builds. **This is the setup.**

**Difficulty range:** BEGINNER (1) → MODERATE (4)

| Level | Challenge Example |
|-------|------------------|
| 1 | Fix a typo in a user-facing string or error message |
| 2 | Add a missing docstring to an exported function |
| 3 | Write a single passing test for an untested utility function |
| 4 | Fix an inconsistent naming convention in a module |
| 5 | Add type hints to an untyped function |

### Phase 3 — Day 3: The Spiral Begins (Topic Rotation)

Challenges rotate through five core topics. Each rotation is harder than the last.

- **Testing** — Write tests for code you didn't write
- **Documentation** — Explain code to someone who's never seen it
- **Refactoring** — Make code smaller without changing behavior
- **Integration** — Connect two parts that don't talk yet
- **Debugging** — Find the bug in intentionally broken code

### Phase 4 — Day 4: The Shift (Your Code Is Not Enough)

Tasks now require something the agent hasn't built yet: **estimation**. Tasks come with time limits. The agent must predict how long something will take. If wrong, it wastes cycles. If right, it gets harder challenges.

The agent MUST write its own `task_estimator.py` during this phase — a calibration tool that improves with each iteration.

### Phase 5 — Day 5: Dojo (Fight Yourself)

The agent faces **shadow variants** of itself:

| Challenger | Type | Behavior |
|-----------|------|----------|
| Twin-EASY | Simplified | Same topic, difficulty -2, shortened solution |
| Twin-HARD | Extended | Same topic, difficulty +2, additional edge cases |
| Twin-ADVERSARIAL | Deceptive | Same difficulty, swapped variables, misleading description prefix |

All get the same challenge. The agent must:
1. Complete the task itself
2. Evaluate all 3 shadow submissions
3. Pick the best one
4. Explain WHY it's best
5. Integrate any good ideas from the others

### Phase 6+: Continuous Spiral (Never Stop Learning)

The spiral continues with escalating difficulty. New challenges are generated from the project's actual weak spots — test coverage gaps, undocumented functions, missing error handling, dead code paths.

> **The key rule:** as soon as the cadet thinks it's smart, the challenges shift. The bootcamp keeps the agent at the edge of its ability.

---

## Difficulty Scale

Challenges are rated on a 10-level scale from BEGINNER to IMPOSSIBLE:

| Level | Name | Description |
|-------|------|-------------|
| 1 | BEGINNER | Simple identification tasks, basic fixes |
| 2 | EASY | Single-function changes, basic tests |
| 3 | MEDIUM | Multi-step tasks, edge case coverage |
| 4 | MODERATE | Cross-module awareness required |
| 5 | HARD | Architectural thinking, trade-off analysis |
| 6 | EXPERT | System design, complex refactoring |
| 7 | MASTER | **Blind mode enabled** — no acceptance criteria shown |
| 8 | GRANDMASTER | Blind + error handling + documentation required |
| 9 | NIGHTMARE | Full redesign, adversarial specifications |
| 10 | IMPOSSIBLE | Security audits, reverse-engineering corrupted data |

---

## How to Enroll & Participate

### Prerequisites

- Python 3.10+
- A target git repository to train against (optional but recommended)
- No external dependencies required (stdlib only)

### Installation

```bash
# Clone the bootcamp
git clone <fleet-repo>/agent-bootcamp.git
cd agent-bootcamp

# Run tests to verify
python -m pytest tests/ -v
```

### Quick Start — CLI Workflow

The CLI (`cli.py`) provides all bootcamp operations:

```bash
# 1. Enroll a new agent
python3 cli.py enroll navigator --project-path /path/to/target-repo

# 2. Start training session
python3 cli.py start navigator

# 3. View current challenge
python3 cli.py challenge navigator

# 4. Submit a solution (from file or inline)
python3 cli.py submit navigator <challenge-id> --solution-file solution.py
python3 cli.py submit navigator <challenge-id> --solution-text "def solve(): ..."

# 5. Check progress
python3 cli.py progress navigator

# 6. Enter dojo sparring
python3 cli.py dojo navigator --solution-file solution.py

# 7. Generate full training report
python3 cli.py report navigator --output report.json

# 8. View fleet rankings
python3 cli.py rank
```

### Programmatic Usage

```python
from bootcamp import Bootcamp, Rankings

# Create and start a bootcamp
bc = Bootcamp(agent_name="navigator", project_path="/path/to/repo")
bc.start_training()

# Training loop
challenge = bc.current_challenge
grade = bc.submit_solution(challenge.id, solution_code)

# Assess and adapt
weaknesses = bc.assess_weaknesses()
next_challenges = bc.generate_curriculum(count=20)  # adaptive to weaknesses

# Export results
bc.export_report("training_report.json")
bc.end_training()
```

### Persistence

Agent state is persisted to `~/.agent-bootcamp/<agent_name>.json`. This includes skills data, curriculum progress, transcript entries, and dojo results. Agents can resume training across sessions.

---

## Exercises and Challenges

### Challenge Topics (9 Domains)

| Topic | Description | Sample Challenges |
|-------|------------|-------------------|
| **Reconnaissance** | Project mapping, dependency analysis, risk assessment | "Build a visual dependency graph and identify circular dependencies" |
| **First Wins** | Quick fixes, docstrings, basic improvements | "Replace a magic number with a named constant" |
| **Testing** | Unit tests, edge cases, property-based, mutation-resistant | "Write mutation-testing-resistant tests for a pure function" |
| **Documentation** | Docstrings, tutorials, ADRs, architecture docs | "Write an architecture decision record for a design choice" |
| **Refactoring** | DRY, SOLID, design patterns, type safety | "Introduce a strategy pattern to eliminate type-checking conditionals" |
| **Integration** | Adapters, facades, event buses, plugin systems | "Implement a plugin system without modifying core code" |
| **Debugging** | Logic errors, resource leaks, race conditions, Heisenbugs | "Debug a Heisenbug that only appears under specific timing conditions" |
| **Estimation** | Duration prediction, complexity analysis, Bayesian calibration | "Build a Bayesian estimator that updates as new data arrives" |
| **Dojo** | Self-sparring, peer review, code golf, adversarial specs | "Given a deliberately adversarial specification, find the traps" |

### Challenge Generation Engine

Challenges are not static — they are **synthesized from the actual project's weak spots**:

```python
class ChallengeGenerator:
    """Generates challenges from real project weak spots."""

    def scan_project(self, repo_path: str) -> list[WeakSpot]:
        """Find areas that need work."""
        weak_spots = []
        weak_spots.append(self.find_untested_functions(repo_path))
        weak_spots.append(self.find_undocumented_code(repo_path))
        weak_spots.append(self.find_long_functions(repo_path))
        weak_spots.append(self.find_missing_error_handling(repo_path))
        weak_spots.append(self.find_dead_code(repo_path))
        return weak_spots

    def generate_challenge(self, weak_spot: WeakSpot, difficulty: int) -> Challenge:
        """Create a challenge targeting a specific weak spot."""
        # difficulty 1-10, spiral adjusts based on performance
        return Challenge(
            target=weak_spot,
            task=self.format_task(weak_spot, difficulty),
            time_limit=self.estimate_time(difficulty),
            verification=self.create_verification(weak_spot),
        )
```

Difficulty scales challenge complexity:

| Difficulty | Task Format |
|-----------|-------------|
| ≤ 3 | `Add a test for {function_name}` |
| ≤ 6 | `Refactor {function_name} to be testable, then test it` |
| > 6 | `Redesign the {module} module — {function_name} has grown too complex. Split it, test each part, maintain backward compatibility.` |

---

## Assessment and Certification

### Grading System

Every submission is graded on a 0.0–1.0 scale with letter grades:

| Grade | Score Range | Meaning |
|-------|------------|---------|
| A | 90–100% | Exceptional — exceeds all criteria |
| B | 80–89% | Strong — meets all criteria with minor gaps |
| C | 70–79% | Adequate — meets most criteria |
| D | 50–69% | Below standard — significant gaps |
| F | 0–49% | Failing — does not meet minimum requirements |

Grading considers: acceptance criteria coverage, solution quality (function definitions, error handling, tests), time performance (bonus for under-limit, penalty for overtime), and blind challenge bonuses.

### Skill Proficiency Tracking

Proficiency is tracked per topic using an **Exponential Moving Average (EMA)** with α=0.3, meaning recent performance matters more than historical data. Proficiency ranges from 0.0 (no data) to 1.0 (mastery).

The system detects:
- **Weaknesses** — topics with proficiency < 0.5 OR 3+ consecutive failures
- **Plateaus** — topics where the average score hasn't changed across two windows of attempts
- **Mastery** — topics with proficiency > 0.8 (these are deprioritized in adaptive curriculum)

### Graduation Criteria

An agent graduates bootcamp when it meets **all six** criteria:

1. **Task estimator calibrated** — within 20% of actual time, 80% of the time
2. **Zero-shot on novel challenges** — can handle tasks it hasn't seen before
3. **Dojo wins >50%** — beats its own shadow variants at least half the time
4. **Blind test pass rate >80%** — delivers working code without seeing the test
5. **Has written its own tools** — task_estimator.py, challenge_generator.py, etc.
6. **Diary shows growth** — each day's transcript entry shows genuine learning

### Training Transcripts

Every challenge generates a structured transcript entry:

```
[2026-04-14T10:30:00Z] completed testing challenge (difficulty 3) [B] 82% —
  Met: All tests must pass, Tests must cover edge cases
```

Transcripts export to JSON with full summaries (total challenges, pass rate, average score).

### Dockside Exam (Fleet Certification)

The vessel undergoes a **7-point dockside exam** evaluating:

| Category | Checks |
|----------|--------|
| Identity | CHARTER.md, README.md, License |
| Code Quality | Compiles/runs, no secrets, documented deps |
| Testing | Test suite exists, passes, edge cases covered |
| Fleet Integration | Git-Agent Standard v2.0, I2I protocol, STATE.md |
| Documentation | API docs, configuration, examples |
| Safety | No destructive ops without confirmation, error handling, graceful degradation |
| Operational | Independent deployment, health checks, logging ready |

**Scoring:** 7/7 = Seaworthy 🟢 · 5-6/7 = Conditional 🟡 · <5/7 = Needs Work ⚠️

---

## Fleet Integration

### Git-Agent Standard v2.0 Compliance

This bootcamp is itself a git-agent, compliant with the Git-Agent Standard v2.0:

- **CHARTER.md** — declares mission, type (vessel), captain, and maintainer
- **STATE.md** — tracks operational status (Active, Health: Operational)
- **DOCKSIDE-EXAM.md** — fleet certification checklist for seaworthiness
- **I2I Protocol** — inter-instance communication compatible

### Multi-Agent Banter Protocol

When multiple agents are training simultaneously, the estimation engine creates **natural rhythms** — agents don't all check in at once. The `BanterScheduler`:

- Schedules check-ins at 50% and 100% of estimated task duration
- Triggers notifications on peer completion or error detection
- Adds random delays (0.5–2.0 minutes) to prevent thundering-herd effects

### Fleet Rankings

The `Rankings` class tracks and compares all enrolled agents:

```
Leaderboard:
  Rank  Agent                          Proficiency     Challenges  Dojo WR
  ------------------------------------ --------------- ----------- --------
  1     navigator                      78.5%           42          66.7%
  2     pathfinder                     65.2%           38          55.0%
  3     sentinel                       52.1%           35          44.4%
```

### The Blind Test Protocol

The ultimate assessment: an agent completes a task and doesn't know if it worked. Verification happens asynchronously:

1. The tender visits (next sync)
2. A dependent agent tries to use the output
3. CI runs (if connected)
4. The orchestrator checks on a heartbeat

> This is how you know if a skill is REAL — when the agent can't see the answer key.

### Orchestrator's Role

The orchestrator (human or managing agent) doesn't micromanage. It:
1. **Sets up the bootcamp** — points at a project, defines difficulty curve
2. **Adds application code** — builds challenge generators, estimators, dojo
3. **Watches the spiral** — adjusts difficulty when the agent plateaus or struggles
4. **Triggers shifts** — when the cadet gets comfortable, shifts the challenge type
5. **Manages cron cycles** — uses the estimator to not waste compute on idle agents
6. **Sets up blind tests** — verifies work without the agent seeing the answer key

---

## Task Estimation Engine

Agents build this during bootcamp. It calibrates from experience:

```python
class TaskEstimator:
    """Learns to estimate task duration from experience."""

    def __init__(self):
        self.history = []  # (description, estimated, actual, context)
        self.calibration = 1.0  # adjusts over time

    def estimate(self, task: str, context: dict) -> Estimate:
        """Predict how long a task will take."""
        similar = self.find_similar(task, context)
        if similar:
            base = statistics.median([s.actual for s in similar])
        else:
            base = 10  # default 10 minutes for unknown

        # Context multipliers
        multiplier = 1.0
        if context.get("unfamiliar_code"):
            multiplier *= 1.5
        if context.get("cross_language"):
            multiplier *= 2.0
        if context.get("has_tests_to_fix"):
            multiplier *= 1.3

        estimated = base * multiplier * self.calibration
        confidence = len(similar) / 10
        return Estimate(minutes=estimated, confidence=min(confidence, 0.95))

    def calibrate(self, task: str, estimated: float, actual: float):
        """Learn from each completed task."""
        self.history.append((task, estimated, actual))
        if actual > estimated:
            self.calibration *= 1.05  # estimate higher next time
        else:
            self.calibration *= 0.97  # estimate lower next time
        self.calibration = max(0.5, min(2.0, self.calibration))
```

---

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Specific module tests
python -m pytest tests/test_bootcamp.py::TestSkillsTracker -v
python -m pytest tests/test_bootcamp.py::TestCurriculumAdaptive -v
python -m pytest tests/test_bootcamp.py::TestDojo -v

# With coverage
python -m pytest tests/ --tb=short -q
```

The test suite covers skills tracking, curriculum generation, dojo sparring, bootcamp lifecycle, grading logic, CLI parsing, and full integration cycles — over 90 test cases.

---

## License

See [LICENSE](LICENSE) for details.

---

## Acknowledgments

*Part of the Git-Agent Standard v2.0*
*Agent builds its own skills. Bootcamp just provides the pressure.*

---

<img src="callsign1.jpg" width="128" alt="callsign">
