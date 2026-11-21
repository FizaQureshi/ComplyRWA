#!/usr/bin/env python3
"""ComplyRWA step 4.8: score the answers of the LLM-only review. No LLM and no network here.

Input: one run folder, results/review_<batch>_<model>/
  raw/<TARGET>.txt   the model's raw answer for each target (written by review_baseline.py)
  calls.json         optional: per target {input_tokens, output_tokens, cost_usd, seconds, truncated, stop_reason}
Data: pipeline/review_keywords.json (linked rules and strict words, frozen before the first live call),
      pipeline/configs.json (which targets are clean or variants), pipeline/review_policy.json (the 10 rules).

Definitions (the same text is in review_keywords.json):
  official detected   a HIGH or MEDIUM finding whose rule is one of the variant's linked rules
  strict detected     official, and that finding's where+why text holds one of the variant's strict words
  false positive      a clean target with at least one HIGH or MEDIUM finding
  no valid answer     empty, cut off, or not valid JSON. Never counted as "no findings".
  stock-gap finding   a K2 finding that describes the twin-signature gap (S03 in Phase 3: a revoked claim can be
                      re-added with signature (r, n-s, v^1)). It is a real gap of the ONCHAINID dependency, not a seeded
                      variant, and Phase 3 kept it out of the detection and false-positive measures. The report therefore
                      shows every number twice: as defined above, and "adjusted", which ignores stock-gap findings.
                      This rule was fixed after the first real answer (C01) and before the other 20 answers existed.

Outputs in the run folder: report.md, scores.csv, findings.json

  python pipeline/review_score.py --dir results/review_r1_haiku
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
KEYWORDS_FILE = PIPE / "review_keywords.json"
MANIFEST_FILE = PIPE / "configs.json"
POLICY_FILE = PIPE / "review_policy.json"

SEVERITIES = ("HIGH", "MEDIUM", "LOW")
SERIOUS = ("HIGH", "MEDIUM")
SEV_ALIAS = {"CRITICAL": "HIGH", "MED": "MEDIUM", "INFO": "LOW", "INFORMATIONAL": "LOW"}

# Words that mark a K2 finding as the known twin-signature stock gap (S03). Lower case, searched in where + why + steps.
STOCK_GAP_WORDS = ("malleab", "high-s", "high s", "n-s", "n - s", "n\u2212s", "twin signature", "twin sig",
                   "different signature", "alternate signature", "second signature", "alternative signature")


def is_stock_gap(f):
    text = (f["where"] + " " + f["why"] + " " + f["steps"]).lower()
    return f["rule"] == "K2" and any(w in text for w in STOCK_GAP_WORDS)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ parsing
def parse_answer(text, truncated=False):
    """Return (status, findings, notes). status is 'ok' or 'no_valid_answer'."""
    notes = []
    if truncated:
        return "no_valid_answer", [], ["answer was cut off by max_tokens"]
    if not text or not text.strip():
        return "no_valid_answer", [], ["empty answer"]
    body = text
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        body = m.group(1)
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end <= start:
        return "no_valid_answer", [], ["no JSON object in the answer"]
    try:
        data = json.loads(body[start:end + 1])
    except json.JSONDecodeError as e:
        return "no_valid_answer", [], [f"invalid JSON: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        return "no_valid_answer", [], ["JSON has no 'findings' list"]
    out = []
    for i, f in enumerate(data["findings"]):
        if not isinstance(f, dict):
            return "no_valid_answer", [], [f"finding {i} is not an object"]
        sev = str(f.get("severity") or "").strip().upper()
        sev = SEV_ALIAS.get(sev, sev)
        if sev not in SEVERITIES:
            notes.append(f"finding {i}: unknown severity {f.get('severity')!r}, treated as LOW")
            sev = "LOW"
        out.append({
            "rule": str(f.get("rule") or "").strip().upper(),
            "where": str(f.get("where") or ""),
            "severity": sev,
            "why": str(f.get("why") or ""),
            "steps": str(f.get("steps") or ""),
        })
    return "ok", out, notes


# ------------------------------------------------------------------ scoring
def score_target(tid, kind, status, findings, kw, rules):
    r = {"target": tid, "kind": kind, "status": status, "findings": len(findings),
         "serious": 0, "official": False, "strict": False, "flagged_any": False,
         "false_positive": False, "out_of_scope": 0, "rules_flagged": [], "matched": None,
         "stock_gap_findings": 0, "official_adj": False, "strict_adj": False, "false_positive_adj": False}
    if status != "ok":
        return r
    serious = [f for f in findings if f["severity"] in SERIOUS]
    gap = [f for f in serious if is_stock_gap(f)]
    plain = [f for f in serious if not is_stock_gap(f)]
    r["serious"] = len(serious)
    r["stock_gap_findings"] = len(gap)
    r["rules_flagged"] = sorted({f["rule"] for f in serious})
    r["flagged_any"] = bool(serious)
    if kind == "variant":
        spec = kw["variants"][tid]
        linked, words = set(spec["linked_rules"]), spec["strict_any_of"]

        def strict_of(hits):
            return [f for f in hits if any(w in (f["where"] + " " + f["why"]).lower() for w in words)]

        hits = [f for f in serious if f["rule"] in linked]
        hits_adj = [f for f in plain if f["rule"] in linked]
        r["official"], r["official_adj"] = bool(hits), bool(hits_adj)
        r["strict"], r["strict_adj"] = bool(strict_of(hits)), bool(strict_of(hits_adj))
        r["matched"] = (strict_of(hits_adj) or hits_adj or strict_of(hits) or hits or [None])[0]
    else:
        r["false_positive"] = bool(serious)
        r["false_positive_adj"] = bool(plain)
        r["out_of_scope"] = sum(1 for f in serious if f["rule"] not in rules)
        r["matched"] = (plain or serious or [None])[0]
    return r


def score_all(answers, kw, entries, rules):
    """answers: {target: {"text": str, "truncated": bool}}. Returns (rows, parsed_notes, parsed_findings)."""
    rows, notes, found = [], {}, {}
    for e in entries:
        tid = e["id"]
        a = answers.get(tid)
        if a is None:
            status, findings, n = "no_valid_answer", [], ["no answer saved for this target"]
        else:
            status, findings, n = parse_answer(a.get("text", ""), a.get("truncated", False))
        notes[tid], found[tid] = n, findings
        rows.append(score_target(tid, e["kind"], status, findings, kw, rules))
    return rows, notes, found


def summarize(rows):
    var = [r for r in rows if r["kind"] == "variant"]
    cln = [r for r in rows if r["kind"] == "clean"]
    var_ok = [r for r in var if r["status"] == "ok"]
    cln_ok = [r for r in cln if r["status"] == "ok"]
    s = {
        "variants": len(var), "variants_valid": len(var_ok),
        "official": sum(r["official"] for r in var), "strict": sum(r["strict"] for r in var),
        "flagged_any": sum(r["flagged_any"] for r in var),
        "clean": len(cln), "clean_valid": len(cln_ok),
        "false_positives": sum(r["false_positive"] for r in cln),
        "out_of_scope_findings": sum(r["out_of_scope"] for r in cln),
        "no_valid_answer": [r["target"] for r in rows if r["status"] != "ok"],
        "official_adj": sum(r["official_adj"] for r in var), "strict_adj": sum(r["strict_adj"] for r in var),
        "false_positives_adj": sum(r["false_positive_adj"] for r in cln),
        "stock_gap_targets": [r["target"] for r in rows if r["stock_gap_findings"]],
    }
    s["detection_rate_adj"] = s["official_adj"] / s["variants"] if s["variants"] else 0.0
    s["strict_rate_adj"] = s["strict_adj"] / s["variants"] if s["variants"] else 0.0
    s["false_positive_rate_adj"] = s["false_positives_adj"] / s["clean"] if s["clean"] else 0.0
    s["detection_rate"] = s["official"] / s["variants"] if s["variants"] else 0.0
    s["strict_rate"] = s["strict"] / s["variants"] if s["variants"] else 0.0
    s["false_positive_rate"] = s["false_positives"] / s["clean"] if s["clean"] else 0.0
    s["detection_rate_valid_only"] = s["official"] / s["variants_valid"] if s["variants_valid"] else 0.0
    s["false_positive_rate_valid_only"] = s["false_positives"] / s["clean_valid"] if s["clean_valid"] else 0.0
    return s


# ------------------------------------------------------------------ output
def pct(x):
    return f"{x:.0%}"


def write_report(out, name, rows, notes, s, calls):
    L = [f"# LLM-only review: {name}", ""]
    L += ["| measure | value |", "|---|---|",
          f"| variants detected (official) | {s['official']} of {s['variants']} = {pct(s['detection_rate'])} |",
          f"| variants detected (strict, names the changed code) | {s['strict']} of {s['variants']} = {pct(s['strict_rate'])} |",
          f"| variants detected (official, adjusted: ignoring stock-gap findings) | {s['official_adj']} of {s['variants']} = {pct(s['detection_rate_adj'])} |",
          f"| variants detected (strict, adjusted) | {s['strict_adj']} of {s['variants']} = {pct(s['strict_rate_adj'])} |",
          f"| variants with any HIGH/MEDIUM finding | {s['flagged_any']} of {s['variants']} |",
          f"| clean targets with a false positive | {s['false_positives']} of {s['clean']} = {pct(s['false_positive_rate'])} |",
          f"| clean targets with a false positive (adjusted: ignoring stock-gap findings) | {s['false_positives_adj']} of {s['clean']} = {pct(s['false_positive_rate_adj'])} |",
          f"| targets with a stock-gap finding (twin signature, S03) | {len(s['stock_gap_targets'])} ({' '.join(s['stock_gap_targets']) or 'none'}) |",
          f"| false-positive findings on a rule outside the 10 listed | {s['out_of_scope_findings']} |",
          f"| targets with no valid answer | {len(s['no_valid_answer'])} ({' '.join(s['no_valid_answer']) or 'none'}) |"]
    if s["no_valid_answer"]:
        L.append(f"| detection over valid answers only | {s['official']} of {s['variants_valid']} = {pct(s['detection_rate_valid_only'])} |")
        L.append(f"| false positives over valid answers only | {s['false_positives']} of {s['clean_valid']} = {pct(s['false_positive_rate_valid_only'])} |")
    if calls:
        tin = sum(c.get("input_tokens", 0) for c in calls.values())
        tout = sum(c.get("output_tokens", 0) for c in calls.values())
        usd = sum(c.get("cost_usd", 0.0) for c in calls.values())
        sec = sum(c.get("seconds", 0.0) for c in calls.values())
        cut = sum(1 for c in calls.values() if c.get("truncated"))
        L += [f"| LLM calls (cut off) | {len(calls)} ({cut}) |", f"| input / output tokens | {tin:,} / {tout:,} |",
              f"| cost USD | ${usd:.4f} |", f"| model time (seconds) | {sec:.0f} |"]
    L += ["", "## Variants", "",
          "| target | status | official | strict | rules flagged (HIGH/MEDIUM) | matched finding |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r["kind"] != "variant":
            continue
        m = r["matched"]
        mt = f"{m['rule']} {m['severity']}: {m['where'][:60]}" if m else ""
        L.append(f"| {r['target']} | {r['status']} | {'yes' if r['official'] else 'no'} | {'yes' if r['strict'] else 'no'} | "
                 f"{' '.join(r['rules_flagged']) or '-'} | {mt} |")
    L += ["", "## Clean targets", "",
          "| target | status | false positive | rules flagged (HIGH/MEDIUM) | first serious finding |", "|---|---|---|---|---|"]
    for r in rows:
        if r["kind"] != "clean":
            continue
        m = r["matched"]
        mt = f"{m['rule']} {m['severity']}: {m['where'][:60]}" if m else ""
        L.append(f"| {r['target']} | {r['status']} | {'YES' if r['false_positive'] else 'no'} | "
                 f"{' '.join(r['rules_flagged']) or '-'} | {mt} |")
    bad = {t: n for t, n in notes.items() if n}
    if bad:
        L += ["", "## Notes from the parser", ""]
        L += [f"- {t}: {'; '.join(n)}" for t, n in bad.items()]
    L += ["", "## How to read this", "",
          "- The reviewer reads the code and setup of each target and lists rule breaks without running anything.",
          "- Official detection needs a HIGH or MEDIUM finding on a linked rule. Strict detection also needs a word that names the changed code.",
          "- A clean target with any HIGH or MEDIUM finding counts as a false positive.",
          "- An empty, cut-off or invalid answer is never counted as 'no findings'.",
          "- Stock-gap findings describe the twin-signature gap (S03 in Phase 3), a real gap of the ONCHAINID dependency that is not a seeded variant. "
          "Phase 3 kept it out of the detection and false-positive measures, so the adjusted rows ignore these findings. "
          "The rule was fixed after the first real answer and before the other answers existed. A finding that mixes S03 with a real bug would be dropped from the adjusted rows, which is the cautious direction."]
    Path(out, "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_csv(out, rows, calls):
    with open(Path(out, "scores.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target", "kind", "status", "findings", "serious", "official", "strict", "flagged_any",
                    "false_positive", "rules_flagged", "official_adj", "strict_adj", "false_positive_adj", "stock_gap_findings", "input_tokens", "output_tokens", "cost_usd", "seconds"])
        for r in rows:
            c = calls.get(r["target"], {})
            w.writerow([r["target"], r["kind"], r["status"], r["findings"], r["serious"], int(r["official"]),
                        int(r["strict"]), int(r["flagged_any"]), int(r["false_positive"]), " ".join(r["rules_flagged"]),
                        int(r["official_adj"]), int(r["strict_adj"]), int(r["false_positive_adj"]), r["stock_gap_findings"],
                        c.get("input_tokens", ""), c.get("output_tokens", ""), c.get("cost_usd", ""), c.get("seconds", "")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="run folder, e.g. results/review_r1_haiku")
    ap.add_argument("--keywords", default=str(KEYWORDS_FILE))
    ap.add_argument("--manifest", default=str(MANIFEST_FILE))
    a = ap.parse_args()
    d = Path(a.dir)
    if not (d / "raw").is_dir():
        sys.exit(f"no raw/ folder in {d}")
    kw = load_json(a.keywords)
    entries = load_json(a.manifest)["configs"]
    rules = load_json(POLICY_FILE)["rules"]
    calls = load_json(d / "calls.json") if (d / "calls.json").exists() else {}
    answers = {}
    for e in entries:
        f = d / "raw" / f"{e['id']}.txt"
        if f.exists():
            answers[e["id"]] = {"text": f.read_text(encoding="utf-8"),
                                "truncated": bool(calls.get(e["id"], {}).get("truncated"))}
    rows, notes, found = score_all(answers, kw, entries, rules)
    s = summarize(rows)
    write_report(d, d.name, rows, notes, s, calls)
    write_csv(d, rows, calls)
    Path(d, "findings.json").write_text(json.dumps(
        {r["target"]: {"status": r["status"], "notes": notes[r["target"]], "findings": found[r["target"]]} for r in rows},
        indent=1), encoding="utf-8")
    print(f"{d.name}: variants official {s['official']}/{s['variants']}, strict {s['strict']}/{s['variants']}; "
          f"clean false positives {s['false_positives']}/{s['clean']}; no valid answer: {len(s['no_valid_answer'])}")
    print(f"wrote {d}/report.md, scores.csv, findings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())