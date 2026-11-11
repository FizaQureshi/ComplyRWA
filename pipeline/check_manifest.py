"""Check pipeline/configs.json against the Solidity files (Phase 4, step 4.0).

Uses only the Python standard library, so it runs on any Python 3.
Run from the ComplyRWA folder:   python pipeline/check_manifest.py
Optional:                        python pipeline/check_manifest.py --root path/to/ComplyRWA

It checks text only. It does NOT compile anything: forge test is the real proof.
Checks:
  1. 8 clean + 13 variant entries, ids C01..C08 and V01..V13, no duplicates.
  2. Each cfg contract exists in its file as `abstract contract X is ComplyFixture`.
  3. The hooks listed in the manifest equal the hooks the contract really overrides.
  4. Each gold suite contract exists in its test file.
  5. Every Cfg contract in the two config files is listed in the manifest (no orphans).
  6. Linked tests of variants are valid table columns.
"""
import json
import re
import sys
from pathlib import Path


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def contract_body(text, name):
    """Return the text between the braces of `abstract contract <name> is ComplyFixture {`, or None."""
    m = re.search(r"abstract\s+contract\s+" + re.escape(name) + r"\s+is\s+ComplyFixture\s*\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def main(root):
    errors = []
    manifest = json.loads((root / "pipeline" / "configs.json").read_text(encoding="utf-8"))
    columns = set(manifest["columns"])
    configs = manifest["configs"]

    ids = [c["id"] for c in configs]
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids in manifest")
    want = [f"C{n:02d}" for n in range(1, 9)] + [f"V{n:02d}" for n in range(1, 14)]
    if sorted(ids) != sorted(want):
        errors.append(f"ids differ from C01..C08 + V01..V13: {sorted(set(want) ^ set(ids))}")

    file_cache = {}

    def read(rel):
        if rel not in file_cache:
            p = root / rel
            file_cache[rel] = strip_comments(p.read_text(encoding="utf-8")) if p.exists() else None
        return file_cache[rel]

    listed = {}
    for c in configs:
        cid, cfg, cfile = c["id"], c["cfg_contract"], c["cfg_file"]
        listed.setdefault(cfile, set()).add(cfg)
        text = read(cfile)
        if text is None:
            errors.append(f"{cid}: file not found: {cfile}")
            continue
        body = contract_body(text, cfg)
        if body is None:
            errors.append(f"{cid}: `abstract contract {cfg} is ComplyFixture` not found in {cfile}")
        else:
            real = set(re.findall(r"function\s+(_\w+)\s*\([^)]*\)\s+internal\s+virtual\s+override", body))
            claimed = {h["name"] for h in c["hooks"]}
            if real != claimed:
                errors.append(f"{cid}: hooks differ. in code: {sorted(real)}  in manifest: {sorted(claimed)}")
        for kind, s in c["gold_suites"].items():
            t = read(s["file"])
            if t is None:
                errors.append(f"{cid}: test file not found: {s['file']}")
            elif not re.search(r"\bcontract\s+" + re.escape(s["contract"]) + r"\b", t):
                errors.append(f"{cid}: {kind} contract {s['contract']} not found in {s['file']}")
        for t in c.get("linked_tests", []):
            if t not in columns:
                errors.append(f"{cid}: linked test {t} is not a table column")

    for cfile, names in listed.items():
        text = read(cfile) or ""
        found = set(re.findall(r"abstract\s+contract\s+(Cfg\w+)\s+is\s+ComplyFixture", text))
        if found != names:
            errors.append(f"{cfile}: contracts differ. in file only: {sorted(found - names)}  in manifest only: {sorted(names - found)}")

    if errors:
        print("MANIFEST CHECK FAILED")
        for e in errors:
            print(" -", e)
        return 1
    n_clean = sum(c["kind"] == "clean" for c in configs)
    n_var = sum(c["kind"] == "variant" for c in configs)
    n_suites = sum(len(c["gold_suites"]) for c in configs)
    print(f"MANIFEST OK: {n_clean} clean + {n_var} variants, {n_suites} gold suites, all hooks match the code")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    if "--root" in sys.argv:
        root = Path(sys.argv[sys.argv.index("--root") + 1]).resolve()
    sys.exit(main(root))
