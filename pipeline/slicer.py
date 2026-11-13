"""ComplyRWA code slicer (Phase 4, step 4.3).

Cuts the pinned T-REX / ONCHAINID contracts down to the functions each rule needs, removes
all comments (Phase 1 found copy-pasted NatSpec that misleads an LLM), and writes one
compact text file per rule. No LLM is used.

The curated map lives in pipeline/slice_map.json:
  units  = named groups of functions in one contract   (file, contract, functions)
  rules  = K1..K5, J1..J4, H1..H4, each a list of units (in transfer-path order)
The slicer then adds, from the SAME contract and automatically:
  - helper functions and modifiers that an included function calls or uses
  - `error` declarations that an included function mentions
  - the contract's state variable declarations (mappings, constants, ...)
State that a contract inherits from another file (for example TokenStorage) is not included.

Usage (from the ComplyRWA folder, in Git Bash):
  python pipeline/slicer.py --check            every name in the map exists in the pinned source
  python pipeline/slicer.py --rule K1          print the slice for one rule
  python pipeline/slicer.py --all              write pipeline/slices/*.txt, index.json, sizes.md
Options: --root PATH (project root, default: parent of pipeline/), --out DIR

Outputs of --all (in pipeline/slices/):
  <RULE>.txt            the slice for each rule
  _fixture_api.txt      test/ComplyFixture.sol without function bodies (members, helpers, hooks)
  index.json            sizes per rule: characters and approximate tokens (characters / 4)
  sizes.md              the same as a table, with the saving against the full source files
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent


# ------------------------------------------------------------------ text helpers
def _skip_string(t, i):
    """t[i] is a quote. Return the index of the closing quote."""
    q, n = t[i], len(t)
    i += 1
    while i < n and t[i] != q:
        if t[i] == "\\":
            i += 1
        i += 1
    return i


def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c, two = src[i], src[i:i + 2]
        if c in "\"'":
            j = _skip_string(src, i)
            out.append(src[i:j + 1])
            i = j + 1
        elif two == "//":
            j = src.find("\n", i)
            i = n if j == -1 else j
        elif two == "/*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_brace(t, i):
    """t[i] is '{'. Return the index of its matching '}'."""
    depth, n = 0, len(t)
    while i < n:
        c = t[i]
        if c in "\"'":
            i = _skip_string(t, i)
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced braces")


def find_contract(text, name):
    m = re.search(r"\b(?:abstract\s+)?contract\s+" + re.escape(name) + r"\b[^{]*\{", text)
    if not m:
        return None
    end = match_brace(text, m.end() - 1)
    header = " ".join(text[m.start():m.end() - 1].split())
    return header, text[m.end():end]


KW = re.compile(r"(function|modifier|constructor|error|event|struct|enum|using|receive|fallback)\b(?:\s+(\w+))?")


def parse_members(body):
    """Split a contract body into top-level members: functions, modifiers, errors, state, ..."""
    items, i, start, n = [], 0, 0, len(body)

    def make(text):
        t = text.strip()
        m = KW.match(t)
        kind = m.group(1) if m else "state"
        name = m.group(2) if m and kind in ("function", "modifier", "error", "event", "struct", "enum") else None
        if kind == "constructor":
            name = "constructor"
        return {"kind": kind, "name": name, "text": t}

    while i < n:
        c = body[i]
        if c in "\"'":
            i = _skip_string(body, i)
        elif c == ";":
            items.append(make(body[start:i + 1]))
            start = i + 1
        elif c == "{":
            j = match_brace(body, i)
            items.append(make(body[start:j + 1]))
            start, i = j + 1, j
        i += 1
    return items


def tidy(text):
    lines = [l.rstrip() for l in text.split("\n") if l.strip()]
    return "    " + lines[0] + ("\n" + "\n".join(lines[1:]) if len(lines) > 1 else "")


# ------------------------------------------------------------------ slicing
def load_map(root):
    return json.loads((HERE / "slice_map.json").read_text(encoding="utf-8"))


def contract_items(root, file, contract):
    p = root / file
    if not p.exists():
        return None, None, f"file not found: {file}"
    raw = p.read_text(encoding="utf-8")
    found = find_contract(strip_comments(raw), contract)
    if not found:
        return raw, None, f"contract {contract} not found in {file}"
    header, body = found
    return raw, (header, parse_members(body)), None


def slice_contract(root, file, contract, funcs, with_state=True):
    """Return (text, missing_names, raw_source_size)."""
    raw, parsed, err = contract_items(root, file, contract)
    if err:
        return "", [err], len(raw or "")
    header, items = parsed
    defs = {}
    for idx, it in enumerate(items):
        if it["kind"] in ("function", "modifier") and it["name"]:
            defs.setdefault(it["name"], []).append(idx)
    missing = [f for f in funcs if f not in defs]
    chosen, todo = set(), [f for f in funcs if f in defs]

    def pull(name):
        for idx in defs.get(name, []):
            if idx not in chosen:
                chosen.add(idx)
                t = items[idx]["text"]
                todo.extend(re.findall(r"(?<![\.\w])(\w+)\s*\(", t))
                todo.extend(w for w in re.findall(r"\w+", t.split("{", 1)[0]) if w in defs)

    while todo:
        pull(todo.pop())
    code = " ".join(items[i]["text"] for i in chosen)
    for idx, it in enumerate(items):
        if it["kind"] == "error" and re.search(r"\b" + re.escape(it["name"]) + r"\b", code):
            chosen.add(idx)
        if with_state and it["kind"] == "state":
            chosen.add(idx)
    lines = [f"// ===== {file} :: {contract} =====", header + " {"]
    lines += [tidy(items[i]["text"]) for i in sorted(chosen)]
    lines.append("}")
    return "\n".join(lines), missing, len(raw)


def rule_units(smap, rule):
    """Merge the units of a rule by (file, contract), keeping first-seen order."""
    merged = {}
    for u in smap["rules"][rule]["units"]:
        spec = smap["units"][u]
        key = (spec["file"], spec["contract"])
        m = merged.setdefault(key, {"functions": [], "state": True})
        for f in spec["functions"]:
            if f not in m["functions"]:
                m["functions"].append(f)
        m["state"] = m["state"] and spec.get("state", True)
    return merged


def build_rule(root, smap, rule):
    parts, missing, raw_sizes = [], [], {}
    for (file, contract), m in rule_units(smap, rule).items():
        text, miss, size = slice_contract(root, file, contract, m["functions"], m["state"])
        parts.append(text)
        missing += [f"{file} :: {contract} :: {x}" for x in miss]
        raw_sizes[file] = size
    head = (f"// Rule {rule}: {smap['rules'][rule]['title']}\n"
            f"// Source: pinned T-REX 4.1.6 (a09cfd3) and ONCHAINID 2.1.0. Comments removed. "
            f"Only the parts this rule needs.\n")
    body = "\n\n".join(parts)
    return head + "\n" + body + "\n", body, missing, raw_sizes


def fixture_api(text):
    """Fixture members, helper signatures and doc comments, without function bodies."""
    def code_only(line):
        line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
        return re.sub(r"//.*", "", line)

    out, depth = [], 0
    for line in text.split("\n"):
        d0, code = depth, code_only(line)
        depth += code.count("{") - code.count("}")
        s = line.strip()
        if d0 == 0:
            if re.match(r"(abstract\s+)?contract\b", s):
                out.append(re.sub(r"\s*\{.*$", " {", s))
        elif d0 == 1:
            if "{" in code:
                cut = line.index("{")
                prefix = line[:cut].rstrip()
                if prefix.strip():
                    out.append(prefix + ";")
                elif out:
                    out[-1] += ";"
            else:
                out.append(line.rstrip())
    res, blank = [], False
    for l in out:
        if not l.strip():
            if not blank:
                res.append("")
            blank = True
        else:
            res.append(l)
            blank = False
    return "\n".join(res).strip() + "\n"


# ------------------------------------------------------------------ commands
def check(root, smap):
    problems = 0
    for key, spec in smap["units"].items():
        raw, parsed, err = contract_items(root, spec["file"], spec["contract"])
        if err:
            print(f"  [{key}] {err}")
            problems += 1
            continue
        names = {i["name"] for i in parsed[1] if i["kind"] in ("function", "modifier") and i["name"]}
        for f in spec["functions"]:
            if f not in names:
                print(f"  [{key}] {spec['contract']}.{f} NOT FOUND. Available: {', '.join(sorted(names))}")
                problems += 1
    for r, spec in smap["rules"].items():
        for u in spec["units"]:
            if u not in smap["units"]:
                print(f"  rule {r}: unknown unit {u}")
                problems += 1
    for r in smap.get("default_audit", []):
        if r not in smap["rules"]:
            print(f"  default_audit: unknown rule {r}")
            problems += 1
    print("SLICE MAP OK: %d units, %d rules" % (len(smap["units"]), len(smap["rules"])) if not problems
          else f"SLICE MAP CHECK FAILED: {problems} problem(s)")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rule")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    smap = load_map(root)

    if a.check:
        return 1 if check(root, smap) else 0
    if a.rule:
        text, _, missing, _ = build_rule(root, smap, a.rule)
        if missing:
            print("MISSING:", missing, file=sys.stderr)
            return 1
        print(text)
        return 0
    if not a.all:
        ap.print_help()
        return 0

    if check(root, smap):
        return 1
    out = Path(a.out).resolve() if a.out else HERE / "slices"
    out.mkdir(parents=True, exist_ok=True)
    index, comment_hits = {}, []
    for rule in smap["rules"]:
        text, body, _, raw_sizes = build_rule(root, smap, rule)
        (out / f"{rule}.txt").write_text(text, encoding="utf-8")
        if re.search(r"//|/\*", re.sub(r"^// =====.*$", "", body, flags=re.M)):
            comment_hits.append(rule)
        full = sum(raw_sizes.values())
        index[rule] = {"title": smap["rules"][rule]["title"], "files": len(raw_sizes),
                       "slice_chars": len(text), "slice_tokens": round(len(text) / 4),
                       "full_chars": full, "full_tokens": round(full / 4)}
    fx = root / "test" / "ComplyFixture.sol"
    if fx.exists():
        api = fixture_api(fx.read_text(encoding="utf-8"))
        (out / "_fixture_api.txt").write_text(api, encoding="utf-8")
        index["_fixture_api"] = {"slice_chars": len(api), "slice_tokens": round(len(api) / 4)}
    (out / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    with open(out / "sizes.md", "w", encoding="utf-8") as f:
        f.write("| rule | files | slice chars | slice ~tokens | full files chars | full ~tokens | slice is |\n|---|---|---|---|---|---|---|\n")
        for r, v in index.items():
            if r.startswith("_"):
                continue
            f.write(f"| {r} | {v['files']} | {v['slice_chars']} | {v['slice_tokens']} | {v['full_chars']} | "
                    f"{v['full_tokens']} | {100 * v['slice_chars'] / v['full_chars']:.0f}% |\n")
    rules = [v for k, v in index.items() if not k.startswith("_")]
    print(f"Wrote {len(rules)} rule slices to {out}")
    print(f"Comment check: {'OK, no comments in any slice' if not comment_hits else 'COMMENT MARKERS FOUND in ' + ', '.join(comment_hits)}")
    print(f"Average slice: {sum(v['slice_tokens'] for v in rules) // len(rules)} ~tokens "
          f"(full source files: {sum(v['full_tokens'] for v in rules) // len(rules)} ~tokens)")
    if "_fixture_api" in index:
        print(f"Fixture API: {index['_fixture_api']['slice_tokens']} ~tokens")
    return 1 if comment_hits else 0


if __name__ == "__main__":
    sys.exit(main())
