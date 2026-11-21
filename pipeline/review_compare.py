#!/usr/bin/env python3
"""ComplyRWA step 4.8: compare all review runs in one table. No LLM, no network.

Every run folder results/review_<batch>_<model>/ (mock runs are skipped) is scored again from its raw answers,
once as the first run, and once more with the retry answers if there are any.

  python pipeline/review_compare.py                    table, also written to results/review_compare.md
  python pipeline/review_compare.py --clean-findings   every HIGH/MEDIUM finding on a clean target, per run
  python pipeline/review_compare.py --rescore-all      rewrite report.md, scores.csv, findings.json of every run
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
import review_score as rs  # noqa: E402


def run_dirs(explicit):
    if explicit:
        return [Path(x) for x in explicit]
    return [d for d in sorted((ROOT / "results").glob("review_*_*")) if (d / "raw").is_dir() and "mock" not in d.name]


def score_dir(d, with_retry, kw, entries, rules):
    d = Path(d)
    calls = rs.load_json(d / "calls.json") if (d / "calls.json").exists() else {}
    answers = {}
    for e in entries:
        f = d / "raw" / f"{e['id']}.txt"
        if f.exists():
            answers[e["id"]] = {"text": f.read_text(encoding="utf-8"), "truncated": bool(calls.get(e["id"], {}).get("truncated"))}
    retried = []
    if with_retry:
        answers, calls, retried = rs.apply_retries(d, entries, answers, calls)
    rows, notes, found = rs.score_all(answers, kw, entries, rules)
    return rows, rs.summarize(rows), calls, retried, found


def views(d):
    """(label, with_retry) for a run folder: the first run, and the run with retries if any retry exists."""
    name = Path(d).name.removeprefix("review_")
    out = [(name, False)]
    if (Path(d) / "calls_retry.json").exists() and rs.load_json(Path(d) / "calls_retry.json"):
        out.append((name + " +retry", True))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="*", help="run folders (default: all results/review_*_*)")
    ap.add_argument("--clean-findings", action="store_true")
    ap.add_argument("--rescore-all", action="store_true")
    a = ap.parse_args()
    dirs = run_dirs(a.dirs)
    if not dirs:
        sys.exit("no run folders found")
    if a.rescore_all:
        for d in dirs:
            for _, wr in views(d):
                cmd = [sys.executable, str(PIPE / "review_score.py"), "--dir", str(d)] + (["--with-retry"] if wr else [])
                subprocess.run(cmd, cwd=ROOT, check=True)
        return 0
    kw = rs.load_json(rs.KEYWORDS_FILE)
    entries = rs.load_json(rs.MANIFEST_FILE)["configs"]
    rules = rs.load_json(rs.POLICY_FILE)["rules"]

    if a.clean_findings:
        for d in dirs:
            label, wr = views(d)[-1]
            rows, _, _, _, found = score_dir(d, wr, kw, entries, rules)
            print(f"== {label}")
            for r in rows:
                if r["kind"] != "clean" or r["status"] != "ok":
                    continue
                for f in found[r["target"]]:
                    if f["severity"] in rs.SERIOUS:
                        gap = "STOCK-GAP" if rs.is_stock_gap(f) else "         "
                        print(f"  {r['target']} {f['rule']} {f['severity']:<6} {gap} {f['where'][:95]}")
        return 0

    head = ["run", "detected", "strict", "detected adj", "strict adj", "invalid", "false pos", "false pos adj",
            "targets with S03/S04", "cost USD", "time s"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for d in dirs:
        for label, wr in views(d):
            rows, s, calls, retried, _ = score_dir(d, wr, kw, entries, rules)
            cost = sum(c.get("cost_usd", 0.0) for c in calls.values())
            sec = sum(c.get("seconds", 0.0) for c in calls.values())
            lines.append("| " + " | ".join([
                label, f"{s['official']}/{s['variants']}", f"{s['strict']}/{s['variants']}",
                f"{s['official_adj']}/{s['variants']}", f"{s['strict_adj']}/{s['variants']}",
                str(len(s["no_valid_answer"])) + (f" ({' '.join(s['no_valid_answer'])})" if s["no_valid_answer"] else ""),
                f"{s['false_positives']}/{s['clean']}", f"{s['false_positives_adj']}/{s['clean']}",
                str(len(s["stock_gap_targets"])), f"${cost:.4f}", f"{sec:.0f}"]) + " |")
    text = "\n".join(lines)
    print(text)
    (ROOT / "results").mkdir(exist_ok=True)
    Path(ROOT / "results", "review_compare.md").write_text(text + "\n", encoding="utf-8")
    print("\nWrote results/review_compare.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())