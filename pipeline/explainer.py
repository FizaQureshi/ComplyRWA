#!/usr/bin/env python3
"""ComplyRWA step 4.6: turn failing generated tests into short audit findings.

Input : results/filter_<batch>/joint/forge.log  (which test failed on which configuration)
        candidates/<batch>/Cand_<rule>_<batch>.sol  (the test source)
        pipeline/prompts/explainer.md  (the prompt)
One finding per (configuration, rule): all failing tests of that rule on that configuration go
into ONE call, so three failing tests with one root cause give one finding, not three.

Modes of the configuration description:
  blind  (default) the model is NOT told what the configuration changes. This is what a real audit knows.
  reveal (--reveal-config) the model gets the description from configs.json (leaks the answer; use it
         only to compare how much the explanation improves when the cause is known).

Automatic checks on every answer (warnings, never hidden):
  format    first line has a severity, the five headings appear in order, at most 250 words
  grounding every `backticked` function name in the answer appears in the input given to the model

  python pipeline/explainer.py --mode mock --batch d1 --configs V05
  python pipeline/explainer.py --mode live --model haiku --batch d1 e1 --configs V05 V12
  python pipeline/explainer.py --mode live --model haiku --batch d1 e1                 (all variants)
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(PIPE))
import llm  # noqa: E402
import prompts  # noqa: E402

KNOWN_EXCEPTIONS = """- An agent's forcedTransfer to a restricted country succeeds on purpose (it skips the read-side compliance check). Label it INFO, never HIGH.
- Moving tokens between two wallets of the same identity can be rejected by the cap check even when the net change is zero. That rejection is expected, not a finding."""

BLIND_TEXT = ("Not provided. The audit tool did not tell you what this configuration changes. "
              "Say only what the test and the failure output show; if the cause is not visible, say it is not known.")

HEADINGS = ["Violated policy", "What went wrong", "Affected functions", "How to reproduce", "Suggested fix"]
RAN = re.compile(r"^Ran \d+ tests? for \S+?:(Gen_\S+)")
FAIL = re.compile(r"^\[FAIL(?:: (.*))?\] (\w+)\(")
WRAP = re.compile(r"Gen_Cand_([A-Z]\d)_([A-Za-z0-9]+)_([CV]\d\d)")


def parse_failures(batch):
    """[(rule, cfg, test, reason)] from the 'Ran ... tests' blocks (the 'Encountered' summary is skipped)."""
    log = RESULTS / f"filter_{batch}" / "joint" / "forge.log"
    if not log.exists():
        sys.exit(f"missing {log} (the filter must have run jointly for this batch)")
    out, cur = [], None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RAN.match(line)
        if m:
            cur = m.group(1)
            continue
        if line.startswith(("Encountered", "Suite result")):
            cur = None
            continue
        f = FAIL.match(line)
        if f and cur:
            w = WRAP.fullmatch(cur)
            if w and w.group(2) == batch:
                out.append((w.group(1), w.group(3), f.group(2), (f.group(1) or "").strip()))
    return out


def split_functions(src):
    """name -> source text (with the comment lines just above it), found by brace matching."""
    funcs = {}
    lines = src.splitlines(keepends=True)
    offsets, pos = [], 0
    for l in lines:
        offsets.append(pos)
        pos += len(l)
    for m in re.finditer(r"function\s+(\w+)\s*\(", src):
        i = src.find("{", m.end())
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        line_no = max(k for k, o in enumerate(offsets) if o <= m.start())
        k = line_no
        while k > 0 and lines[k - 1].strip().startswith("//"):
            k -= 1
        funcs[m.group(1)] = src[offsets[k]:j + 1]
    return funcs


def load_descriptions():
    data = json.loads((PIPE / "configs.json").read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else [e for v in data.values() if isinstance(v, list) for e in v]
    return {e["id"]: e.get("description", "") for e in entries if isinstance(e, dict) and "id" in e}


def check_format(text):
    problems = []
    first = next((l for l in text.splitlines() if l.strip()), "")
    if not re.search(r"\b(HIGH|MEDIUM|INFO)\b", first):
        problems.append("first line has no severity (HIGH, MEDIUM or INFO)")
    pos = 0
    for h in HEADINGS:
        m = re.search(re.escape(h), text[pos:], re.I)
        if not m:
            problems.append(f"heading missing or out of order: {h}")
            break
        pos += m.end()
    words = len(re.findall(r"\S+", text))
    if words > 250:
        problems.append(f"{words} words (limit 250)")
    return problems


def check_grounding(text, source):
    """Backticked names that never appear in what the model was given."""
    bad = []
    for tok in sorted(set(re.findall(r"`([^`\n]+)`", text))):
        m = re.match(r"^[\w.]*?(\w+)\s*(\(.*)?$", tok.strip())
        if not m:
            continue
        name = m.group(1)
        if name.isdigit() or len(name) < 3:
            continue
        if name not in source:
            bad.append(tok)
    return bad


def severity(text):
    first = next((l for l in text.splitlines() if l.strip()), "")
    m = re.search(r"\b(HIGH|MEDIUM|INFO)\b", first)
    return m.group(1) if m else "?"


def main():
    cfg = llm.load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", nargs="+", required=True, help="generation batches, e.g. d1 e1")
    ap.add_argument("--configs", nargs="+", default=None, help="e.g. V05 V12 (default: every variant that failed)")
    ap.add_argument("--reveal-config", action="store_true")
    ap.add_argument("--model", default=cfg.get("default_model", "haiku"))
    ap.add_argument("--mode", default=cfg.get("default_mode", "mock"), choices=["mock", "replay", "live"])
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--cap", type=float, default=None)
    a = ap.parse_args()

    groups = defaultdict(list)
    for b in a.batch:
        for rule, c, test, reason in parse_failures(b):
            if c.startswith("C"):
                print(f"warning: {test} failed on CLEAN configuration {c} in batch {b} (not explained)")
                continue
            if a.configs and c not in a.configs:
                continue
            groups[(c, rule, b)].append((test, reason))
    if not groups:
        sys.exit("no failing tests found for the chosen batches and configurations")

    descs = load_descriptions() if a.reveal_config else {}
    client = llm.LLMClient(a.mode, a.cap)
    mode_name = "reveal" if a.reveal_config else "blind"
    outdir = RESULTS / f"explain_{'+'.join(a.batch)}_{mode_name}"
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"{len(groups)} finding(s) to explain, mode {a.mode}, model {llm.resolve_model(a.model, cfg)}, config text: {mode_name}\n")

    rows, blocks = [], defaultdict(list)
    for (c, rule, b), fails in sorted(groups.items()):
        name = f"Cand_{rule}_{b}"
        funcs = split_functions((ROOT / "candidates" / b / f"{name}.sol").read_text(encoding="utf-8"))
        failing = [t for t, _ in fails]
        parts = [funcs[t] for t in failing if t in funcs]
        parts += [src for n, src in funcs.items() if not n.startswith("test")]      # helpers the tests call
        test_source = "\n\n".join(parts)
        failure_log = "\n".join(f"[FAIL: {r}] {t}()" if r else f"[FAIL] {t}()" for t, r in fails)
        failure_log += "\n(These are plain scenario tests: forge printed no call sequence. Steps come from the test source.)"
        description = descs.get(c, "(no description found)") if a.reveal_config else BLIND_TEXT
        system, user = llm.render(
            "explainer", KNOWN_EXCEPTIONS=KNOWN_EXCEPTIONS, RULE_ID=rule, POLICY_TEXT=prompts.RULE_TEXT.get(rule, rule),
            CONFIG_ID=c, CONFIG_DESCRIPTION=description, TEST_SOURCE=test_source, FAILURE_LOG=failure_log,
            FIXTURE_FACTS=(PIPE / "fixture_facts.md").read_text(encoding="utf-8"))
        tag = f"explainer:{rule}:{c}:{b}:{mode_name}"
        r = client.complete(system, user, model=a.model, max_tokens=a.max_tokens, tag=tag)
        text = r.text.strip()
        fmt = check_format(text) + (["answer was cut by max_tokens"] if r.truncated else [])
        gnd = check_grounding(text, system + user)
        (outdir / f"{rule}_{c}_{b}.md").write_text(text + "\n", encoding="utf-8")
        sev = severity(text)
        print(f"{c} {rule} ({b}): {len(fails)} failing test(s), severity {sev}, {r.output_tokens} out tokens, "
              f"${r.original_cost_usd:.4f}{' (cached)' if r.cached else ''}")
        for p in fmt:
            print(f"    format: {p}")
        for g in gnd:
            print(f"    not in the input: {g}")
        rows.append({"config": c, "rule": rule, "batch": b, "failing_tests": len(fails), "severity": sev,
                     "format_problems": "; ".join(fmt), "ungrounded": "; ".join(gnd),
                     "out_tokens": r.output_tokens, "cost_usd": round(r.original_cost_usd, 6)})
        note = ""
        if fmt or gnd:
            note = "\n\n> Automatic checks: " + "; ".join(fmt + [f"not in input: {g}" for g in gnd])
        blocks[c].append(f"### Rule {rule} (tests from batch {b}: {', '.join(failing)})\n\n{text}{note}\n")

    report = [f"# ComplyRWA audit findings ({mode_name} configuration text)\n",
              "| configuration | rule | severity | failing tests | checks |", "|---|---|---|---|---|"]
    for w in rows:
        ok = "ok" if not (w["format_problems"] or w["ungrounded"]) else "see note"
        report.append(f"| {w['config']} | {w['rule']} | {w['severity']} | {w['failing_tests']} | {ok} |")
    for c in sorted(blocks):
        report.append(f"\n## Configuration {c}\n")
        report.extend(blocks[c])
    (outdir / "audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    with open(outdir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    clean = sum(1 for w in rows if not (w["format_problems"] or w["ungrounded"]))
    print(f"\n{len(rows)} finding(s); {clean} pass both automatic checks; cost of these answers ${sum(w['cost_usd'] for w in rows):.4f}")
    print(f"report: {outdir.relative_to(ROOT).as_posix()}/audit_report.md")
    print(client.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())