#!/usr/bin/env python3
"""ComplyRWA step 4.4: helpers around the prompt templates (no network here).

The wording of the prompt lives in pipeline/prompts/generator.md (the team's version).
This file only: holds the plain-English rule texts, loads the code slice, fills the template
through llm.render(), and parses the model's answer.

The generator sees ONLY the rule text, the comment-free slice, the fixture API and the
fixture facts. Never variants/ or the gold tests (Phase 4 decision 8).

  python pipeline/prompts.py --rule K1 --n 4          size only
  python pipeline/prompts.py --rule K1 --n 4 --show   print the whole prompt
"""
import argparse
import re
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPE))
import llm  # noqa: E402

SLICES = PIPE / "slices"

# K1, K3, J1, H1, H3 = demo policy lines (Phase 2 section 6). Others = "plain-English rule" lines of the Phase 2 cards.
# J4 is not an audit rule (known-exception trap), so it has no policy line.
RULE_TEXT = {
    "K1": "Only investors with a valid KYC claim from a trusted issuer may receive tokens.",
    "K2": "If an investor's KYC is revoked, the wallet can no longer receive tokens.",
    "K3": "At least one KYC claim topic must be required.",
    "K4": "A KYC claim past its expiry date must not let a wallet receive tokens.",
    "K5": "A wallet whose KYC was revoked must not be able to send tokens.",
    "J1": "Investors registered in a restricted country may not receive tokens.",
    "J2": "If a wallet's country is updated to a restricted country, it can no longer receive tokens.",
    "J3": "A country restriction is only real if the country module is bound to the compliance contract and has the right countries set.",
    "H1": "No investor may hold more than the maximum allowed number of tokens.",
    "H2": "Two wallets under the same identity share one cap.",
    "H3": "The holding-limit module's balance records must match the real token balances.",
    "H4": "The holding cap must match the issuer's number. It must not be 0 or the maximum uint256.",
}
DEFAULT_AUDIT = ["K1", "K3", "J1", "H1", "H3"]


def load_slice(rule):
    f = SLICES / f"{rule}.txt"
    if not f.exists():
        raise FileNotFoundError(f"no slice file {f}")
    return f.read_text(encoding="utf-8")


def slice_title(text, rule):
    m = re.match(r"//\s*Rule\s+\w+:\s*(.+)", text)
    return m.group(1).strip() if m else rule


def generator_prompt(rule, n_tests=4, batch="b1", policy_text=None):
    """Return (system, user, contract_name) for one rule."""
    name = f"Cand_{rule}_{batch}"
    text = load_slice(rule)
    policy = policy_text or RULE_TEXT.get(rule)
    if policy is None:
        raise KeyError(f"rule {rule} has no policy text; pass policy_text=")
    system, user = llm.render(
        "generator", CONTRACT_NAME=name, RULE_ID=rule, RULE_TITLE=slice_title(text, rule),
        POLICY_TEXT=policy, N_TESTS=n_tests, SLICE=text,
        FIXTURE_API=(SLICES / "_fixture_api.txt").read_text(encoding="utf-8"),
        FIXTURE_FACTS=(PIPE / "fixture_facts.md").read_text(encoding="utf-8"))
    return system, user, name


_FENCE = re.compile(r"```(?:solidity|sol)?\s*\n(.*?)```", re.S)


def extract_solidity(text, expected_name=None):
    """Pull the Solidity file out of a model answer. Returns (code, problems).
    code is None when there is no code block. A problem list does not stop the pipeline:
    the validity filter (step 4.2) is the real judge; this only explains early failures."""
    problems = []
    blocks = _FENCE.findall(text)
    if not blocks:
        return None, ["no code block found"]
    if len(blocks) > 1:
        problems.append(f"{len(blocks)} code blocks found, used the first")
    code = blocks[0].strip() + "\n"
    m = re.search(r"\bcontract\s+(\w+)\s+is\s+ComplyFixture\b", code)
    if not m:
        problems.append("no 'contract X is ComplyFixture' found")
    elif expected_name and m.group(1) != expected_name:
        code = re.sub(rf"\b{re.escape(m.group(1))}\b", expected_name, code)
        problems.append(f"contract renamed {m.group(1)} -> {expected_name}")
    if "../../test/ComplyFixture.sol" not in code:
        problems.append("wrong or missing ComplyFixture import")
    if re.search(r"function\s+setUp\b", code):
        problems.append("defines setUp (not allowed)")
    if re.search(r"function\s+invariant_", code):
        problems.append("has invariant_ function (not allowed)")
    if re.search(r"function\s+_\w+", code):
        problems.append("defines an underscore function (may clash with fixture hooks)")
    if re.search(r"function\s+test\w*\(\s*[^)\s]", code):
        problems.append("test function with arguments (not allowed)")
    if "vm.ffi" in code:
        problems.append("uses vm.ffi (not allowed)")
    if not re.search(r"function\s+test\w*\(\s*\)", code):
        problems.append("no test function found")
    return code, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True, choices=sorted(RULE_TEXT))
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    system, user, name = generator_prompt(a.rule, a.n)
    print(f"rule {a.rule}, contract {name}")
    print(f"system ~{llm.estimate_tokens(system)} tokens, user ~{llm.estimate_tokens(user)} tokens (characters / 4)")
    if a.show:
        print("\n===== SYSTEM =====\n" + system + "\n===== USER =====\n" + user)
    return 0


if __name__ == "__main__":
    sys.exit(main())