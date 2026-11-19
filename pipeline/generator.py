#!/usr/bin/env python3
"""ComplyRWA step 4.5: policy rule -> candidate Foundry tests -> validity filter.

For each rule: one model call (the prompt asks for N tests), the answer is saved under
candidates/<batch>/, then ALL candidates of the batch go through pipeline/validity_filter.py
(step 4.2), which decides KEEP / VACUOUS / REJECT by running them.

  python pipeline/generator.py --mode mock --rules K1                  free: uses mock/generator.txt
  python pipeline/generator.py --mode live --model haiku --rules K1    first real run (a few cents at most)
  python pipeline/generator.py --mode live --rules default             the 5 demo rules
  python pipeline/generator.py --mode replay --rules default           re-run from saved answers, free
Add --no-filter to only write the candidate files.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
import llm  # noqa: E402
import prompts  # noqa: E402

# Problems that would break the executor wrappers or the fixture, so the file is NOT sent to the filter.
HARD = ("defines setUp", "has invariant_", "defines a fixture function", "test function with arguments",
        "uses vm.ffi", "no 'contract X", "no test function", "wrong or missing")


def main():
    cfg = llm.load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", nargs="+", default=["K1"],
                    help="rule ids, or 'default' (K1 K3 J1 H1 H3), or 'all' (the 12 audit rules)")
    ap.add_argument("--batch", default="b1", help="batch name; files go to candidates/<batch>/")
    ap.add_argument("--n", type=int, default=4, help="tests asked per rule")
    ap.add_argument("--model", default=cfg.get("default_model", "haiku"))
    ap.add_argument("--mode", default=cfg.get("default_mode", "mock"), choices=["mock", "replay", "live"])
    ap.add_argument("--max-tokens", type=int, default=12000)
    ap.add_argument("--cap", type=float, default=None)
    ap.add_argument("--no-filter", action="store_true")
    a = ap.parse_args()

    rules = a.rules
    if rules == ["default"]:
        rules = prompts.DEFAULT_AUDIT
    elif rules == ["all"]:
        rules = sorted(prompts.RULE_TEXT)

    client = llm.LLMClient(a.mode, a.cap)
    fixture_names = prompts.fixture_function_names()
    outdir = ROOT / "candidates" / a.batch
    (outdir / "raw").mkdir(parents=True, exist_ok=True)
    (outdir / "rejected").mkdir(exist_ok=True)

    sent, skipped = [], []
    t_in = t_out = 0
    paid = original = 0.0
    print(f"batch {a.batch}: mode {a.mode}, model {llm.resolve_model(a.model, cfg)}, rules {' '.join(rules)}\n")
    for rule in rules:
        system, user, name = prompts.generator_prompt(rule, a.n, a.batch)
        r = client.complete(system, user, model=a.model, max_tokens=a.max_tokens, tag=f"generator:{rule}:{a.batch}")
        t_in += r.input_tokens
        t_out += r.output_tokens
        paid += r.cost_usd
        original += r.original_cost_usd
        (outdir / "raw" / f"{name}.txt").write_text(r.text, encoding="utf-8")
        code, probs = prompts.extract_solidity(r.text, name, fixture_names)
        if r.truncated:
            probs.append("answer was cut by max_tokens")
        n_tests = code.count("function test") if code else 0
        print(f"{rule}: {r.input_tokens} in / {r.output_tokens} out tokens, ${r.original_cost_usd:.4f}"
              f"{' (cached)' if r.cached else ''}, {n_tests} test function(s)")
        for p in probs:
            print(f"    problem: {p}")
        if code is None:
            skipped.append((rule, "no code block"))
            continue
        bad = [p for p in probs if p.startswith(HARD)] + (["answer was cut by max_tokens"] if r.truncated else [])
        if bad:
            (outdir / "rejected" / f"{name}.sol").write_text(code, encoding="utf-8")
            skipped.append((rule, "; ".join(bad)))
            continue
        path = outdir / f"{name}.sol"
        path.write_text(code, encoding="utf-8")
        sent.append(f"{path.relative_to(ROOT).as_posix()}:{name}")

    print(f"\nasked {len(rules)} rule(s); {len(sent)} file(s) ready for the filter, {len(skipped)} skipped before running")
    for rule, why in skipped:
        print(f"  skipped {rule}: {why}")
    print(f"tokens: {t_in} in / {t_out} out; paid now ${paid:.4f}; cost of these answers when first made ${original:.4f}")
    print(client.summary())

    if sent and not a.no_filter:
        out = f"results/filter_{a.batch}"
        cmd = [sys.executable, str(PIPE / "validity_filter.py"), "--tests", *sent, "--out", out]
        print(f"\nrunning the validity filter (takes minutes): output in {out}/report.md")
        return subprocess.run(cmd, cwd=ROOT).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())