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


# ------------------------------------------------------------------ stock-gap (S03) handling
GAP_WHY = ("Revocation is keyed on the exact signature bytes, but ecrecover accepts high-s signatures. The revoked "
           "signature (r, s, v) can be rewritten as (r, n-s, v^1), which recovers to the same signer but is not in revokedClaims.")


def empty_answers():
    return {e["id"]: {"text": answer(), "truncated": False} for e in ENTRIES}


@check
def stock_gap_on_clean_target_is_not_adjusted_false_positive():
    a = empty_answers()
    a["C01"]["text"] = answer(fnd("K2", "HIGH", "ClaimIssuer.getRecoveredAddress / isClaimValid", GAP_WHY))
    a["C02"]["text"] = answer(fnd("K2", "HIGH", "ClaimIssuer.isClaimValid", "revoked claims are accepted"))
    rows, _, _ = rs.score_all(a, KW, ENTRIES, RULES)
    r = {x["target"]: x for x in rows}
    assert r["C01"]["false_positive"] and not r["C01"]["false_positive_adj"] and r["C01"]["stock_gap_findings"] == 1
    assert r["C02"]["false_positive"] and r["C02"]["false_positive_adj"] and r["C02"]["stock_gap_findings"] == 0
    s = rs.summarize(rows)
    assert s["false_positives"] == 2 and s["false_positives_adj"] == 1 and s["stock_gap_targets"] == ["C01"], s


@check
def stock_gap_does_not_credit_v03():
    a = empty_answers()
    a["V03"]["text"] = answer(fnd("K2", "HIGH", "ClaimIssuer.isClaimValid / revokeClaim", GAP_WHY))
    rows, _, _ = rs.score_all(a, KW, ENTRIES, RULES)
    r = {x["target"]: x for x in rows}["V03"]
    assert r["official"] and r["strict"], "as defined in the frozen file, the finding would count"
    assert not r["official_adj"] and not r["strict_adj"], "adjusted scores must not credit the twin-signature finding"
    a["V03"]["text"] = answer(fnd("K2", "HIGH", "ClaimIssuer.isClaimValid", "isClaimValid never checks isClaimRevoked, so a revoked claim is accepted"))
    rows, _, _ = rs.score_all(a, KW, ENTRIES, RULES)
    r = {x["target"]: x for x in rows}["V03"]
    assert r["official_adj"] and r["strict_adj"] and r["stock_gap_findings"] == 0


@check
def stock_gap_only_applies_to_k2():
    assert rs.is_stock_gap(fnd("K2", "HIGH", "x", GAP_WHY))
    assert not rs.is_stock_gap(fnd("K1", "HIGH", "x", GAP_WHY))
    assert not rs.is_stock_gap(fnd("K2", "HIGH", "isClaimValid", "revocation ignored"))


# ------------------------------------------------------------------ invalid JSON and retry (V08 of the Sonnet r1 run)
V08_BROKEN = ('{"findings":[{"rule":"J3","where":"Deployment._configureModules","severity":"HIGH","why":"y","steps":"z"}},'
              '{"rule":"J1","where":"x","severity":"HIGH","why":"y","steps":"z"}}]}')


@check
def stray_brace_is_not_valid_json():
    """The real V08 answer had an extra closing brace after each finding. It must count as no valid answer."""
    st, f, n = rs.parse_answer(V08_BROKEN)
    assert st == "no_valid_answer" and f == [] and "invalid JSON" in n[0], (st, n)


@check
def retry_answer_replaces_invalid_first_answer():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "raw").mkdir()
        good = answer(fnd("J3", "HIGH", "Deployment._configureModules", "no country is restricted"))
        (d / "raw" / "V08.retry1.txt").write_text(good, encoding="utf-8")
        (d / "raw" / "V01.retry1.txt").write_text(good, encoding="utf-8")   # V01's first answer is valid: must be ignored
        (d / "calls_retry.json").write_text(json.dumps({"V08": {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.5,
                                                                "seconds": 2.0, "truncated": False}}), encoding="utf-8")
        answers = empty_answers()
        answers["V08"] = {"text": V08_BROKEN, "truncated": False}
        calls = {"V08": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 1.0, "seconds": 3.0, "truncated": False}}
        new_answers, new_calls, retried = rs.apply_retries(d, ENTRIES, answers, calls)
        assert retried == ["V08"], retried
        assert new_calls["V08"]["input_tokens"] == 110 and abs(new_calls["V08"]["cost_usd"] - 1.5) < 1e-9
        rows, _, _ = rs.score_all(new_answers, KW, ENTRIES, RULES)
        r = {x["target"]: x for x in rows}
        assert r["V08"]["status"] == "ok" and r["V08"]["official"] and r["V08"]["strict"], r["V08"]
        assert r["V01"]["findings"] == 0, "a valid first answer must not be replaced"
        before, _, _ = rs.score_all(answers, KW, ENTRIES, RULES)
        assert {x["target"]: x for x in before}["V08"]["status"] == "no_valid_answer", "the first-run scoring must stay unchanged"


@check
def extra_units_file_is_well_formed():
    data = rs.load_json(PIPE / "review_extra_units.json")
    assert data["r2"], "r2 must list extra units"
    for spec in data["r2"]:
        assert spec["file"] and spec["contract"] and spec["functions"], spec


@check
def s04_v_byte_wording_is_a_stock_gap():
    """The real C02 finding of the Haiku r1 run (v byte changed from 27/28 to 0/1) is the S04 gap, confirmed by a Foundry test."""
    why = ("getRecoveredAddress accepts v in {0,1} as well as {27,28}. A revoked signature can be re-encoded with a "
           "different v byte, giving different bytes that recover to the same signer and are not in revokedClaims.")
    assert rs.is_stock_gap(fnd("K2", "HIGH", "ClaimIssuer.revokeClaim / isClaimValid / getRecoveredAddress", why))
    assert not rs.is_stock_gap(fnd("K2", "HIGH", "ClaimIssuer.isClaimValid", "isClaimValid never checks isClaimRevoked"))


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