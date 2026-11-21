#!/usr/bin/env python3
"""ComplyRWA step 4.8: offline checks for the review scorer and the frozen data. No network, no cost.

  python pipeline/test_review.py
"""
import json
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPE))
import review_score as rs  # noqa: E402

KW = rs.load_json(rs.KEYWORDS_FILE)
ENTRIES = rs.load_json(rs.MANIFEST_FILE)["configs"]
RULES = rs.load_json(rs.POLICY_FILE)["rules"]
PREFIX_TO_RULE = {"G01": "K1", "G02": "K3", "G03": "J1", "G04": "H1", "G05": "H3",
                  "G06": "K2", "G07": "J2", "G08": "J3", "G09": "H2", "G10": "H4"}

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def fnd(rule, sev="HIGH", where="", why=""):
    return {"rule": rule, "severity": sev, "where": where, "why": why, "steps": ""}


def answer(*findings):
    return json.dumps({"findings": list(findings)})


# ------------------------------------------------------------------ parser
@check
def parser_valid():
    st, f, n = rs.parse_answer(answer(fnd("k1", "high", "A.b", "x")))
    assert st == "ok" and f[0]["rule"] == "K1" and f[0]["severity"] == "HIGH", (st, f)


@check
def parser_empty_list_is_ok():
    st, f, _ = rs.parse_answer('{"findings":[]}')
    assert st == "ok" and f == []


@check
def parser_fenced_and_surrounded():
    txt = "Here you go:\n```json\n" + answer(fnd("H1")) + "\n```\nHope it helps."
    st, f, _ = rs.parse_answer(txt)
    assert st == "ok" and len(f) == 1
    st, f, _ = rs.parse_answer("Sure. " + answer(fnd("H1")) + " Done.")
    assert st == "ok" and len(f) == 1


@check
def parser_bad_answers_are_not_clean():
    for txt, trunc in [("", False), ("   ", False), ("no json here", False), ('{"findings": [', False),
                       ('{"other": 1}', False), ('{"findings": {"a": 1}}', False), ('{"findings":[1]}', False),
                       (answer(fnd("K1")), True)]:
        st, f, n = rs.parse_answer(txt, trunc)
        assert st == "no_valid_answer" and f == [] and n, (txt, st)


@check
def parser_severity_aliases_and_unknown():
    st, f, n = rs.parse_answer(answer(fnd("K1", "critical"), fnd("K2", "weird"), {"rule": "K3"}))
    assert [x["severity"] for x in f] == ["HIGH", "LOW", "LOW"], f
    assert len(n) == 2, n


@check
def mock_answer_parses():
    txt = (PIPE / "mock" / "reviewer.txt").read_text(encoding="utf-8")
    st, f, _ = rs.parse_answer(txt)
    assert st == "ok" and f, "mock/reviewer.txt must hold a valid answer with one finding"


# ------------------------------------------------------------------ scoring
def fake_answers():
    a = {}
    for e in ENTRIES:
        a[e["id"]] = {"text": answer(), "truncated": False}
    spec = KW["variants"]
    # V01: right rule and a strict word -> official and strict
    a["V01"]["text"] = answer(fnd(spec["V01"]["linked_rules"][0], "HIGH", "IdentityRegistry.isVerified", "returns on one topic"))
    # V02: right rule, no strict word -> official only
    a["V02"]["text"] = answer(fnd(spec["V02"]["linked_rules"][0], "MEDIUM", "somewhere", "something is off"))
    # V03: right rule but only LOW -> not detected
    a["V03"]["text"] = answer(fnd(spec["V03"]["linked_rules"][0], "LOW", "ClaimIssuer.isClaimValid", "revoke"))
    # V04: wrong rule (H4) -> not official, but flagged
    a["V04"]["text"] = answer(fnd("H4", "HIGH", "removeClaimTopic", "empty"))
    # V05: invalid answer -> no valid answer
    a["V05"] = {"text": "oops", "truncated": False}
    # V06: cut off -> no valid answer
    a["V06"] = {"text": answer(fnd("J2")), "truncated": True}
    # V07: missing answer
    del a["V07"]
    # C01: HIGH finding -> false positive; C02: LOW only -> not; C03: MEDIUM on a rule outside the list -> FP, out of scope
    a["C01"]["text"] = answer(fnd("H1", "HIGH", "Token.transfer", "x"))
    a["C02"]["text"] = answer(fnd("K1", "LOW", "x", "x"))
    a["C03"]["text"] = answer(fnd("K5", "MEDIUM", "Token.transfer", "sender not checked"))
    a["C04"] = {"text": "", "truncated": False}
    return a


@check
def scoring_on_fake_answers():
    rows, notes, found = rs.score_all(fake_answers(), KW, ENTRIES, RULES)
    r = {x["target"]: x for x in rows}
    assert r["V01"]["official"] and r["V01"]["strict"]
    assert r["V02"]["official"] and not r["V02"]["strict"]
    assert not r["V03"]["official"] and not r["V03"]["flagged_any"]
    assert not r["V04"]["official"] and r["V04"]["flagged_any"]
    assert r["V05"]["status"] == "no_valid_answer" and not r["V05"]["official"]
    assert r["V06"]["status"] == "no_valid_answer"
    assert r["V07"]["status"] == "no_valid_answer" and notes["V07"]
    assert r["C01"]["false_positive"] and not r["C02"]["false_positive"]
    assert r["C03"]["false_positive"] and r["C03"]["out_of_scope"] == 1
    assert r["C04"]["status"] == "no_valid_answer" and not r["C04"]["false_positive"]
    s = rs.summarize(rows)
    assert s["official"] == 2 and s["strict"] == 1 and s["flagged_any"] == 3, s
    assert s["false_positives"] == 2 and s["out_of_scope_findings"] == 1, s
    assert set(s["no_valid_answer"]) == {"V05", "V06", "V07", "C04"}, s["no_valid_answer"]
    assert s["variants"] == 13 and s["clean"] == 8, s


@check
def report_files_are_written():
    import tempfile
    rows, notes, found = rs.score_all(fake_answers(), KW, ENTRIES, RULES)
    s = rs.summarize(rows)
    with tempfile.TemporaryDirectory() as d:
        rs.write_report(d, "fake", rows, notes, s, {"V01": {"input_tokens": 1, "output_tokens": 2, "cost_usd": 0.1, "seconds": 3, "truncated": False}})
        rs.write_csv(d, rows, {})
        text = Path(d, "report.md").read_text(encoding="utf-8")
        assert "official" in text and "no valid answer" in text and "C03" in text
        assert len(Path(d, "scores.csv").read_text(encoding="utf-8").splitlines()) == len(rows) + 1


# ------------------------------------------------------------------ frozen data
@check
def keywords_are_complete_and_clean():
    v = KW["variants"]
    ids = {e["id"] for e in ENTRIES if e["kind"] == "variant"}
    assert set(v) == ids and len(ids) == 13, (sorted(v), sorted(ids))
    for tid, spec in v.items():
        assert spec["linked_rules"] and set(spec["linked_rules"]) <= set(RULES), (tid, spec["linked_rules"])
        assert spec["strict_any_of"], tid
        assert all(w == w.lower() and w.strip() == w and w for w in spec["strict_any_of"]), (tid, spec["strict_any_of"])


@check
def linked_rules_match_linked_tests():
    """linked_rules in review_keywords.json must equal the rules of linked_tests in configs.json."""
    for e in ENTRIES:
        if e["kind"] != "variant":
            continue
        want = {PREFIX_TO_RULE[t[:3]] for t in e["linked_tests"]}
        have = set(KW["variants"][e["id"]]["linked_rules"])
        assert want == have, f"{e['id']}: configs.json gives {sorted(want)}, keywords file has {sorted(have)}"


@check
def policy_rules_have_text_and_slices():
    import prompts
    import slicer
    smap = slicer.load_map(rs.ROOT)
    for r in RULES:
        assert r in prompts.RULE_TEXT and r in smap["rules"], r
    assert len(RULES) == 10


def main():
    failed = 0
    for fn in CHECKS:
        try:
            fn()
            print(f"  ok    {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(CHECKS) - failed} of {len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())