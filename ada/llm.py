"""Structured-output calls to Claude, with cost accounting and hard spending caps.

Every call returns validated JSON (``output_config.format`` with a JSON schema), is priced
from its token usage, and is refused if it would break the run profile's daily or total cap.
A deterministic offline mock is available for free testing.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import db

# USD per million tokens (Claude API first-party pricing, cached 2026-10).
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache_read": 0.01},
    "mock": {"in": 0.0, "out": 0.0, "cache_read": 0.0},
}
CACHE_WRITE_MULT = 1.25


class BudgetExceeded(RuntimeError):
    pass


class Refused(RuntimeError):
    pass


def price(model: str, usage: Any) -> float:
    p = PRICES.get(model, PRICES["claude-opus-5-5"])
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (inp * p["in"] + out * p["out"] + cr * p["cache_read"] + cw * p["in"] * CACHE_WRITE_MULT) / 1e6


def _load_dotenv():
    import pathlib
    here = pathlib.Path(__file__).resolve()
    for path in (here.parents[1] / ".env", here.parents[2] / ".env"):  # livinglab/.env, then its parent
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().removeprefix("export ").strip()
                if k and k not in os.environ:
                    os.environ[k] = v.strip().strip('"').strip("'")


@dataclass
class Budget:
    daily_usd: float
    total_usd: float

    def check(self, con, estimate: float = 0.0):
        today = db.spent(con, db.budget_day())
        total = db.spent(con)
        if today + estimate > self.daily_usd:
            raise BudgetExceeded(f"daily cap reached (${today:.3f} of ${self.daily_usd:.2f}; resets 9:00 Eastern)")
        if total + estimate > self.total_usd:
            raise BudgetExceeded(f"total cap reached (${total:.2f} of ${self.total_usd:.2f})")


class Claude:
    """One shared client. ``mock`` replaces the API with a deterministic function (free)."""

    def __init__(self, con, budget: Budget, mock: Callable[[str, str, dict], dict] | None = None):
        self.con = con
        self.budget = budget
        self.mock = mock
        self._client = None
        if mock is None:
            _load_dotenv()
            import anthropic
            self._client = anthropic.Anthropic(max_retries=4)

    def json(self, *, stage: str, model: str, system: str, user: str, schema: dict, effort: str = "low",
             max_tokens: int = 8000) -> tuple[dict, float]:
        self.budget.check(self.con)
        if self.mock is not None:
            return self.mock(stage, user, schema), 0.0
        kwargs: dict[str, Any] = dict(
            model=model, max_tokens=max_tokens,
            system=[{"type": "text", "text": system}],
            messages=[{"role": "user", "content": user}],
            cache_control={"type": "ephemeral"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if model.startswith("claude-haiku"):
            kwargs["thinking"] = {"type": "disabled"}  # routine, well-specified work: no thinking tokens
        if model in ("claude-opus-5-5", "claude-sonnet-5-5"):
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"
            msg = self._client.beta.messages.create(**kwargs)
        else:
            msg = self._client.messages.create(**kwargs)
        usd = price(msg.model or model, msg.usage)
        db.add_spend(self.con, model, stage, usd)
        if msg.stop_reason == "refusal":
            raise Refused(f"{stage}: request declined ({getattr(msg, 'stop_details', None)})")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError(f"{stage}: output hit max_tokens")
        text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
        return json.loads(text), usd
