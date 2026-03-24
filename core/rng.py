"""Deterministic RNG for reproducible game sessions."""

import random
from typing import Any, List


class Rng:
    """Deterministic random number generator with seed."""

    def __init__(self, seed: int):
        self._r = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        """Random integer in range [a, b]."""
        return self._r.randint(a, b)

    def random(self) -> float:
        """Random float in [0.0, 1.0)."""
        return self._r.random()

    def gauss(self, mu: float, sigma: float) -> float:
        """Gaussian random number."""
        return self._r.gauss(mu, sigma)

    def choice(self, xs: List[Any]) -> Any:
        """Choose random element from list."""
        return self._r.choice(xs)

    def shuffle(self, xs: List[Any]) -> None:
        """Shuffle list in place."""
        self._r.shuffle(xs)

