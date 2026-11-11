"""ComplyRWA executor (Phase 4, step 4.1).

Runs one or more Foundry test contracts on every configuration (C01..C08, V01..V13)
listed in pipeline/configs.json, and writes the same table as scripts/make_table.py.

How it works
  1. For each test contract and each configuration it writes a small wrapper contract
       contract Gen_<Test>_<ConfigID> is <Test>, <CfgContract> { ...overrides... }
     into test/generated/Wrappers.t.sol. The overrides come from the manifest hooks.
  2. It deletes cache/invariant (stale fuzz failures), then runs forge test on the
     wrappers only, with the settings from foundry.toml (same fuzz seed).
  3. It feeds the log to make_table.py, so parsing and verdicts are the Phase 3 ones.
  4. It deletes the wrappers again (unless --keep), so plain `forge test` still gives
     the Phase 3 counts.

Which configurations a test contract runs on
  A test contract that has `invariant_` functions is an "invariants" suite. Any other
  test contract is a "scenarios" suite. It runs only on configurations whose manifest
  entry lists that kind under gold_suites (scenario suites assume an empty start state,
  so C03, C04, C07 and V11 have none).

Limits (step 4.1)
  - Test names must look like test_G01a_... or invariant_G01a_..., because the table
    parser from make_table.py only knows those. Widening this belongs to step 4.2/4.5.
  - The test contract must define setUp itself or inherit it from ComplyFixture,
    and must not override fixture hooks (names starting with "_").

Usage (from the ComplyRWA folder, in Git Bash):
  python pipeline/executor.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest \
        test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/exec_gold
  python pipeline/executor.py --tests ... --dry-run      (write wrappers, do not run forge)
Options: --configs C01 V05 (subset), --keep (keep wrappers), --out DIR
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "test" / "generated"
sys.path.insert(0, str(ROOT / "scripts"))
import make_table  # noqa: E402  (Phase 3 parser and table writer)

WRAP_NAME = re.compile(r"Gen_\w+_([CV]\d\d)")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def contract_body(text, name):
    m = re.search(r"\bcontract\s+" + re.escape(name) + r"\b[^{]*\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def inspect_test(rel_path, name):
    p = ROOT / rel_path
    if not p.exists():
        sys.exit(f"ERROR: test file not found: {rel_path}")
    body = contract_body(strip_comments(p.read_text(encoding="utf-8")), name)
    if body is None:
        sys.exit(f"ERROR: contract {name} not found in {rel_path}")
    kind = "invariants" if re.search(r"function\s+invariant\w*\s*\(", body) else "scenarios"
    has_setup = bool(re.search(r"function\s+setUp\s*\(", body))
    bad = re.findall(r"function\s+(_\w+)\s*\([^)]*\)[^{;]*\boverride\b", body)
    if bad:
        sys.exit(f"ERROR: {name} overrides fixture hooks {bad}; the executor cannot wrap it.")
    return kind, has_setup


def hook_override(h, cfg_contract):
    sig = f"function {h['name']}({h['params']}) internal override(ComplyFixture, {cfg_contract})"
    call = f"{cfg_contract}.{h['name']}({h['args']})"
    if h["returns"]:
        return f"    {sig} returns ({h['returns']}) {{ return {call}; }}"
    return f"    {sig} {{ {call}; }}"


def make_wrapper(test, cfg, has_setup):
    name = f"Gen_{test}_{cfg['id']}"
    lines = [f"contract {name} is {test}, {cfg['cfg_contract']} {{"]
    if has_setup:
        lines.append(f"    function setUp() public override({test}, ComplyFixture) {{ {test}.setUp(); }}")
    lines += [hook_override(h, cfg["cfg_contract"]) for h in cfg["hooks"]]
    lines.append("}")
    return "\n".join(lines)


def rel_import(target):
    r = os.path.relpath(ROOT / target, GEN).replace("\\", "/")
    return r if r.startswith(".") else "./" + r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", nargs="+", required=True, help="path/File.t.sol:ContractName")
    ap.add_argument("--configs", nargs="*", help="subset of configuration ids")
    ap.add_argument("--out", default="results/exec")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    manifest = json.loads((ROOT / "pipeline" / "configs.json").read_text(encoding="utf-8"))
    configs = [c for c in manifest["configs"] if not a.configs or c["id"] in a.configs]

    files, blocks, n_wrappers = [], [], 0
    for spec in a.tests:
        path, test = spec.rsplit(":", 1)
        kind, has_setup = inspect_test(path, test)
        files.append(path)
        for cfg in configs:
            if kind not in cfg["gold_suites"]:
                continue
            blocks.append(make_wrapper(test, cfg, has_setup))
            n_wrappers += 1
        print(f"{test}: kind={kind}, setUp={'own' if has_setup else 'inherited'}")

    imports = sorted(set(files) | {c["cfg_file"] for c in configs})
    src = ["// SPDX-License-Identifier: GPL-3.0", "pragma solidity 0.8.17;", ""]
    src += [f'import "{rel_import(f)}";' for f in imports]
    src += ["", "// GENERATED by pipeline/executor.py. Do not edit. Deleted after each run.", ""]
    src += [b + "\n" for b in blocks]

    GEN.mkdir(parents=True, exist_ok=True)
    for old in GEN.glob("*.sol"):
        old.unlink()
    (GEN / "Wrappers.t.sol").write_text("\n".join(src), encoding="utf-8")
    print(f"Wrote {n_wrappers} wrappers to test/generated/Wrappers.t.sol")
    if a.dry_run:
        return 0

    out = (ROOT / a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(ROOT / "cache" / "invariant", ignore_errors=True)
    forge = shutil.which("forge")
    if not forge:
        sys.exit("ERROR: forge not found on PATH (add ~/.foundry/bin).")
    try:
        t0 = time.perf_counter()
        proc = subprocess.run([forge, "test", "--match-path", "test/generated/*"],
                              cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        seconds = time.perf_counter() - t0
    finally:
        if not a.keep:
            for old in GEN.glob("*.sol"):
                old.unlink()

    log = out / "forge.log"
    log.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if "Ran " not in proc.stdout:
        print("ERROR: forge did not run any tests (probably a compile error). Last lines:")
        print("\n".join((proc.stdout + proc.stderr).splitlines()[-40:]))
        return 2

    # Reuse the Phase 3 parser and table writer; only the suite-name mapping is new.
    make_table.cfg_of = lambda n: (WRAP_NAME.fullmatch(n).group(1) if WRAP_NAME.fullmatch(n) else None)
    cwd = os.getcwd()
    os.chdir(out)
    try:
        make_table.main([str(log)])
    finally:
        os.chdir(cwd)
    for ext in ("csv", "md"):
        shutil.move(str(out / "results" / f"variant_table.{ext}"), str(out / f"table.{ext}"))
    shutil.rmtree(out / "results", ignore_errors=True)

    (out / "run_info.json").write_text(json.dumps(
        {"tests": a.tests, "wrappers": n_wrappers, "seconds": round(seconds, 2)}, indent=2))
    print(f"Wrappers run: {n_wrappers}   forge time (with compile): {seconds:.1f} s")
    print(f"Table: {a.out}/table.md and table.csv   Log: {a.out}/forge.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
