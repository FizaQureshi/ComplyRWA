#!/usr/bin/env python3
"""Step 4.7: end-to-end demo.
policy input -> generated property -> executed test -> counterexample -> audit report.
Reuses saved generator batches and filter results. Blind: never reads the config description."""
import argparse, csv, glob, json, os, re, subprocess, sys, time

POLICY = {
    "K1": "Only investors with a valid KYC claim from a trusted issuer may receive tokens.",
    "K3": "At least one KYC claim topic must be required.",
    "J1": "Investors registered in a restricted country may not receive tokens.",
    "H1": "No investor may hold more than the maximum allowed tokens.",
    "H3": "The holding-limit module's balance records must match the real token balances.",
}
CAUSE = {  # grouping by symptom (rule category), not by configuration
    "K": "KYC requirement missing or bypassed",
    "J": "Jurisdiction restriction not enforced",
    "H": "Holding limit not enforced or tracked wrongly",
}
LEDGER = "results/llm_ledger.jsonl"


def ledger_lines():
    if not os.path.exists(LEDGER):
        return 0
    with open(LEDGER, encoding="utf-8") as f:
        return sum(1 for _ in f)


def ledger_since(n):
    cost = orig = secs = 0.0
    calls = 0
    if not os.path.exists(LEDGER):
        return calls, cost, orig, secs
    with open(LEDGER, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < n or not line.strip():
                continue
            d = json.loads(line)
            calls += 1
            cost += d.get("cost_usd", 0) or 0
            orig += d.get("original_cost_usd", 0) or 0
            secs += d.get("seconds", 0) or 0
    return calls, cost, orig, secs


def read_matrix(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_fail_reasons(batch):
    """(rule, config, test) -> reason, from the saved forge log."""
    out = {}
    path = f"results/filter_{batch}/joint/forge.log"
    if not os.path.exists(path):
        return out
    wrapper = None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"(?:Ran|Encountered) .* (?:in|for) \S+:(Gen_\S+?)(?::|\s|$)", line)
        if m:
            wrapper = m.group(1)
        m = re.search(r"^(Gen_\S+) invariants", line)
        if m:
            wrapper = m.group(1)
        m = re.search(r"\[FAIL: (.*?)\] (test\w+)", line)
        if m and wrapper:
            w = re.match(r"Gen_Cand_([A-Z]\d)_\w+?_(C\d\d|V\d\d)$", wrapper)
            if w:
                out.setdefault((w.group(1), w.group(2), m.group(2)), m.group(1))
    return out


def test_source(batch, rule, test):
    for p in glob.glob(f"candidates/{batch}/*.sol"):
        txt = open(p, encoding="utf-8").read()
        if f"contract Cand_{rule}_{batch}" not in txt:
            continue
        m = re.search(r"function\s+" + re.escape(test) + r"\s*\(", txt)
        if not m:
            continue
        i = txt.index("{", m.start())
        depth = 0
        for j in range(i, len(txt)):
            depth += txt[j] == "{"
            depth -= txt[j] == "}"
            if depth == 0:
                return txt[m.start():j + 1]
    return None


def finding_files(folder, target):
    res = {}
    for p in glob.glob(os.path.join(folder, "*.md")):
        m = re.match(r"([A-Z]\d)_(V\d\d|C\d\d)_(\w+)\.md$", os.path.basename(p))
        if m and m.group(2) == target:
            text = open(p, encoding="utf-8").read()
            sev = re.search(r"Severity:\s*(\w+)", text)
            body = re.sub(r"^\s*\**Severity:\s*\w+\**\s*\n+", "", text, count=1)
            res[m.group(1)] = (sev.group(1) if sev else "HIGH", body.strip(), m.group(3))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="configuration being audited, e.g. V09")
    ap.add_argument("--batches", nargs="+", default=["d1", "d2"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--mode", default="live", choices=["mock", "replay", "live"])
    ap.add_argument("--skip-explain", action="store_true", help="reuse an existing explainer folder")
    ap.add_argument("--probe", default="results/filter_probe/matrix.csv")
    a = ap.parse_args()
    t0 = time.time()
    if not re.fullmatch(r"[CV]\d\d", a.target):
        sys.exit(f"invalid target {a.target}")
    for fn in ("report.md", "report.json"):
        old = os.path.join(f"results/demo_{a.target}", fn)
        if os.path.exists(old):
            os.remove(old)
    rules = list(POLICY)

    # stage 1: policy input
    print("[1/5] policy input:", ", ".join(rules))

    # stage 2+3: generated properties and their execution results on the target
    print("[2/5] generated properties from batches:", " ".join(a.batches))
    tests = {r: [] for r in rules}  # rule -> [(batch, test, result_on_target)]
    for b in a.batches:
        mp = f"results/filter_{b}/matrix.csv"
        if not os.path.exists(mp):
            sys.exit(f"missing {mp}: run the generator for batch {b} first")
        for row in read_matrix(mp):
            rule = row["contract"].split("_")[1]
            if rule in tests:
                if a.target not in row:
                    sys.exit(f"unknown configuration {a.target}")
                tests[rule].append((b, row["test"], row[a.target]))
    print("[3/5] executed tests on", a.target, "(from saved filter matrices)")

    # stage 4: counterexamples -> explainer
    before = ledger_lines()
    batches_tag = "+".join(a.batches)
    folder = f"results/explain_{batches_tag}_blind"
    anyfail = any(t[2] == "F" for r in rules for t in tests[r])
    if not anyfail:
        print("[4/5] no generated test failed on", a.target, "- explainer not needed")
    elif not a.skip_explain:
        cmd = [sys.executable, "pipeline/explainer.py", "--batch", *a.batches,
               "--configs", a.target, "--model", a.model, "--mode", a.mode]
        print("[4/5] explainer:", " ".join(cmd))
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout, end="")
        if r.returncode != 0:
            tail = (r.stderr.strip().splitlines() or ["no error text"])[-1]
            sys.exit(f"explainer failed (exit {r.returncode}): {tail}")
    else:
        print("[4/5] explainer skipped, using", folder)
    found = {k: v for k, v in finding_files(folder, a.target).items() if k in rules}
    calls, cost, orig, secs = ledger_since(before)

    reasons = {}
    for b in a.batches:
        reasons.update(parse_fail_reasons(b))

    # known exception probe
    info = None
    if os.path.exists(a.probe):
        for row in read_matrix(a.probe):
            if row["test"].startswith("test_J4") and row.get(a.target) == "P":
                info = ("INFO: J1 bypassed via forcedTransfer (agent-only path). "
                        "Classified as a known exception, not a vulnerability. "
                        "(Result of a fixed probe test, not generated from the policy.)")

    # stage 5: report
    print("[5/5] building report")
    status = {}
    for r in rules:
        ran = [t for t in tests[r] if t[2] in ("P", "F")]
        failed = [t for t in ran if t[2] == "F"]
        status[r] = (len(ran), len(failed))

    groups = {}
    for r in rules:
        if status[r][1] > 0:
            groups.setdefault(r[0], []).append(r)

    findings = {}
    L = [f"# ComplyRWA audit report: {a.target}", "",
         f"Audit target: configuration `{a.target}` (cause hidden from the auditor). "
         f"Model: {a.model}. Mode: {a.mode}.", "",
         "## 1. Policy input", "", "| Rule | Policy |", "|---|---|"]
    L += [f"| {r} | {POLICY[r]} |" for r in rules]
    L += ["", "## 2. Generated properties and execution results", "",
          "| Rule | Generated tests run | Failed | Status |", "|---|---|---|---|"]
    for r in rules:
        ran, fl = status[r]
        st = "FAIL" if fl else ("PASS" if ran else "NOT RUN")
        L.append(f"| {r} | {ran} | {fl} | {st} |")
    L += ["", "## 3. Findings grouped by symptom", ""]
    if not groups:
        L.append("No generated test failed on this configuration. No findings.")
    for cat, rs in groups.items():
        L += [f"### {CAUSE[cat]} ({', '.join(rs)})", ""]
        for r in rs:
            sev, text, b = found.get(r, ("UNKNOWN", "(explainer text not found)", ""))
            L += [f"#### Rule {r}: severity {sev}", "", text, ""]
            fl = [t for t in tests[r] if t[2] == "F"]
            side = 0
            ftests = []
            L.append("Failing tests and reasons:")
            for bb, name, _ in fl:
                why = reasons.get((r, a.target, name), "reason not found in log")
                tag = ""
                if r.startswith("H") and r != "H3" and re.search(r"\b0 != \d+", why):
                    tag = " (side effect: the module's counter did not move)"
                    side += 1
                if r == "H3" and any(status[k][1] for k in status if k.startswith("K")) \
                        and "tracked != real" not in why:
                    tag = " (side effect: a KYC failure let a transfer through)"
                    side += 1
                ftests.append({"name": name, "reason": why, "side_effect": bool(tag)})
                L.append(f"- `{name}`: {why}{tag}")
            L += ["", f"Direct evidence: {len(fl) - side} of {len(fl)} failing tests."]
            if r == "H3" and fl and side == len(fl):
                L += ["", "All failing H3 tests are side effects of the KYC failure above. "
                      "No separate holding-limit problem is shown."]
            if r == "H3" and fl and all(re.search(r"tracked != real: 0 != \d+", reasons.get((r, a.target, n), "")) for _, n, _ in fl):
                L += ["", "Symptom hint: the module's tracked balance stayed at 0 after real mints, so the module "
                      "is not being notified. Check that `compliance.getModules()` lists MaxBalanceModule."]
            if fl:
                named = re.findall(r"(test_\w+)", found.get(r, ("", "", ""))[1])
                pick = next((t for t in fl if t[1] in named), fl[0])
                src = test_source(pick[0], r, pick[1])
                if src:
                    L += ["", "Reproducible test (generated):", "", "```solidity", src, "```"]
                findings[r] = {"severity": sev, "text": text,
                               "direct_evidence": {"direct": len(fl) - side, "total": len(fl)},
                               "failing_tests": ftests, "reproducible_test": src}
            L.append("")
        if len(groups) > 1:
            pass
    if len(groups) > 1:
        L += ["Note: a finding can be a side effect of another group's problem. "
              "Grouping is by rule category, not by proven root cause.", ""]
    L += ["## 4. Known exceptions", ""]
    L.append(info or "Known-exception probe result not available.")
    L += ["", "## 5. Cost and time", "",
          f"- Explainer LLM calls this run: {calls}; cost paid ${cost:.4f}; "
          f"cost when first made ${orig:.4f}; model seconds {secs:.0f}",
          f"- Demo wall time: {time.time() - t0:.0f} s",
          "- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed)."]
    outdir = f"results/demo_{a.target}"
    os.makedirs(outdir, exist_ok=True)
    open(f"{outdir}/report.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    js = {"status": "ok", "target": a.target, "model": a.model, "mode": a.mode,
          "rules": {r: {"policy": POLICY[r], "tests_run": status[r][0], "failed": status[r][1],
                        "status": "FAIL" if status[r][1] else ("PASS" if status[r][0] else "NOT_RUN"),
                        "severity": found.get(r, ("UNKNOWN",))[0] if status[r][1] else None}
                    for r in rules},
          "groups": {CAUSE[c]: rs for c, rs in groups.items()},
          "info": [info] if info else [],
          "findings": findings,
          "cost": {"llm_calls": calls, "paid_usd": round(cost, 6), "first_made_usd": round(orig, 6),
                   "model_seconds": round(secs, 1), "wall_seconds": round(time.time() - t0, 1)}}
    json.dump(js, open(f"{outdir}/report.json", "w", encoding="utf-8"), indent=2)
    print("Wrote", f"{outdir}/report.md", "and report.json")
    print({r: ("FAIL" if status[r][1] else ("PASS" if status[r][0] else "NOT_RUN")) for r in rules})


def _write_error(msg):
    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--target")
    t, _ = pp.parse_known_args()
    if not t.target or not re.fullmatch(r"[CV]\d\d", t.target):
        return
    d = f"results/demo_{t.target}"
    os.makedirs(d, exist_ok=True)
    json.dump({"status": "error", "target": t.target, "step": "demo", "message": str(msg)},
              open(f"{d}/report.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            _write_error(e.code if isinstance(e.code, str) else f"exit code {e.code}")
        raise
    except Exception as e:
        _write_error(repr(e))
        raise
