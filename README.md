# agent-bootcamp

Spiral-difficulty challenge framework for training git-agents.

## Concept

Agents face progressively harder challenges targeting their specific weaknesses. The spiral design ensures no skill is left behind.

## Usage

```bash
python src/challenge.py
```

Example output:
```
Adapted level: 2 (mate)
Challenge: {'level': 'mate', 'task': 'Bisect a bug'}
```

## Levels

| Level | Title | Example Tasks |
|-------|-------|---------------|
| 0 | Rookie | Navigate, read, commit |
| 1 | Deckhand | Merge, rebase, cherry-pick |
| 2 | Mate | Bisect, interactive rebase, partial stash |
| 3 | Captain | Multi-branch, hotfix, releases |

Run multiple times to watch the spiral adapt to simulated failures.