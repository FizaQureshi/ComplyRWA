#!/usr/bin/env python3
"""ComplyRWA step 4.5: add up generation batches into one benchmark table.

Reads results/filter_<batch>/report.csv (validity filter) and results/llm_ledger.jsonl (tokens, cost, seconds).
Replay calls are not double counted: for every (tag, model) the FIRST ledger line is used,
and its original_cost_usd (what the answer cost when first made).

  python pipeline/benchmark_summary.py --group Haiku=d1,d2,e1 --group Sonnet=s1
Writes results/benchmark_generated.md and .json
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
ALL_VARIANTS = [f"V{i:02d}" for i in range(1, 14)]


def read_ledger():
    rows, seen = [], set()
    f = RESULTS / "llm_ledger.jsonl"
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r["tag"].startswith("generator:") or r["mode"] == "mock":
            continue
        k = (r["tag"], r["model"])
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
    return rows


def summarize(batches, ledger):
    s = {"tests": 0, "KEEP": 0, "VACUOUS": 0, "REJECT": 0, "rules": set(), "killed": set(),
         "calls": 0, "failed_calls": 0, "in": 0, "out": 0, "usd": 0.0, "seconds": 0.0, "models": set()}
    for b in batches:
        rep = RESULTS / f"filter_{b}" / "report.csv"
        if not rep.exists():
            sys.exit(f"missing {rep}")
        for row in csv.DictReader(open(rep, encoding="utf-8")):
            s["tests"] += 1
            s[row["outcome"]] += 1
            m = re.match(r"Cand_(\w+?)_" + re.escape(b) + "$", row["contract"])
            if m:
                s["rules"].add(m.group(1))
            s["killed"].update(re.findall(r"V\d\d", row["reason"]) if row["outcome"] == "KEEP" else [])
        for r in ledger:
            parts = r["tag"].split(":")
            if parts[2] == b:
                s["calls"] += 1
                s["failed_calls"] += 1 if r.get("truncated") else 0
                s["in"] += r["input_tokens"]
                s["out"] += r["output_tokens"]
                s["usd"] += r["original_cost_usd"]
                s["seconds"] += r["seconds"]
                s["models"].add(r["model"])
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", action="append", required=True, help="Name=batch1,batch2")
    a = ap.parse_args()
    ledger = read_ledger()
    out = {}
    for g in a.group:
        name, batches = g.split("=")
        out[name] = summarize(batches.split(","), ledger)

    names = list(out)
    lines = ["| measure | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]

    def row(label, fn):
        lines.append(f"| {label} | " + " | ".join(fn(out[n]) for n in names) + " |")

    row("model", lambda s: ", ".join(sorted(s["models"])))
    row("rules covered", lambda s: f"{len(s['rules'])} ({' '.join(sorted(s['rules']))})")
    row("tests judged", lambda s: str(s["tests"]))
    row("KEEP / VACUOUS / REJECT", lambda s: f"{s['KEEP']} / {s['VACUOUS']} / {s['REJECT']}")
    row("valid and non-vacuous (KEEP)", lambda s: f"{s['KEEP']/s['tests']:.0%}")
    row("variants killed by a generated test", lambda s: f"{len(s['killed'])} of 13 (missing: {' '.join(v for v in ALL_VARIANTS if v not in s['killed']) or 'none'})")
    row("LLM calls (failed = cut off)", lambda s: f"{s['calls']} ({s['failed_calls']} failed)")
    row("input tokens", lambda s: f"{s['in']:,}")
    row("output tokens", lambda s: f"{s['out']:,}")
    row("cost USD (all calls incl. failed)", lambda s: f"${s['usd']:.4f}")
    row("cost USD per rule", lambda s: f"${s['usd']/max(1, len(s['rules'])):.4f}")
    row("model time (seconds, all calls)", lambda s: f"{s['seconds']:.0f}")
    text = "\n".join(lines)
    print(text)
    (RESULTS / "benchmark_generated.md").write_text(text + "\n", encoding="utf-8")
    for s in out.values():
        s["rules"] = sorted(s["rules"]); s["killed"] = sorted(s["killed"]); s["models"] = sorted(s["models"])
    (RESULTS / "benchmark_generated.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nWrote results/benchmark_generated.md and results/benchmark_generated.json")


if __name__ == "__main__":
    main()