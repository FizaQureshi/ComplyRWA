#!/usr/bin/env python3
"""Offline self-test for step 4.4. No network, no cost.   python pipeline/test_llm_interface.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm
import prompts

TEAM_MOCK = '''```solidity
pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_K1_mock is ComplyFixture {
    function test_K1_mock_a() public {
        assertEq(uint256(1), uint256(1));
    }
}
```'''


def fresh(mode="mock", cap=1.0):
    d = Path(tempfile.mkdtemp())
    (d / "mock").mkdir()
    (d / "mock" / "default.txt").write_text("MOCK ANSWER", encoding="utf-8")
    (d / "mock" / "generator.txt").write_text(TEAM_MOCK, encoding="utf-8")
    return llm.LLMClient(mode, cap, d / "cache", d / "ledger.jsonl", d / "mock"), d


def test_cost_math():
    assert abs(llm.cost_usd("claude-sonnet-5-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000}) - 12.0) < 1e-9
    assert abs(llm.cost_usd("claude-haiku-5-5", {"input_tokens": 50_000, "output_tokens": 10_000}) - 0.01) < 1e-9


def test_alias():
    assert llm.resolve_model("haiku") == "claude-haiku-5-5"
    assert llm.resolve_model("claude-sonnet-5-5") == "claude-sonnet-5-5"


def test_render():
    d = Path(tempfile.mkdtemp())
    (d / "t.md").write_text("sys {{A}}\n---USER---\nuser {{B}} {{A}}", encoding="utf-8")
    old = llm.PROMPT_DIR
    llm.PROMPT_DIR = d
    try:
        s, u = llm.render("t", A="x", B="{{A}}")      # inserted text must not be re-scanned
        assert s == "sys x" and u == "user {{A}} x", (s, u)
        try:
            llm.render("t", A="x")
            raise AssertionError("expected KeyError")
        except KeyError:
            pass
    finally:
        llm.PROMPT_DIR = old


def test_mock_picks_file_by_tag_and_is_free():
    c, _ = fresh("mock")
    r = c.complete("s", "u", model="haiku", tag="generator:K1:1")
    assert r.text == TEAM_MOCK and r.cost_usd == 0.0 and r.original_cost_usd > 0
    r2 = c.complete("s", "u", model="haiku", tag="other")
    assert r2.text == "MOCK ANSWER"
    assert c.spent() == 0.0 and len(c._read_ledger()) == 2


def test_replay_miss_and_hit():
    c, _ = fresh("replay")
    try:
        c.complete("s", "u", model="haiku", tag="x")
        raise AssertionError("expected ReplayMiss")
    except llm.ReplayMiss:
        pass
    key = c.make_key("claude-haiku-5-5", "s", "u", 4000, 0)
    c._cache_put(key, {"text": "hello", "usage": {"input_tokens": 10, "output_tokens": 5},
                       "stop_reason": "end_turn", "cost_usd": 0.001})
    r = c.complete("s", "u", model="haiku", tag="x")
    assert r.cached and r.text == "hello" and r.cost_usd == 0.0 and r.original_cost_usd == 0.001


def test_budget_blocks_live_call():
    c, _ = fresh("live", cap=0.0001)
    try:
        c.complete("s", "u" * 4000, model="sonnet", max_tokens=4000, tag="big")
        raise AssertionError("expected BudgetExceeded")
    except llm.BudgetExceeded:
        pass


def test_extract_solidity():
    code, probs = prompts.extract_solidity(TEAM_MOCK, "Cand_K1_b1")
    assert "contract Cand_K1_b1 is ComplyFixture" in code
    assert probs == ["contract renamed Cand_K1_mock -> Cand_K1_b1"], probs
    _, probs = prompts.extract_solidity("no code here")
    assert probs == ["no code block found"]
    bad = TEAM_MOCK.replace("test_K1_mock_a()", "testFuzz_a(uint256 x)")
    _, probs = prompts.extract_solidity(bad)
    assert any("arguments" in p for p in probs), probs


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"{len(tests)} passed")