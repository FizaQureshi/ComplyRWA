import re, sys, csv
from pathlib import Path

# Columns in display order. Scenario tests use the plain ID; property tests too,
# except G05b which exists twice (recovery scenario and fuzzed property).
COLS = ["G01a","G01b","G02a","G02b","G03a","G03b","G04","G05a",
        "G05b-prop","G05b-rec","G06a","G06b","G06c","G07","G08","G09","G10","G13"]

# Linked tests per variant (from the Phase 2 plan and the Wave 1 table).
LINKED = {
 "V01":["G01a","G01b"], "V02":["G01a","G01b"], "V03":["G06c"],
 "V04":["G02a","G02b","G01a","G01b"], "V05":["G03a","G03b","G08"],
 "V06":["G07"], "V07":["G07","G08"], "V08":["G08","G03a"],
 "V09":["G04","G05a","G05b-prop"], "V10":["G09","G04"],
 "V11":["G05a","G05b-prop","G04"], "V12":["G05b-prop"],
 "V13":["G04","G09","G10"],
}

SUITE = re.compile(r"([VC]\d\d)_(?:Scenarios|Invariants)")
def cfg_of(name):
    m = SUITE.fullmatch(name)
    if m: return m.group(1)
    if name in ("GoldScenariosTest", "GoldInvariantsTest"): return "C01"
    return None

R_SUITE_A = re.compile(r"(?:Ran \d+ tests? for|failing tests? in) \S+?:(\w+)")
R_SUITE_B = re.compile(r"^\s*(\w+) invariants[:\s]")
R_TEST    = re.compile(r"^\[(PASS|FAIL)\b.*?\]\s+test_(G\d\d[a-z]?)\w*\(")
R_INV     = re.compile(r"^\[(PASS|FAIL)\b.*?\]\s+invariant_(G\d\d[a-z]?)_\w+\s*$")

def parse(path, res):
    cur = None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = R_SUITE_A.search(line) or R_SUITE_B.match(line)
        if m:
            cur = cfg_of(m.group(1))
            continue
        m = R_TEST.match(line)
        kind = "test"
        if not m:
            m = R_INV.match(line)
            kind = "inv"
        if not m or cur is None:
            continue
        status, gid = m.group(1), m.group(2)
        if gid == "G05b":
            gid = "G05b-rec" if kind == "test" else "G05b-prop"
        if res.setdefault(cur, {}).get(gid) != "FAIL":   # FAIL always wins
            res[cur][gid] = status

def main(paths):
    res = {}
    for p in paths:
        parse(p, res)

    rows = []
    for cfg in sorted(res):
        cells = [res[cfg].get(c, "-") for c in COLS]
        failed = [c for c in COLS if res[cfg].get(c) == "FAIL"]
        if cfg.startswith("V"):
            linked = [c for c in LINKED.get(cfg, []) if res[cfg].get(c) == "FAIL"]
            verdict = "CAUGHT (linked)" if linked else ("CAUGHT (other only)" if failed else "NOT CAUGHT")
        else:
            verdict = "FALSE POSITIVE" if failed else "clean"
        rows.append([cfg] + cells + [verdict, " ".join(failed)])

    Path("results").mkdir(exist_ok=True)
    header = ["config"] + COLS + ["verdict", "failed_tests"]
    with open("results/variant_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    with open("results/variant_table.md", "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(header[:-1]) + " |\n")
        f.write("|" + "---|" * (len(header) - 1) + "\n")
        for r in rows:
            f.write("| " + " | ".join(r[:-1]) + " |\n")

    v = [r for r in rows if r[0].startswith("V")]
    c = [r for r in rows if r[0].startswith("C")]
    print(f"Seeded variants found: {len(v)}")
    print(f"  caught by a linked test: {sum(r[-2]=='CAUGHT (linked)' for r in v)}")
    print(f"  caught by any test:      {sum(r[-2].startswith('CAUGHT') for r in v)}")
    print(f"  not caught:              {sum(r[-2]=='NOT CAUGHT' for r in v)}")
    if v:
        print(f"  detection rate (linked): {100*sum(r[-2]=='CAUGHT (linked)' for r in v)/len(v):.0f}%")
    print(f"Clean configs found: {len(c)}")
    if c:
        fp = sum(r[-2] == "FALSE POSITIVE" for r in c)
        print(f"  with a failing gold test: {fp}  -> false-positive rate {100*fp/len(c):.0f}%")
    print("Wrote results/variant_table.csv and results/variant_table.md")

if __name__ == "__main__":
    main(sys.argv[1:])