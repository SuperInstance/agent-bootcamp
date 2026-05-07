"""Spiral-difficulty challenge system for git-agents."""
import random
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChallengeResult:
    skill: str
    passed: bool
    attempts: int

class SpiralChallenge:
    """Adapts difficulty based on agent weaknesses."""
    
    DIFFICULTY_LEVELS = ["rookie", "deckhand", "mate", "captain"]
    
    def __init__(self):
        self.weaknesses: dict[str, int] = {}
        self.current_level = 0
    
    def assess(self, results: list[ChallengeResult]) -> int:
        """Analyze past failures to target weak areas."""
        for r in results:
            self.weaknesses[r.skill] = self.weaknesses.get(r.skill, 0) + (0 if r.passed else 1)
        
        weakest = max(self.weaknesses, key=self.weaknesses.get, default="navigation")
        self.current_level = min(3, self.weaknesses.get(weakest, 0) // 2)
        return self.current_level
    
    def generate(self) -> dict:
        """Generate a challenge at current spiral level."""
        level = self.DIFFICULTY_LEVELS[self.current_level]
        templates = {
            "rookie": ["Navigate to repo", "Read a file", "Commit a change"],
            "deckhand": ["Merge conflict", "Rebase safely", "Cherry-pick"],
            "mate": ["Bisect a bug", "Interactive rebase", "Partial stash"],
            "captain": ["Multi-branch strategy", "Hotfix protocol", "Release tagging"],
        }
        return {"level": level, "task": random.choice(templates[level])}

if __name__ == "__main__":
    ch = SpiralChallenge()
    results = [ChallengeResult("merge", False, 2), ChallengeResult("merge", False, 1)]
    level = ch.assess(results)
    print(f"Adapted level: {level} ({ch.DIFFICULTY_LEVELS[level]})")
    challenge = ch.generate()
    print(f"Challenge: {challenge}")