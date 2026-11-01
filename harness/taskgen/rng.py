"""A tiny deterministic random-number generator built on SHA-256.

Why not `random.Random`? Its seeding is stable today, but Python does not promise that `shuffle`,
`randrange` or `sample` keep the same algorithm across versions. A frozen, pre-registered task set
must regenerate byte-for-byte on any machine, so every draw here comes from SHA-256 in counter mode,
which never changes.

Seeds are strings or ints. Sub-streams are derived by name (`rng.child("rulebook")`), never by
`seed + idx`, so neighbouring items share nothing.
"""

from __future__ import annotations

import hashlib
from typing import List, Sequence, TypeVar

T = TypeVar("T")


def derive_seed(*parts: object) -> int:
    """Hash any parts into a 63-bit seed. `derive_seed("main", 7)` is unrelated to `derive_seed("main", 8)`."""
    text = "\x1f".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big") >> 1


class HashRNG:
    def __init__(self, seed: object):
        self._key = str(seed).encode()
        self._counter = 0
        self._pool = 0
        self._bits = 0

    def child(self, name: str) -> "HashRNG":
        """An independent stream for one purpose (rulebook, start values, ...)."""
        return HashRNG(hashlib.sha256(self._key + b"/" + name.encode()).hexdigest())

    def _refill(self) -> None:
        block = hashlib.sha256(self._key + b"#" + str(self._counter).encode()).digest()
        self._counter += 1
        self._pool = (self._pool << 256) | int.from_bytes(block, "big")
        self._bits += 256

    def getrandbits(self, k: int) -> int:
        while self._bits < k:
            self._refill()
        self._bits -= k
        out = self._pool >> self._bits
        self._pool &= (1 << self._bits) - 1
        return out

    def randbelow(self, n: int) -> int:
        """Uniform integer in [0, n), by rejection sampling (no modulo bias)."""
        if n <= 0:
            raise ValueError("n must be positive")
        k = n.bit_length()
        while True:
            r = self.getrandbits(k)
            if r < n:
                return r

    def randint(self, lo: int, hi: int) -> int:
        """Uniform integer in [lo, hi], both ends included."""
        return lo + self.randbelow(hi - lo + 1)

    def choice(self, seq: Sequence[T]) -> T:
        return seq[self.randbelow(len(seq))]

    def shuffled(self, seq: Sequence[T]) -> List[T]:
        """Fisher-Yates; returns a new list."""
        out = list(seq)
        for i in range(len(out) - 1, 0, -1):
            j = self.randbelow(i + 1)
            out[i], out[j] = out[j], out[i]
        return out
