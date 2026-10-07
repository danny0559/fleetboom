"""UI-independent round timing, energy, scoring and shockwave state."""
from dataclasses import dataclass, field
from .config import COSTS, DURATION


@dataclass
class RoundState:
    elapsed: float = 0.0
    energy: float = 70.0
    score: int = 0
    kills: int = 0
    best_chain: int = 0
    ended: bool = False
    chains: dict = field(default_factory=dict)
    next_chain: int = 0

    @property
    def remaining(self):
        return max(0.0, DURATION-self.elapsed)

    @property
    def phase(self):
        return 4 if self.elapsed >= 75 else int(self.elapsed//20)

    def advance(self, dt):
        if self.ended:
            return
        dt = max(0.0, min(dt, self.remaining))
        self.elapsed += dt
        self.energy = min(100.0, self.energy+dt*.6)
        self.ended = self.elapsed >= DURATION

    def spend(self, tool):
        cost = COSTS[tool]
        if self.ended or self.energy < cost:
            return False
        self.energy -= cost
        return True

    def kill(self, chain=None):
        if self.ended:
            return None
        if chain is None:
            self.next_chain += 1
            chain = self.next_chain
        count = self.chains.get(chain, 0)+1
        self.chains[chain] = count
        awarded = 100+50*min(count-1, 14)
        self.score += awarded
        self.kills += 1
        self.best_chain = max(self.best_chain, count)
        self.energy = min(100.0, self.energy+7+2*min(count-1, 5))
        return chain, count, awarded


@dataclass
class Shockwave:
    x: float
    y: float
    chain: int
    age: float = 0.0
    radius: float = 108.0
    life: float = .5
    items: tuple = ()
