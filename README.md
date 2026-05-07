# Agent Bootcamp

**Spiral-difficulty challenge framework for training git-agents.**

![Status](https://img.shields.io/badge/Status-Functional-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10+-blue)

Agents learn by doing. Bootcamp throws agents into progressively harder challenges, then adapts the spiral based on where they fail — so the hardest problems get revisited until they're mastered.

---

## Key Features

- **Spiral Difficulty Scaling** — Challenges start at rookie level and spiral up (deckhand → mate → captain) based on tracked weaknesses
- **Weakness-Targeted Adaptation** — Each agent's failure history shapes their next challenge; repeated failures at a skill push that skill higher in the queue
- **Simulated Failure Feedback** — `ChallengeResult` captures pass/fail, attempts, and skill category for post-run analysis
- **4-Tier Difficulty Ladder** — Rookie, Deckhand, Mate, Captain; each tier has 3 challenge templates
- **Lightweight & Standalone** — Single `src/challenge.py`, no external dependencies beyond stdlib

---

## Usage

```bash
python src/challenge.py
```

```
Adapted level: 2 (mate)
Challenge: {'level': 'mate', 'task': 'Bisect a bug'}
```

### API Example

```python
from challenge import SpiralChallenge, ChallengeResult

ch = SpiralChallenge()

# Simulate agent failing merge twice, navigation once
results = [
    ChallengeResult("merge", False, 2),
    ChallengeResult("merge", False, 1),
    ChallengeResult("navigation", True, 1),
]

level = ch.assess(results)      # Returns 2 (mate — merge is weakest)
challenge = ch.generate()        # {'level': 'mate', 'task': 'Bisect a bug'}
print(challenge)
```

### Running Multiple Iterations

Each run re-assesses and generates a new challenge. Watch the spiral adapt:

```bash
for i in {1..5}; do python src/challenge.py; echo "---"; done
```

---

## Difficulty Levels

| Level | Title | Example Tasks |
|-------|-------|---------------|
| 0 | **Rookie** | Navigate to repo, Read a file, Commit a change |
| 1 | **Deckhand** | Merge conflict, Rebase safely, Cherry-pick |
| 2 | **Mate** | Bisect a bug, Interactive rebase, Partial stash |
| 3 | **Captain** | Multi-branch strategy, Hotfix protocol, Release tagging |

The spiral algorithm: failures in a skill → that skill gets elevated to the next difficulty tier on the next run. A weak agent doing "mate" level tasks gets recycled back through easier challenges targeting the same weakness.

---

## Architecture

```
src/
└── challenge.py
    ├── SpiralChallenge
    │   ├── weaknesses: dict[str, int]     # skill -> failure count
    │   ├── current_level: int              # 0-3
    │   ├── assess(results) -> int          # recomputes weakest, returns level
    │   └── generate() -> dict             # {'level': str, 'task': str}
    │
    └── ChallengeResult (dataclass)
        ├── skill: str
        ├── passed: bool
        └── attempts: int
```

The `assess()` method is the spiral core: it tallies failures per skill, finds the weakest, and sets `current_level = min(3, weakness_count // 2)`. An agent with 4 merge failures gets level 2; 2 merge failures gets level 1.

---

## Related Repos

- [fleet-agent](https://github.com/SuperInstance/fleet-agent) — Fleet orchestration that agents plug into
- [superinstance](https://github.com/SuperInstance/superinstance) — Agent collective framework
- [agent-forge](https://github.com/SuperInstance/agent-forge) — Agent onboarding and task assignment
