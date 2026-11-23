#!/usr/bin/env python3
"""ComplyRWA step 4.8: run the LLM-only review. One model call per target, no tests are run.

For each target (C01..C08, V01..V13) the input comes from pipeline/review_inputs.py.
Answers are saved in results/review_<batch>_<model>/ :
  raw/<TARGET>.txt   the model's raw answer
  calls.json         per target: tokens, cost, seconds, cut-off flag, prompt hash
After all 21 targets are done, pipeline/review_score.py is run on the folder.

Safety:
  * Before any call, every selected input is checked again (no leaks, no comments, no missing code).
  * A per-run money limit: the client's cap is (money spent so far) + --budget. The run stops when it would pass it.
  * Every call is in results/llm_ledger.jsonl with the tag reviewer:<TARGET>:<batch>.
  * Answers are cached by llm.py, so a repeated live run costs nothing and gives the same answers.
    To retry a cut-off answer, give a larger --max-tokens (that is a new prompt key).
  * A mock run writes to results/review_mock_<batch>_<model>/ so it is never mistaken for a real result.

  python pipeline/review_baseline.py --dry-run --model haiku                    free: sizes and cost guess
  python pipeline/review_baseline.py --mode mock --model haiku                  free: fake answers
  python pipeline/review_baseline.py --mode live --model haiku --targets C01    pilot: one real call
  python pipeline/review_baseline.py --mode live --model haiku                  all 21 targets
  python pipeline/review_baseline.py --mode replay --model haiku                from saved answers, free
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
import llm  # noqa: E402
import review_inputs as ri  # noqa: E402
import review_score as rs  # noqa: E402

# Output limit and money limit for one run. Haiku once returned an empty answer at 6,000 output tokens, so it gets more room.
# Haiku wrote up to 9,341 output tokens on one target, so Sonnet gets room too.
DEFAULTS = {"haiku": {"max_tokens": 12000, "budget": 0.40},
            "sonnet": {"max_tokens": 16000, "budget": 3.00}}
OUT_ASSUMED = 4000  # output tokens per call, used only for the guess before any real call


def original_seconds(key_prefix):
    """Model time of the first live call with this key, from the ledger (a cached answer re-read takes about 0 s)."""
    f = getattr(llm, "LEDGER", None)
    if not f or not Path(f).exists():
        return None
    for line in Path(f).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("key") == key_prefix and row.get("mode") == "live" and not row.get("cached"):
            return row.get("seconds")
    return None


def pick_targets(spec):
    ids = ri.all_target_ids()
    if spec == ["all"]:
        return ids
    if spec == ["clean"]:
        return [i for i in ids if i.startswith("C")]
    if spec == ["variants"]:
        return [i for i in ids if i.startswith("V")]
    bad = [t for t in spec if t not in ids]
    if bad:
        sys.exit(f"unknown target(s): {' '.join(bad)}. Known: {' '.join(ids)}")
    return spec


def project(all_built, calls, cfg, model):
    """Guess the cost of all targets from the real calls so far (or from the default factor if none)."""
    model_id = llm.resolve_model(model, cfg)
    done = [(calls[t]["input_tokens"] / calls[t]["est_tokens"], calls[t]["output_tokens"])
            for t in calls if calls[t].get("input_tokens") and calls[t].get("est_tokens")]
    if done:
        ratio = sum(d[0] for d in done) / len(done)
        out_avg = sum(d[1] for d in done) / len(done)
        basis = f"from {len(done)} real call(s): input = estimate x {ratio:.2f}, output {out_avg:.0f} tokens per call"
    else:
        ratio, out_avg = ri.REAL_FACTOR, OUT_ASSUMED
        basis = f"no real call yet: input = estimate x {ratio}, output assumed {OUT_ASSUMED} per call"
    tin = sum(int(t["est_tokens"] * ratio) for t in all_built.values())
    tout = int(out_avg * len(all_built))
    usd = llm.cost_usd(model_id, {"input_tokens": tin, "output_tokens": tout}, cfg)
    return tin, tout, usd, basis


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)  # Git Bash otherwise holds all output until the program ends
    except (AttributeError, ValueError):
        pass
    cfg = llm.load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku", choices=["haiku", "sonnet"])
    ap.add_argument("--mode", default="mock", choices=["mock", "replay", "live"])
    ap.add_argument("--batch", default="r1", help="run name; output goes to results/review_<batch>_<model>/")
    ap.add_argument("--targets", nargs="+", default=["all"], help="ids, or all / clean / variants")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--budget", type=float, default=None, help="most USD this run may spend")
    ap.add_argument("--dry-run", action="store_true", help="no calls: sizes and cost guess only")
    ap.add_argument("--no-score", action="store_true", help="do not run review_score.py at the end")
    ap.add_argument("--sample", type=int, default=0, help="repeat number: a new number makes a new, paid call (noise check)")
    ap.add_argument("--retry-invalid", action="store_true",
                    help="ask once more for a target whose answer is not valid JSON (same rule for every model)")
    ap.add_argument("--code-set", default=None, help="extra code view, e.g. r2 (see review_extra_units.json)")
    a = ap.parse_args()

    max_tokens = a.max_tokens or DEFAULTS[a.model]["max_tokens"]
    budget = a.budget if a.budget is not None else DEFAULTS[a.model]["budget"]
    targets = pick_targets(a.targets)

    # build and check every input first: nothing is sent if one of them is wrong
    all_built = {tid: ri.build_target(tid, a.code_set) for tid in ri.all_target_ids()}
    for tid in targets:
        t = all_built[tid]
        bad = t["problems"] + t["leaks"] + (["comment markers found"] if t["comments"] else [])
        if bad:
            print(f"input of {tid} is not clean, nothing was sent:")
            for b in bad:
                print(f"   {b}")
            return 2

    model_id = llm.resolve_model(a.model, cfg)
    if a.dry_run:
        print(f"dry run: model {model_id}, {len(targets)} target(s), max output {max_tokens}, run limit ${budget:.2f}")
        for tid in targets:
            print(f"  {tid}: ~{all_built[tid]['est_tokens']} estimated tokens")
        tin, tout, usd, basis = project(all_built, {}, cfg, a.model)
        print(f"guess for all {len(all_built)} targets: ~{tin} input, ~{tout} output tokens, about ${usd:.3f}  ({basis})")
        return 0

    folder = f"review_{'mock_' if a.mode == 'mock' else ''}{a.batch}_{a.model}"
    out = ROOT / "results" / folder
    (out / "raw").mkdir(parents=True, exist_ok=True)
    calls_file = out / "calls.json"
    calls = json.loads(calls_file.read_text(encoding="utf-8")) if calls_file.exists() else {}
    retry_file = out / "calls_retry.json"
    retries = json.loads(retry_file.read_text(encoding="utf-8")) if retry_file.exists() else {}

    base = llm.LLMClient("mock").spent()
    client = llm.LLMClient(a.mode, base + budget)
    print(f"{folder}: mode {a.mode}, model {model_id}, {len(targets)} target(s), max output {max_tokens}, "
          f"run limit ${budget:.2f}\n")
    t_start = time.time()
    stopped = None
    for tid in targets:
        t = all_built[tid]
        sha = hashlib.sha256((t["system"] + "\n---USER---\n" + t["user"]).encode("utf-8")).hexdigest()
        try:
            r = client.complete(t["system"], t["user"], model=a.model, max_tokens=max_tokens,
                                tag=f"reviewer:{tid}:{a.batch}", sample=a.sample)
        except llm.BudgetExceeded as e:
            stopped = f"stopped before {tid}: {e}"
            break
        except llm.ReplayMiss as e:
            print(f"{tid}: no saved answer ({e})")
            continue
        except Exception as e:  # noqa: BLE001  (network or API problem: stop, do not burn money)
            stopped = f"stopped at {tid}: {type(e).__name__}: {e}"
            break
        (out / "raw" / f"{tid}.txt").write_text(r.text, encoding="utf-8")
        seconds = r.seconds
        if r.cached and a.mode != "mock":
            seconds = original_seconds(r.key[:16]) or r.seconds
        calls[tid] = {"model": r.model, "mode": a.mode, "input_tokens": r.input_tokens,
                      "output_tokens": r.output_tokens, "cost_usd": r.original_cost_usd, "paid_usd": r.cost_usd,
                      "seconds": round(seconds, 2), "truncated": r.truncated, "stop_reason": r.stop_reason,
                      "cached": r.cached, "est_tokens": t["est_tokens"], "prompt_sha256": sha, "max_tokens": max_tokens,
                      "sample": a.sample, "code_set": a.code_set}
        calls_file.write_text(json.dumps(calls, indent=1), encoding="utf-8")
        flag = "  CUT OFF (raise --max-tokens)" if r.truncated else ""
        ratio = r.input_tokens / t["est_tokens"] if a.mode != "mock" else 0
        print(f"{tid}: {r.input_tokens} in / {r.output_tokens} out, ${r.original_cost_usd:.4f}"
              f"{' (cached)' if r.cached else ''}, {seconds:.0f}s, stop {r.stop_reason}"
              f"{f', input = estimate x {ratio:.2f}' if ratio else ''}{flag}")
        if a.retry_invalid and a.mode != "mock":
            status, _, why = rs.parse_answer(r.text, r.truncated)
            if status != "ok":
                print(f"   {tid}: first answer is not valid ({'; '.join(why)}). One retry.")
                try:
                    r2 = client.complete(t["system"], t["user"], model=a.model, max_tokens=max_tokens,
                                         tag=f"reviewer:{tid}:{a.batch}:retry", sample=a.sample + 1)
                except (llm.BudgetExceeded, llm.ReplayMiss) as e:
                    print(f"   retry not made: {e}")
                else:
                    (out / "raw" / f"{tid}.retry1.txt").write_text(r2.text, encoding="utf-8")
                    secs2 = (original_seconds(r2.key[:16]) or r2.seconds) if r2.cached else r2.seconds
                    retries[tid] = {"model": r2.model, "mode": a.mode, "input_tokens": r2.input_tokens,
                                    "output_tokens": r2.output_tokens, "cost_usd": r2.original_cost_usd,
                                    "paid_usd": r2.cost_usd, "seconds": round(secs2, 2), "truncated": r2.truncated,
                                    "stop_reason": r2.stop_reason, "cached": r2.cached, "sample": a.sample + 1}
                    retry_file.write_text(json.dumps(retries, indent=1), encoding="utf-8")
                    ok2 = rs.parse_answer(r2.text, r2.truncated)[0] == "ok"
                    print(f"   retry: {r2.input_tokens} in / {r2.output_tokens} out, ${r2.original_cost_usd:.4f}"
                          f"{' (cached)' if r2.cached else ''}, answer {'valid' if ok2 else 'NOT valid again'}")

    print(f"\n{len(targets)} target(s) asked, {sum(1 for t in targets if t in calls)} answered, "
          f"{time.time() - t_start:.0f}s wall time")
    if stopped:
        print(stopped)
    print(client.summary())
    if a.mode != "mock" and calls:
        tin, tout, usd, basis = project(all_built, calls, cfg, a.model)
        print(f"guess for all {len(all_built)} targets with this model: ~{tin} input, ~{tout} output tokens, "
              f"about ${usd:.3f}  ({basis})")

    all_ids = ri.all_target_ids()
    have_all = all((out / "raw" / f"{t}.txt").exists() for t in all_ids)
    if have_all and not a.no_score:
        print("\nall targets answered: scoring")
        code = subprocess.run([sys.executable, str(PIPE / "review_score.py"), "--dir", str(out)], cwd=ROOT).returncode
        if retries:
            print("\nscoring again with the retry answers")
            code |= subprocess.run([sys.executable, str(PIPE / "review_score.py"), "--dir", str(out), "--with-retry"],
                                   cwd=ROOT).returncode
        return code
    if not have_all:
        print(f"\nnot all {len(all_ids)} targets have an answer yet, so no score was made. "
              f"Run review_score.py --dir results/{folder} when they do.")
    return 3 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())