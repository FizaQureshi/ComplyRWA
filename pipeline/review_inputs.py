#!/usr/bin/env python3
"""ComplyRWA step 4.8: build the input of the LLM-only review for each of the 21 targets.

For one target (C01..C08, V01..V13) the reviewer gets, as a real auditor would:
  POLICY  the 10 rule texts (same wording as the generator), the policy numbers of this target, definitions
  CODE    the pinned contracts, cut down to the functions the 10 rules need (the slicer is reused).
          For a code-copy variant (V01, V02, V03, V06, V10, V12) the copied file is cut instead of the stock
          file, and its name is changed back to the stock name.
  SETUP   the base deployment code (test/ComplyFixture.sol) and the overrides of this target
All comments are removed. Names and literals that would reveal the target are changed (see SANITIZE).
The reviewer never sees target ids, descriptions, gold tests or file names of variants.

  python pipeline/review_inputs.py --check          all 21 targets: builds, no leaks, no comments
  python pipeline/review_inputs.py --sizes          size and rough cost per target and model (free)
  python pipeline/review_inputs.py --show V05       print the whole prompt of one target

Other scripts use build_target(id) and all_target_ids().
"""
import argparse
import json
import re
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
import llm  # noqa: E402
import prompts  # noqa: E402
import slicer  # noqa: E402

POLICY_FILE = PIPE / "review_policy.json"
MANIFEST_FILE = PIPE / "configs.json"
EXTRA_UNITS_FILE = PIPE / "review_extra_units.json"

# Code-copy variants: (stock contract name, copied file, copied contract name, fixture hook that swaps it in).
# The swap hook is left out of the setup text: the reviewer sees the deployed contract under its stock name.
SWAPS = {
    "V01": ("IdentityRegistry", "variants/IdentityRegistryV01.sol", "IdentityRegistryV01", "_newIdentityRegistry"),
    "V02": ("ClaimIssuer", "variants/ClaimIssuerV02.sol", "ClaimIssuerV02", "_newClaimIssuer"),
    "V03": ("ClaimIssuer", "variants/ClaimIssuerV03.sol", "ClaimIssuerV03", "_newClaimIssuer"),
    "V06": ("IdentityRegistry", "variants/IdentityRegistryV06.sol", "IdentityRegistryV06", "_newIdentityRegistry"),
    "V10": ("MaxBalanceModule", "variants/MaxBalanceModuleV10.sol", "MaxBalanceModuleV10", "_maxBalanceImpl"),
    "V12": ("Token", "variants/TokenV12.sol", "TokenV12", "_newToken"),
}

# Fixture functions shown as the base setup (state variables are always shown).
BASE_SHOW = [
    "setUp", "_configure", "_deployRegistries", "_newIdentityRegistry", "_deployClaimIssuer", "_newClaimIssuer",
    "_deployComplianceAndToken", "_newToken", "_registerInvestors", "_wireModules", "_deployModules",
    "_maxBalanceImpl", "_addModules", "_configureModules", "_afterSetUp",
    "_issueClaim", "_issueClaimFrom", "_revokeClaim", "_mint", "_restrictCountry", "_setCap",
]

# Text changes applied to code and setup before the reviewer sees them (order matters).
SANITIZE = [
    (r"\bIdentityRegistryV\d\d\b", "IdentityRegistry"),
    (r"\bClaimIssuerV\d\d\b", "ClaimIssuer"),
    (r"\bMaxBalanceModuleV\d\d\b", "MaxBalanceModule"),
    (r"\bTokenV\d\d\b", "Token"),
    (r'"not-the-issuer"', '"second-key"'),
    (r"\bfakeKey\b", "secondKey"),
    (r"\bComplyFixture\b", "BaseSetup"),
    (r"\b[CV]\d\d:\s*", ""),
]

# Words that must not appear anywhere in a prompt.
LEAKS = [
    (r"\b[CV]\d\d\b", "target id"),
    (r"Cfg\w*", "config contract name"),
    (r"(?i)\bvariants?\b", "word 'variant'"),
    (r"(?i)\bbug\b", "word 'bug'"),
    (r"(?i)\bseeded\b|\bvulnerab\w*", "word 'seeded' or 'vulnerable'"),
    (r"\b\w+V\d\d\b", "name with a variant suffix"),
    (r"not-the-issuer|fakeKey", "revealing literal"),
    (r"ComplyFixture|ComplyRWA|(?i:\bgold\b)", "project or test name"),
]

# Rough guides for --sizes only (real input was about 1.5 times the characters / 4 estimate in step 4.4/4.5).
REAL_FACTOR = 1.6
OUT_ASSUMED = 4000


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest():
    return load_json(MANIFEST_FILE)["configs"]


def all_target_ids():
    return [c["id"] for c in manifest()]


def entry(tid):
    for c in manifest():
        if c["id"] == tid:
            return c
    raise KeyError(f"unknown target {tid}")


def sanitize(text):
    for pat, rep in SANITIZE:
        text = re.sub(pat, rep, text)
    return text


# ------------------------------------------------------------------ the three parts
def union_units(smap, rules):
    """All units of all rules, merged per (file, contract), first-seen order."""
    merged = {}
    for r in rules:
        for key, m in slicer.rule_units(smap, r).items():
            d = merged.setdefault(key, {"functions": [], "state": True})
            for f in m["functions"]:
                if f not in d["functions"]:
                    d["functions"].append(f)
            d["state"] = d["state"] and m["state"]
    return merged


def build_policy(tid):
    pol = load_json(POLICY_FILE)
    nums = {**pol["default"], **pol.get("overrides", {}).get(tid, {})}
    lines = ["Rules:"]
    lines += [f"{r}: {prompts.RULE_TEXT[r]}" for r in pol["rules"]]
    lines += ["", "Numbers:",
              "- Restricted countries (ISO 3166-1 numeric): " + ", ".join(str(x) for x in nums["restricted_countries"]),
              f"- Maximum tokens per investor identity: {nums['cap']}",
              "", "Definitions:"]
    lines += [f"- {d}" for d in pol["definitions"]]
    return "\n".join(lines)


def build_code(tid, smap, rules, code_set=None):
    swap = SWAPS.get(tid)
    parts, problems, swapped = [], [], False
    units = union_units(smap, rules)
    if code_set:   # extra functions for a later batch, see review_extra_units.json
        for spec in load_json(EXTRA_UNITS_FILE)[code_set]:
            d = units.setdefault((spec["file"], spec["contract"]), {"functions": [], "state": True})
            d["functions"] += [f for f in spec["functions"] if f not in d["functions"]]
    for (file, contract), m in units.items():
        f, c = file, contract
        if swap and contract == swap[0]:
            f, c, swapped = swap[1], swap[2], True
        text, missing, _ = slicer.slice_contract(ROOT, f, c, m["functions"], m["state"])
        problems += [f"{f} :: {c} :: {x}" for x in missing]
        if f != file:   # show the stock file and contract name in the marker line
            text = f"// ===== {file} :: {contract} =====\n" + text.split("\n", 1)[1]
        parts.append(text)
    if swap and not swapped:
        problems.append(f"{tid}: stock contract {swap[0]} is not used by the 10 rules, nothing to swap")
    return sanitize("\n\n".join(parts)), problems


def build_setup(tid):
    problems = []
    _, parsed, err = slicer.contract_items(ROOT, "test/ComplyFixture.sol", "ComplyFixture")
    if err:
        raise RuntimeError(err)
    base = ["contract BaseSetup {"]
    shown = set()
    for it in parsed[1]:
        if it["kind"] == "state" or (it["kind"] == "function" and it["name"] in BASE_SHOW):
            base.append(slicer.tidy(it["text"]))
            if it["kind"] == "function":
                shown.add(it["name"])
    base.append("}")
    problems += [f"base setup function not found: {n}" for n in BASE_SHOW if n not in shown]

    e = entry(tid)
    drop = SWAPS[tid][3] if tid in SWAPS else None
    over = []
    if e.get("cfg_contract"):
        _, cparsed, cerr = slicer.contract_items(ROOT, e["cfg_file"], e["cfg_contract"])
        if cerr:
            raise RuntimeError(cerr)
        for it in cparsed[1]:
            if it["kind"] == "function" and it["name"] == drop:
                continue
            if it["kind"] in ("function", "state"):
                over.append(slicer.tidy(it["text"]))
    out = ["// ===== base setup =====", "\n".join(base),
           "// ===== not shown: _makeActors creates the plain addresses; _rsvFor signs claim data with a given key =====",
           "// ===== overrides for this deployment =====",
           ("contract Deployment is BaseSetup {\n" + "\n".join(over) + "\n}") if over
           else "(none: this deployment uses the base setup unchanged)"]
    return sanitize("\n".join(out)), problems


# ------------------------------------------------------------------ checks
def leak_hits(text):
    hits = []
    for pat, why in LEAKS:
        for m in re.finditer(pat, text):
            s = max(0, m.start() - 30)
            hits.append(f"{why}: ...{text[s:m.end() + 30]!r}")
    return hits


def comment_hits(text):
    body = re.sub(r"^// =====.*$", "", text, flags=re.M)
    return re.findall(r"//|/\*", body)


def build_target(tid, code_set=None):
    """Everything the runner needs for one target. code_set: None (batch r1) or a key of review_extra_units.json."""
    smap = slicer.load_map(ROOT)
    pol = load_json(POLICY_FILE)
    policy = build_policy(tid)
    code, p1 = build_code(tid, smap, pol["rules"], code_set)
    setup, p2 = build_setup(tid)
    system, user = llm.render("reviewer", POLICY=policy, CODE=code, SETUP=setup)
    full = system + "\n" + user
    return {
        "id": tid, "kind": entry(tid)["kind"], "code_set": code_set, "system": system, "user": user,
        "problems": p1 + p2,
        "leaks": leak_hits(full),
        "comments": comment_hits(code) + comment_hits(setup),
        "chars": {"policy": len(policy), "code": len(code), "setup": len(setup), "all": len(full)},
        "est_tokens": llm.estimate_tokens(full),
    }


# ------------------------------------------------------------------ commands
def check(code_set=None):
    problems = 0
    smap = slicer.load_map(ROOT)
    pol = load_json(POLICY_FILE)
    for r in pol["rules"]:
        if r not in smap["rules"] or r not in prompts.RULE_TEXT:
            print(f"  rule {r} missing in slice_map.json or prompts.RULE_TEXT")
            problems += 1
    code_variants = {c["id"] for c in manifest() if c.get("type") == "C"}
    if code_variants != set(SWAPS):
        print(f"  SWAPS {sorted(SWAPS)} does not match code-copy variants in configs.json {sorted(code_variants)}")
        problems += 1
    for tid in all_target_ids():
        t = build_target(tid, code_set)
        bad = t["problems"] + t["leaks"] + (["comment markers found"] if t["comments"] else [])
        print(f"  {tid} ({t['kind']}): ~{t['est_tokens']} tokens" + ("  OK" if not bad else "  PROBLEM"))
        for b in bad:
            print(f"      {b}")
        problems += len(bad)
    n = len(all_target_ids())
    print("REVIEW INPUTS OK: %d targets, no leaks, no comments" % n if not problems
          else f"REVIEW INPUTS CHECK FAILED: {problems} problem(s)")
    return 1 if problems else 0


def sizes(code_set=None):
    cfg = llm.load_config()
    rows = []
    tot = {}
    print(f"{'target':<7}{'policy':>8}{'code':>8}{'setup':>8}{'~tokens':>9}{'~real in':>10}   (characters; real = estimate x {REAL_FACTOR})")
    for tid in all_target_ids():
        t = build_target(tid, code_set)
        real_in = int(t["est_tokens"] * REAL_FACTOR)
        c = t["chars"]
        print(f"{tid:<7}{c['policy']:>8}{c['code']:>8}{c['setup']:>8}{t['est_tokens']:>9}{real_in:>10}")
        rows.append(real_in)
    n = len(rows)
    print(f"\n{n} targets, total ~{sum(rows)} real input tokens (guess), output assumed {OUT_ASSUMED} per call")
    for alias in ("haiku", "sonnet"):
        model = llm.resolve_model(alias, cfg)
        usage = {"input_tokens": sum(rows), "output_tokens": OUT_ASSUMED * n}
        print(f"  {alias:<7} one full run of {n} calls: about ${llm.cost_usd(model, usage, cfg):.3f}")
    print("This is a guess. The first live call prints the real token counts.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--sizes", action="store_true")
    ap.add_argument("--show", metavar="TARGET")
    ap.add_argument("--code-set", default=None, help="extra code view, e.g. r2 (see review_extra_units.json)")
    a = ap.parse_args()
    if a.check:
        return check(a.code_set)
    if a.sizes:
        return sizes(a.code_set)
    if a.show:
        t = build_target(a.show, a.code_set)
        print("===== SYSTEM =====\n" + t["system"] + "\n===== USER =====\n" + t["user"])
        for k in ("problems", "leaks", "comments"):
            if t[k]:
                print(f"\n!! {k}: {t[k]}", file=sys.stderr)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())