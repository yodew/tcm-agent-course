"""Bounded metrics and process-local admission control; no patient labels."""

import time
from collections import deque
from dataclasses import dataclass, field

from prometheus_client import CollectorRegistry, Counter, Histogram

from tcm_agent.errors import AgentError


@dataclass(frozen=True, slots=True)
class RateLimiter:
    """Mutable per-process limiter; use a shared gateway for a multi-worker fleet."""

    limit: int
    windows: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, owner: str) -> None:
        """Owner comes from a bounded configured token map, never user input."""
        now = time.monotonic()
        window = self.windows.setdefault(owner, deque())
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= self.limit:
            raise AgentError("rate_limited", 429)
        window.append(now)


@dataclass(frozen=True, slots=True)
class Metrics:
    registry: CollectorRegistry
    turns: Counter
    duration: Histogram
    tokens: Counter

    @classmethod
    def create(cls) -> "Metrics":
        """A registry per app prevents tests and reloads from double-registering."""
        registry = CollectorRegistry()
        return cls(
            registry,
            Counter("tcm_turns", "Completed turns", ["status", "action"], registry=registry),
            Histogram("tcm_turn_seconds", "Full turn latency", registry=registry),
            Counter(
                "tcm_model_tokens",
                "Provider reported token totals",
                ["direction"],
                registry=registry,
            ),
        )
