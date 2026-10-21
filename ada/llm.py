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
BATCH_DISCOUNT = 0.5  # Message Batches API: half price, results usually within the hour


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

    @staticmethod
    def params(*, model: str, system: str, user: str, schema: dict, effort: str = "low", max_tokens: int = 8000) -> dict:
        """One request, as sent directly or inside a batch."""
        kwargs: dict[str, Any] = dict(
            model=model, max_tokens=max_tokens,
            system=[{"type": "text", "text": system}],
            messages=[{"role": "user", "content": user}],
            cache_control={"type": "ephemeral"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if model.startswith("claude-haiku"):
            kwargs["thinking"] = {"type": "disabled"}  # routine, well-specified work: no thinking tokens
        return kwargs

    def json(self, *, stage: str, model: str, system: str, user: str, schema: dict, effort: str = "low",
             max_tokens: int = 8000) -> tuple[dict, float]:
        self.budget.check(self.con)
        if self.mock is not None:
            return self.mock(stage, user, schema), 0.0
        kwargs = self.params(model=model, system=system, user=user, schema=schema, effort=effort, max_tokens=max_tokens)
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

    # ---------------------------------------------------------------- half-price batches
    def submit_batch(self, items: list[dict]) -> str:
        """items: {custom_id, stage, model, system, user, schema, effort, max_tokens}. Returns the batch id.
        Refusal fallbacks are not available in batches; a declined request simply fails and is retried directly."""
        if self.mock is not None:
            bid = f"mock-{time.time():.6f}"
            self._mock_batches = getattr(self, "_mock_batches", {})
            self._mock_batches[bid] = {i["custom_id"]: (self.mock(i["stage"], i["user"], i["schema"]), i) for i in items}
            return bid
        reqs = [{"custom_id": i["custom_id"], "params": self.params(**{k: i[k] for k in (
            "model", "system", "user", "schema", "effort", "max_tokens")})} for i in items]
        return self._client.messages.batches.create(requests=reqs).id

    def batch_done(self, batch_id: str) -> bool:
        if self.mock is not None:
            return True
        return self._client.messages.batches.retrieve(batch_id).processing_status == "ended"

    def batch_results(self, batch_id: str, stages: dict[str, tuple[str, str]]) -> dict[str, tuple[dict, float] | None]:
        """custom_id -> (parsed JSON, usd) or None if it failed. Spend is recorded at the batch price.
        stages: custom_id -> (stage, model), for the spend log."""
        if self.mock is not None:
            return {cid: (res, 0.0) for cid, (res, _) in self._mock_batches.pop(batch_id).items()}
        out = {}
        for r in self._client.messages.batches.results(batch_id):
            stage, model = stages.get(r.custom_id, ("batch", "claude-haiku-5-5"))
            if r.result.type != "succeeded":
                out[r.custom_id] = None
                continue
            msg = r.result.message
            usd = price(msg.model or model, msg.usage) * BATCH_DISCOUNT
            db.add_spend(self.con, model, stage, usd)
            text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
            ok = msg.stop_reason not in ("refusal", "max_tokens") and text
            out[r.custom_id] = (json.loads(text), usd) if ok else None
        return out
