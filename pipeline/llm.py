#!/usr/bin/env python3
"""ComplyRWA step 4.4: the one place where the pipeline talks to an LLM.

Settings come from pipeline/llm_config.json (aliases, prices, temperature, budget).
Prompt templates come from pipeline/prompts/<task>.md (system part, a line with ---USER---, user part).

Modes:
  mock    No network, no cost. Answer = pipeline/mock/<task>.txt, else mock/default.txt.
          <task> is the part of the call's tag before the first ':'  (tag "generator:K1:1" -> generator.txt).
          Also shows what a real call would roughly cost.
  replay  No network. Answers only from the saved cache; a miss is an error.
  live    Cache first (a hit is free). A miss calls the API, saves the answer, logs tokens and USD.

Safety:
  * The key is read only from the environment variable ANTHROPIC_API_KEY.
  * Before every live call, the worst-case cost is checked against the session cap
    (--cap, env COMPLYRWA_CAP_USD, or "session_cap_usd" in llm_config.json) and the hard stop.
  * Every call is written to results/llm_ledger.jsonl.

Usage (from the ComplyRWA folder):
  python pipeline/llm.py --mode mock --smoke
  python pipeline/llm.py --mode live --model haiku --smoke
  python pipeline/llm.py --ledger
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
CONFIG_FILE = PIPE / "llm_config.json"
PROMPT_DIR = PIPE / "prompts"
MOCK_DIR = PIPE / "mock"
CACHE_DIR = ROOT / "results" / "llm_cache"
LEDGER = ROOT / "results" / "llm_ledger.jsonl"


class BudgetExceeded(RuntimeError):
    pass


class ReplayMiss(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float           # money spent by THIS call (0 for mock and cache hits)
    original_cost_usd: float  # cost when first made (use this for the benchmark)
    cached: bool
    stop_reason: str
    truncated: bool           # True if the answer was cut by max_tokens
    seconds: float
    key: str


# ---------------------------------------------------------------- helpers
def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def resolve_model(name, cfg=None):
    cfg = cfg or load_config()
    return cfg.get("aliases", {}).get(name, name)


def estimate_tokens(text):
    """Rough guide only: characters / 4."""
    return max(1, len(text) // 4)


def render(task, **values):
    """Fill pipeline/prompts/<task>.md. Returns (system, user).
    Every {{NAME}} must be given in `values`, else KeyError (so a typo is never sent to the model)."""
    raw = (PROMPT_DIR / f"{task}.md").read_text(encoding="utf-8")
    if "---USER---" not in raw:
        raise ValueError(f"{task}.md has no ---USER--- line")
    system, user = raw.split("---USER---", 1)

    def fill(text):
        def sub(m):
            if m.group(1) not in values:
                raise KeyError(f"prompt '{task}' needs a value for {{{{{m.group(1)}}}}}")
            return str(values[m.group(1)])
        return re.sub(r"\{\{(\w+)\}\}", sub, text).strip()   # one pass: inserted text is never re-scanned

    return fill(system), fill(user)


def cost_usd(model, usage, cfg=None):
    cfg = cfg or load_config()
    p = cfg["models"].get(model)
    if not p or p.get("input_per_mtok_usd") is None or p.get("output_per_mtok_usd") is None:
        raise KeyError(f"no price for '{model}' in llm_config.json")
    return (usage.get("input_tokens", 0) * p["input_per_mtok_usd"]
            + usage.get("output_tokens", 0) * p["output_per_mtok_usd"]) / 1_000_000


# ---------------------------------------------------------------- client
class LLMClient:
    def __init__(self, mode="mock", cap_usd=None, cache_dir=CACHE_DIR,
                 ledger_path=LEDGER, mock_dir=MOCK_DIR):
        if mode not in ("mock", "replay", "live"):
            raise ValueError("mode must be mock, replay or live")
        self.mode = mode
        self.cfg = load_config()
        if cap_usd is None:
            cap_usd = os.environ.get("COMPLYRWA_CAP_USD", self.cfg.get("session_cap_usd", 15))
        self.cap = float(cap_usd)
        self.hard_stop = float(self.cfg.get("budget_usd", {}).get("hard_stop", 115))
        self.temperature = self.cfg.get("temperature")
        self.cache_dir = Path(cache_dir)
        self.ledger_path = Path(ledger_path)
        self.mock_dir = Path(mock_dir)
        self._client = None

    # ledger
    def _read_ledger(self):
        if not self.ledger_path.exists():
            return []
        return [json.loads(l) for l in self.ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def spent(self):
        return sum(r.get("cost_usd", 0.0) for r in self._read_ledger())

    def _log(self, res, tag, max_tokens):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": self.mode, "tag": tag,
               "model": res.model, "cached": res.cached, "input_tokens": res.input_tokens,
               "output_tokens": res.output_tokens, "cost_usd": round(res.cost_usd, 6),
               "original_cost_usd": round(res.original_cost_usd, 6), "stop_reason": res.stop_reason,
               "truncated": res.truncated, "max_tokens": max_tokens,
               "seconds": round(res.seconds, 2), "key": res.key[:16]}
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    # cache
    def make_key(self, model, system, user, max_tokens, sample):
        blob = json.dumps({"model": model, "system": system, "user": user, "max_tokens": max_tokens,
                           "sample": sample, "temperature": self.temperature}, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _cache_get(self, key):
        f = self.cache_dir / f"{key}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def _cache_put(self, key, entry):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / f"{key}.json").write_text(json.dumps(entry, indent=1), encoding="utf-8")

    # main call
    def complete(self, system, user, *, model, max_tokens=4000, tag="", sample=0):
        """`model` may be an alias (haiku, sonnet) or a full id.
        NOTE: with temperature 0 the same prompt gives (almost) the same answer, so `sample`
        does not create variety. To get several different tests, ask for several tests in one prompt."""
        model = resolve_model(model, self.cfg)
        key = self.make_key(model, system, user, max_tokens, sample)
        t0 = time.time()
        if self.mode == "mock":
            res = self._mock(system, user, model, tag, key, t0)
        else:
            hit = self._cache_get(key)
            if hit:
                u = hit["usage"]
                res = LLMResult(hit["text"], model, u.get("input_tokens", 0), u.get("output_tokens", 0),
                                0.0, hit["cost_usd"], True, hit["stop_reason"],
                                hit["stop_reason"] == "max_tokens", time.time() - t0, key)
            elif self.mode == "replay":
                raise ReplayMiss(f"no cached answer for tag '{tag}' (key {key[:12]}). Run once in live mode first.")
            else:
                res = self._live(system, user, model, max_tokens, tag, key)
        self._log(res, tag, max_tokens)
        return res

    def _mock(self, system, user, model, tag, key, t0):
        stem = tag.split(":")[0] if tag else ""
        f = self.mock_dir / f"{stem}.txt"
        if not (stem and f.exists()):
            f = self.mock_dir / "default.txt"
        text = f.read_text(encoding="utf-8")
        usage = {"input_tokens": estimate_tokens(system + user), "output_tokens": estimate_tokens(text)}
        try:
            est = cost_usd(model, usage, self.cfg)
        except KeyError:
            est = 0.0
        return LLMResult(text, model, usage["input_tokens"], usage["output_tokens"],
                         0.0, est, False, "end_turn", False, time.time() - t0, key)

    def _live(self, system, user, model, max_tokens, tag, key):
        worst_in = int(estimate_tokens(system + user) * 1.7)   # newer tokenizers use more tokens
        worst = cost_usd(model, {"input_tokens": worst_in, "output_tokens": max_tokens}, self.cfg)
        spent = self.spent()
        if spent + worst > min(self.cap, self.hard_stop):
            raise BudgetExceeded(f"spent ${spent:.4f} + worst case ${worst:.4f} would pass the limit "
                                 f"${min(self.cap, self.hard_stop):.2f}")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set in this shell")
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                      messages=[{"role": "user", "content": user}])
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        t0 = time.time()
        try:
            resp = self._client.messages.create(**kwargs)
        except Exception as e:                       # some models reject 'temperature'
            if "temperature" in str(e).lower() and "temperature" in kwargs:
                print("note: API rejected temperature; retrying without it "
                      "(set \"temperature\": null in llm_config.json to stop this message)", file=sys.stderr)
                del kwargs["temperature"]
                resp = self._client.messages.create(**kwargs)
            else:
                raise
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        u = resp.usage
        usage = {"input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens or 0}
        c = cost_usd(model, usage, self.cfg)
        stop = resp.stop_reason or ""
        self._cache_put(key, {"text": text, "model": model, "usage": usage, "stop_reason": stop,
                              "cost_usd": c, "tag": tag, "created": time.strftime("%Y-%m-%d %H:%M:%S")})
        return LLMResult(text, model, usage["input_tokens"], usage["output_tokens"], c, c, False,
                         stop, stop == "max_tokens", time.time() - t0, key)

    def summary(self):
        rows = self._read_ledger()
        live = [r for r in rows if r["mode"] == "live" and not r["cached"]]
        spent = sum(r["cost_usd"] for r in rows)
        lines = [f"ledger: {len(rows)} calls, {len(live)} paid live calls",
                 f"spent: ${spent:.4f} of session cap ${self.cap:.2f} (left ${self.cap - spent:.4f}); "
                 f"team plan ${self.cfg.get('budget_usd', {}).get('planned', '?')}, hard stop ${self.hard_stop:.0f}"]
        by = {}
        for r in live:
            d = by.setdefault(r["model"], [0, 0, 0, 0.0])
            d[0] += 1; d[1] += r["input_tokens"]; d[2] += r["output_tokens"]; d[3] += r["cost_usd"]
        for m, (n, i, o, c) in by.items():
            lines.append(f"  {m}: {n} calls, {i} in, {o} out tokens, ${c:.4f}")
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=None, choices=["mock", "replay", "live"])
    ap.add_argument("--model", default=None, help="alias (haiku, sonnet) or full model id")
    ap.add_argument("--cap", type=float, default=None)
    ap.add_argument("--smoke", action="store_true", help="send one tiny question")
    ap.add_argument("--ledger", action="store_true", help="print the spending summary")
    a = ap.parse_args()
    cfg = load_config()
    client = LLMClient(a.mode or cfg.get("default_mode", "mock"), a.cap)
    if a.smoke:
        r = client.complete("You are a connectivity test.", "Reply with the single word: ok",
                            model=a.model or cfg.get("default_model", "haiku"), max_tokens=20, tag="smoke")
        print(f"model: {r.model}")
        print(f"answer: {r.text.strip()[:60]!r}")
        print(f"tokens in/out: {r.input_tokens}/{r.output_tokens}  cost: ${r.cost_usd:.6f}  cached: {r.cached}")
    if a.ledger or a.smoke:
        print(client.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())