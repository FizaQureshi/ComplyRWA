"""ComplyRWA validity filter (Phase 4, step 4.2).

Takes candidate Foundry test contracts (hand-written now, LLM-written from step 4.5),
runs them on all 21 configurations through pipeline/executor.py, and gives every test
function one outcome:

  REJECT   the contract does not compile, or the test fails on a clean configuration
           (C01..C08), or it produced no result. A correct test must pass on clean setups.
  VACUOUS  it passes on every clean configuration and on EVERY variant it ran on, so it
           never detects any of the seeded bugs. This is "unproven", not necessarily wrong:
           the rule it guards may simply not be broken by any of the 13 variants.
  KEEP     it passes on every clean configuration and fails on at least one variant.

Notes recorded next to the outcome (they do not change it):
  - "no visible assertion": no assert*/require/expectRevert/revert in the test body or in a
    helper function of the same contract (an assertion in another contract, such as a
    handler, is not seen).
  - "ran on x/8 clean, y/13 variants": scenario tests skip configurations whose start state
    has balances (C03, C04, C07, V11).

Compile errors: all candidates are first run together. If forge cannot compile, every
candidate is run alone, so a broken file is rejected without hiding the good ones.

Usage (from the ComplyRWA folder, in Git Bash):
  python pipeline/validity_filter.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest \
        test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/filter_gold
Candidate test files must NOT be under test/ (forge would compile them on every run).
Put them in candidates/<batch>/ and import the fixture as "../../test/ComplyFixture.sol".

Outputs in --out: report.md, report.csv, report.json, matrix.csv (test x configuration),
and one sub-folder per executor run (forge.log, run_info.json).
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import executor  # noqa: E402  (reuses strip_comments and contract_body)

MANIFEST = json.loads((HERE / "configs.json").read_text(encoding="utf-8"))
CFG_IDS = [c["id"] for c in MANIFEST["configs"]]
KIND = {c["id"]: c["kind"] for c in MANIFEST["configs"]}
N_CLEAN = sum(k == "clean" for k in KIND.values())
N_VAR = sum(k == "variant" for k in KIND.values())

# ---- forge log parsing (formats taken from results/exec_gold/forge.log) ----
RAN = re.compile(r"(?:Ran \d+ tests? for|failing tests? in) \S+?:(\w+)")
INV = re.compile(r"^\s*(\w+) invariants[:\s(]")
RES = re.compile(r"^\[(PASS|FAIL)(?::\s*(.*?))?\]\s+((?:test|invariant)\w*)")
WRAP = re.compile(r"Gen_(\w+)_([CV]\d\d)")


def parse_log(path, results, reasons):
    """results[(test_contract, test_name, config)] = PASS or FAIL (FAIL always wins)."""
    cur = None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = RAN.search(line) or INV.match(line)
        if m:
            w = WRAP.fullmatch(m.group(1))
            cur = (w.group(1), w.group(2)) if w else None
            continue
        m = RES.match(line)
        if m and cur:
            status, reason, test = m.groups()
            key = (cur[0], test, cur[1])
            if results.get(key) != "FAIL":
                results[key] = status
                if status == "FAIL":
                    reasons[key] = (reason or "").strip()


# ---- static look at the test source ----
ASSERT = re.compile(r"\bassert\w*\s*\(|\brequire\s*\(|\bvm\.expectRevert|\brevert\b")


def all_functions(body):
    out = {}
    for m in re.finditer(r"function\s+(\w+)\s*\([^)]*\)[^{;]*\{", body):
        depth, i = 1, m.end()
        while i < len(body) and depth:
            depth += {"{": 1, "}": -1}.get(body[i], 0)
            i += 1
        out[m.group(1)] = body[m.end():i - 1]
    return out


def static_info(spec):
    """Return {test_name: assertion_visible} for the test functions written in the contract."""
    path, name = spec.rsplit(":", 1)
    text = executor.strip_comments((ROOT / path).read_text(encoding="utf-8"))
    body = executor.contract_body(text, name) or ""
    funcs = all_functions(body)
    info = {}
    for fn, txt in funcs.items():
        if not re.match(r"(test|invariant)", fn):
            continue
        calls = set(re.findall(r"\b(\w+)\s*\(", txt))
        visible = bool(ASSERT.search(txt)) or any(
            c in funcs and c != fn and ASSERT.search(funcs[c]) for c in calls)
        info[fn] = visible
    return info


# ---- running the executor ----
def run_executor(specs, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(HERE / "executor.py"), "--tests", *specs, "--out", str(outdir)]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout + "\n" + p.stderr)


def safe(spec):
    return re.sub(r"\W+", "_", spec)


# ---- classification ----
def classify(test_key, results, reasons, visible):
    tc, tn = test_key
    ran = {c: results[(tc, tn, c)] for c in CFG_IDS if (tc, tn, c) in results}
    clean = {c: s for c, s in ran.items() if KIND[c] == "clean"}
    var = {c: s for c, s in ran.items() if KIND[c] == "variant"}
    notes = []
    if visible is False:
        notes.append("no visible assertion")
    notes.append(f"ran on {len(clean)}/{N_CLEAN} clean, {len(var)}/{N_VAR} variants")
    bad_clean = [c for c, s in clean.items() if s == "FAIL"]
    if not clean:
        return "REJECT", "no result on any clean configuration", [], notes, ran
    if bad_clean:
        why = reasons.get((tc, tn, bad_clean[0]), "")
        return "REJECT", f"fails on clean: {' '.join(bad_clean)}" + (f" ({why})" if why else ""), [], notes, ran
    killed = [c for c, s in var.items() if s == "FAIL"]
    if killed:
        return "KEEP", f"fails on variants: {' '.join(killed)}", killed, notes, ran
    return "VACUOUS", f"passes on all {len(var)} variants it ran on", [], notes, ran


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", nargs="+", required=True, help="path/File.sol:ContractName")
    ap.add_argument("--out", default="results/filter")
    a = ap.parse_args()
    out = (ROOT / a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    groups, whole_rejects, exec_seconds = [], [], 0.0
    rc, text = run_executor(a.tests, out / "joint")
    if rc == 0:
        groups.append((a.tests, out / "joint"))
    else:
        print(f"Joint run failed (exit {rc}); running each candidate alone.")
        for spec in a.tests:
            d = out / safe(spec)
            rc_i, txt = run_executor([spec], d)
            if rc_i == 0:
                groups.append(([spec], d))
            else:
                reason = "does not compile" if rc_i == 2 else "executor refused it"
                whole_rejects.append((spec, reason, " | ".join(txt.strip().splitlines()[-6:])[:400]))

    results, reasons = {}, {}
    for specs, d in groups:
        parse_log(d / "forge.log", results, reasons)
        info = d / "run_info.json"
        if info.exists():
            exec_seconds += json.loads(info.read_text())["seconds"]

    rows = []   # (contract, test, outcome, reason, notes, ran)
    for specs, _ in groups:
        for spec in specs:
            tc = spec.rsplit(":", 1)[1]
            st = static_info(spec)
            names = sorted(set(st) | {t for (c, t, _) in results if c == tc})
            if not names:
                rows.append((tc, "(none)", "REJECT", "no test functions found", [], {}))
            for tn in names:
                o, why, _, notes, ran = classify((tc, tn), results, reasons, st.get(tn))
                rows.append((tc, tn, o, why, notes, ran))
    for spec, reason, excerpt in whole_rejects:
        rows.append((spec.rsplit(":", 1)[1], "(whole contract)", "REJECT", reason, [excerpt], {}))

    # ---- write reports ----
    n = {o: sum(r[2] == o for r in rows) for o in ("KEEP", "VACUOUS", "REJECT")}
    total = len(rows)
    wall = time.perf_counter() - t0
    with open(out / "report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["contract", "test", "outcome", "reason", "notes"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], r[3], "; ".join(r[4])])
    with open(out / "matrix.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["contract", "test", "outcome"] + CFG_IDS)
        for r in rows:
            w.writerow([r[0], r[1], r[2]] + [{"PASS": "P", "FAIL": "F"}.get(r[5].get(c), "-") for c in CFG_IDS])
    with open(out / "report.md", "w", encoding="utf-8") as f:
        f.write("| contract | test | outcome | reason | notes |\n|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {'; '.join(r[4])} |\n")
    summary = {"tests": total, **n, "valid_not_rejected": n["KEEP"] + n["VACUOUS"],
               "valid_and_non_vacuous": n["KEEP"], "executor_seconds": round(exec_seconds, 1),
               "wall_seconds": round(wall, 1)}
    (out / "report.json").write_text(json.dumps(
        {"summary": summary, "rows": [
            {"contract": r[0], "test": r[1], "outcome": r[2], "reason": r[3], "notes": r[4]} for r in rows]},
        indent=2), encoding="utf-8")

    print(f"Tests judged: {total}")
    print(f"  KEEP    (valid, kills a variant):  {n['KEEP']}")
    print(f"  VACUOUS (valid, kills nothing):    {n['VACUOUS']}")
    print(f"  REJECT  (does not compile / fails on clean): {n['REJECT']}")
    if total:
        print(f"  valid (not rejected):          {n['KEEP'] + n['VACUOUS']} of {total} = {100 * (n['KEEP'] + n['VACUOUS']) / total:.0f}%")
        print(f"  valid and non-vacuous (KEEP):  {n['KEEP']} of {total} = {100 * n['KEEP'] / total:.0f}%")
    print(f"Time: executor {exec_seconds:.1f} s (with compile), whole filter {wall:.1f} s")
    for r in rows:
        if r[2] != "KEEP":
            print(f"  {r[2]:8} {r[0]}.{r[1]}: {r[3]}")
    print(f"Reports: {a.out}/report.md, report.csv, matrix.csv, report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
