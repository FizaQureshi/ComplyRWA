#!/usr/bin/env python3
"""ComplyRWA step 4.8: the three-way benchmark table. No LLM, no network. Every number is read from a result file.

Method 1  hand-written Foundry tests, no LLM (the Phase 3 gold set)   results/variant_table.csv, results/exec_gold/run_info.json
Method 2  LLM-generated tests (Phase 4.5), Haiku and Sonnet            results/benchmark_generated.json, results/filter_<batch>/joint/run_info.json
Method 3  LLM-only review (step 4.8), Haiku and Sonnet                 results/review_<batch>_<model>/ (scored again from the raw answers)
Manual triage counts for method 3 come from results/review_triage.json.

  python pipeline/benchmark_threeway.py
  python pipeline/benchmark_threeway.py --gen-group Haiku=d1,d2,e1 --gen-group Sonnet=s1

Writes results/benchmark_threeway.md
"""
import argparse
import csv
import json
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
import review_compare as rc  # noqa: E402
import review_score as rs  # noqa: E402

RESULTS = ROOT / "results"
VARIANTS = [f"V{i:02d}" for i in range(1, 14)]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def gold():
    f = RESULTS / "variant_table.csv"
    rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
    cols = {k.strip().lower(): k for k in rows[0]}
    if "config" not in cols or "verdict" not in cols:
        sys.exit(f"{f} has the columns {list(rows[0])}, but 'config' and 'verdict' are expected. "
                 f"Paste its first two lines and the script will be adapted.")
    ck, vk = cols["config"], cols["verdict"]
    caught = {r[ck] for r in rows if r[ck].startswith("V") and r[vk].strip().upper().startswith("CAUGHT")}
    false_pos = [r[ck] for r in rows if r[ck].startswith("C") and r[vk].strip().lower() != "clean"]
    return {"caught": caught, "false_pos": false_pos, "seconds": load(RESULTS / "exec_gold" / "run_info.json")["seconds"]}


def generated(groups):
    bench = load(RESULTS / "benchmark_generated.json")
    out = {}
    for name, batches in groups.items():
        b = bench[name]
        foundry = sum(load(RESULTS / f"filter_{x}" / "joint" / "run_info.json")["seconds"] for x in batches)
        out[name] = {"b": b, "killed": set(b["killed"]), "foundry": foundry, "batches": batches}
    return out


def review(model, batch, kw, entries, rules, triage):
    d = RESULTS / f"review_{batch}_{model}"
    label, with_retry = rc.views(d)[-1]
    first_rows, first_s, _, _, _ = rc.score_dir(d, False, kw, entries, rules)
    rows, s, calls, retried, _ = rc.score_dir(d, with_retry, kw, entries, rules)
    return {
        "batch": batch, "model": model, "rows": rows, "s": s, "first": first_s["official"], "retried": retried,
        "tin": sum(c.get("input_tokens", 0) for c in calls.values()),
        "tout": sum(c.get("output_tokens", 0) for c in calls.values()),
        "cost": sum(c.get("cost_usd", 0.0) for c in calls.values()),
        "sec": sum(c.get("seconds", 0.0) for c in calls.values()),
        "triaged": triage.get(f"{batch}_{model}"),
    }


def det(r):
    n = r["s"]["official"]
    return f"{n}/13" if r["first"] == n else f"{n}/13 after retry ({r['first']}/13 as first answered)"


def fp(r):
    s = r["s"]
    return f"{s['false_positives']} / {s['false_positives_adj']} / {r['triaged']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-group", action="append", default=None, help="Name=batch1,batch2 (default: Haiku=d1,d2,e1 Sonnet=s1)")
    a = ap.parse_args()
    groups = {}
    for g in a.gen_group or ["Haiku=d1,d2,e1", "Sonnet=s1"]:
        n, b = g.split("=")
        groups[n] = b.split(",")

    kw = rs.load_json(rs.KEYWORDS_FILE)
    entries = rs.load_json(rs.MANIFEST_FILE)["configs"]
    rules = rs.load_json(rs.POLICY_FILE)["rules"]
    triage = load(RESULTS / "review_triage.json")

    G = gold()
    GEN = generated(groups)
    REV = {m: [review(m, b, kw, entries, rules, triage) for b in ("r1", "r1b")] for m in ("haiku", "sonnet")}

    L = ["# Three-way benchmark (project step 4.8)", "",
         "| Method | Variants detected (of 13) | False alarms on the 8 clean configurations | Tokens in / out | Cost USD | Time (s) |",
         "|---|---|---|---|---|---|"]
    L.append(f"| Hand-written Foundry tests (no LLM) | {len(G['caught'])}/13 | {len(G['false_pos'])} of 8 | 0 / 0 | $0 | {G['seconds']:.0f} (Foundry run incl. compile) |")
    for name, g in GEN.items():
        b = g["b"]
        L.append(f"| LLM-generated tests, {name} | {len(g['killed'])}/13 | 0 of 8 configurations ({b['REJECT']} of {b['tests']} tests rejected for failing on a clean configuration) "
                 f"| {b['in']:,} / {b['out']:,} | ${b['usd']:.4f} | {b['seconds'] + g['foundry']:.0f} ({b['seconds']:.0f} model + {g['foundry']:.0f} Foundry) |")
    for m, runs in REV.items():
        r1, r1b = runs
        L.append(f"| LLM-only review, {m.capitalize()} (r1; repeat r1b) | {det(r1)}; r1b: {det(r1b)} "
                 f"| frozen / adjusted / after triage: r1 {fp(r1)}; r1b {fp(r1b)} "
                 f"| r1 {r1['tin']:,} / {r1['tout']:,} | r1 ${r1['cost']:.4f}; r1b ${r1b['cost']:.4f} | r1 {r1['sec']:.0f}; r1b {r1b['sec']:.0f} (model time) |")

    L += ["", "## Which variants each method catches", "",
          "| Variant | Hand-written | Generated Haiku | Generated Sonnet | Review Haiku (r1) | Review Sonnet (r1, after retry) |", "|---|---|---|---|---|---|"]
    rv = {m: {r["target"]: r["official"] for r in runs[0]["rows"]} for m, runs in REV.items()}
    mark = lambda x: "yes" if x else "NO"  # noqa: E731
    gn = list(GEN)
    for v in VARIANTS:
        gcells = [mark(v in GEN[n]["killed"]) if n in GEN else "-" for n in ("Haiku", "Sonnet")]
        L.append(f"| {v} | {mark(v in G['caught'])} | {gcells[0]} | {gcells[1]} | {mark(rv['haiku'].get(v))} | {mark(rv['sonnet'].get(v))} |")

    L += ["", "## How to read this", "",
          "- Detected: a variant counts when the method reports or fails on it. Hand-written and generated tests: a linked or any test fails on the variant while passing on every clean configuration. Review: a HIGH or MEDIUM finding on a linked rule.",
          "- False alarms: tests are judged on the clean configurations (a generated test that fails there is rejected). The review is judged by its HIGH and MEDIUM findings on clean configurations: frozen = as defined before the runs, adjusted = ignoring the stock gaps S03/S04, after triage = true false alarms only (manual labels, see review_triage.md). The three-count form is frozen / adjusted / after triage.",
          "- The methods see different things. The hand-written tests are the answer key, written by the same author as the variants. The generated tests see only the clean pinned code and the policy text, never the variants. The review sees each target's own code and setup, with comments removed, so it is easier than blind testing. Seven variants are configuration-only changes (V04, V05, V07, V08, V09, V11, V13), where the setup override shows the change itself. Four variants (V03, V06, V10, V12) are visible only in the code, with no setup override.",
          "- Time: model time is the sum of the API call times. Foundry time is the executor run on all configurations including compile. The time to write the hand-written tests and the variants by a person is not counted.",
          "- Costs of the generated tests cover generation only. The explainer adds about $0.0014 per finding on Haiku (Phase 4.6).",
          "- Review rows: Sonnet's first answer was invalid JSON for some targets. One retry per invalid answer was allowed for both models; the cost and time of the retries are included.",
          "- Each review number comes from one run per batch. The two runs on the same input (r1 and r1b) show the run-to-run range."]
    text = "\n".join(L) + "\n"
    print(text)
    Path(RESULTS, "benchmark_threeway.md").write_text(text, encoding="utf-8")
    print("Wrote results/benchmark_threeway.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())