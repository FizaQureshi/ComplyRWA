#!/usr/bin/env python3
"""ComplyRWA step 4.4: dry run. Builds the generator prompt for every rule and
prints its approximate size. Makes NO API call and costs nothing.

  py311 pipeline/prompt_size.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm  # noqa: E402

RULES = ["K1", "K2", "K3", "K4", "K5", "J1", "J2", "J3", "J4", "H1", "H2", "H3", "H4"]
SLICES = HERE / "slices"
POLICY = "(placeholder policy sentence of about this length, written by the issuer in plain English)"


def find_slice(rule):
    pat = re.compile(r"(^|[^A-Z0-9])" + rule + r"([^A-Z0-9]|$)")
    hits = sorted(p for p in SLICES.iterdir()
                  if p.is_file() and not p.name.startswith("_")
                  and p.name not in ("index.json", "sizes.md")
                  and pat.search(p.name.upper()))
    if len(hits) != 1:
        raise SystemExit(f"Rule {rule}: expected exactly one slice file in {SLICES}, "
                         f"found {[h.name for h in hits]}")
    return hits[0]


def main():
    api = (SLICES / "_fixture_api.txt").read_text(encoding="utf-8")
    facts = (HERE / "fixture_facts.md").read_text(encoding="utf-8")
    cfg = llm.load_config()
    rows, total = [], 0
    for r in RULES:
        f = find_slice(r)
        text = f.read_text(encoding="utf-8")
        m = re.match(r"//\s*Rule\s+\w+:\s*(.+)", text)
        title = m.group(1).strip() if m else r
        system, prompt = llm.render(
            "generator", CONTRACT_NAME=f"Cand_{r}_b1", RULE_ID=r, RULE_TITLE=title,
            POLICY_TEXT=POLICY, N_TESTS=4, SLICE=text, FIXTURE_API=api, FIXTURE_FACTS=facts)
        tok = llm.estimate_tokens(system) + llm.estimate_tokens(prompt)
        rows.append((r, f.name, tok))
        total += tok
    print(f"{'rule':<5}{'slice file':<28}{'prompt ~tokens':>14}")
    for r, name, tok in rows:
        print(f"{r:<5}{name:<28}{tok:>14,}")
    avg = total // len(rows)
    print(f"\naverage ~{avg:,} input tokens per rule, all 13 rules ~{total:,} (characters / 4, a rough guide)")
    out = 2000
    for model, p in cfg["models"].items():
        if p["input_per_mtok_usd"] is None or p["output_per_mtok_usd"] is None:
            print(f"{model}: price not set, no cost shown")
            continue
        one = (avg * p["input_per_mtok_usd"] + out * p["output_per_mtok_usd"]) / 1e6
        print(f"{model}: about ${one:.4f} per call with ~{out:,} output tokens; "
              f"13 rules once about ${one * 13:.2f}")


if __name__ == "__main__":
    main()
