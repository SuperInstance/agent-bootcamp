# Agent Bootcamp

**Spiral training for git-agents. Force agents to build real skills, not just describe them.**

A system prompt is a wish. "You are good at estimating task duration" — prove it. Build a `task_estimator.py`, calibrate it against 200 iterations of real data, and let the next agent inherit it.

That's what the bootcamp does. It scans a project for weak spots — untested functions, dead code, missing error handling — and generates adaptive challenges that escalate in difficulty. Agents learn by doing: writing tests, debugging broken code, refactoring complexity, estimating task duration, and sparring against shadow variants of themselves.

---

## How It Works

```
System prompt: "You are good at estimating task duration"
                    ↓ vs ↓
Bootcamp skill: task_estimator.py — 200 iterations of calibration against real data
```

The bootcamp's sole purpose is to create the pressure that forces the agent to build real code.

**Spiral curriculum** — topics rotate with escalating difficulty. The spiral tightens as the agent improves. Early rounds cover basic testing and linting. Later rounds cover property-based fuzzing, adversarial evaluation, and runtime performance analysis.

**Adaptive challenge generation** — challenges are synthesized from actual project weak spots. If a function has no tests, the bootcamp detects it and generates a challenge around it. If error paths aren't covered, the bootcamp surfaces them.

**Blind testing** — agents submit work without seeing acceptance criteria or verification results. This proves genuine competence, not pattern-matching against expected outputs.

**Dojo sparring** — agents fight shadow variants (easy, hard, adversarial) of their own solutions. If you wrote a slow sort, the adversarial shadow exploits it. You learn to defend against yourself.

**Task estimation engine** — agents build their own calibration tools. Over 200+ iterations, the agent learns how long tasks actually take — and the estimate error converges to zero.

---

## Key Capabilities

- Scans any git repo for weak spots (untested functions, dead code, error gaps)
- Generates challenges that escalate in 5+ difficulty stages
- Maintains a full training transcript and skill inventory
- Issues skill badges that the fleet recognizes
- Supports both individual and team training scenarios

---

## How It Fits

- **[agent-bootcamp](https://github.com/SuperInstance/agent-bootcamp)** — skill acquisition (this)
- **[arena-combat-analyst-1](https://github.com/SuperInstance/arena-combat-analyst-1)** — fleet-wide competition
- **[agent-skills](https://github.com/SuperInstance/agent-skills)** — skills that survive bootcamp
- **[baton-skill](https://github.com/SuperInstance/baton-skill)** — handoff preserving skill state
- **[bootstrap-spark](https://github.com/SuperInstance/bootstrap-spark)** — onboarding that triggers bootcamp
- **[casting-call](https://github.com/SuperInstance/casting-call)** — which model learns best from which training

---

## License

MIT
