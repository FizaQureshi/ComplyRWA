# ComplyRWA — Benchmark Data Record

**Author:** Member 3 (Charvi)  
**Branch:** `charvi-reports`  
**Date:** 2026-11-24  
**Purpose:** Single reference document for all detection, false-alarm, validity, cost, time, model and tool version numbers used in the Phase 5 evaluation report. Numbers are taken directly from saved results files; no pipeline runs were made to produce this document.

---

## 0. How to Reproduce

All results in this file can be verified without an API key or Foundry:

```bash
# Check detection / false-alarm table (hand-written tests)
cat results/variant_table.md

# Check three-way benchmark
cat results/benchmark_threeway.md

# Check generated-test quality
cat results/benchmark_generated.md

# Check LLM-only review runs
cat results/review_compare.md
cat results/review_triage.md

# Recompute API spend from the ledger
python3 -c "
import json, pathlib
from collections import defaultdict
records = [json.loads(l) for l in
    pathlib.Path('results/llm_ledger.jsonl').read_text().strip().split('\n')]
by_model = defaultdict(lambda: {'cost':0,'in':0,'out':0,'calls':0})
for r in records:
    m = r.get('model','?')
    by_model[m]['cost']  += r.get('cost_usd',0)
    by_model[m]['in']    += r.get('input_tokens',0)
    by_model[m]['out']   += r.get('output_tokens',0)
    by_model[m]['calls'] += 1
for m,v in by_model.items():
    print(m, v)
"

# Replay any demo (zero cost, no API key needed)
python pipeline/demo.py --target C01 --mode replay
python pipeline/demo.py --target V09 --mode replay
python pipeline/demo.py --target V04 --mode replay
```

> **Do not commit results/ after a replay run.**  
> Run `git checkout -- results` to discard the changes to `results/llm_ledger.jsonl` and `results/explain_d1+d2_blind/`.

---

## 1. Tool and Model Versions

All benchmark results depend on the exact versions below. Update this table if any version changes.

### 1.1 Development Tools

| Tool | Version | Check command |
|---|---|---|
| OS | Windows (native, no WSL) | — |
| Git | 2.37.3.windows.1 | `git --version` |
| Node.js | 20.20.2 (LTS) | `node -v` |
| npm | 10.8.2 | `npm -v` |
| Python | 3.11.9 | `python --version` (venv active) |
| Foundry (`forge`) | **1.8.7** | `forge --version` |
| Foundry commit SHA | `985eeea031d79922cd654d4e94e6c3701e1c7d73` | `forge --version` |
| Halmos | **0.3.3** | `halmos --version` |
| Hardhat | 2.14.0 | `npx hardhat --version` |

### 1.2 Pinned Target

| Item | Value |
|---|---|
| System | T-REX (ERC-3643) |
| Tag | **4.1.6** |
| Commit hash | `a09cfd38aa257d56db7ff9c90f30e65f125a141b` |
| Solidity compiler | 0.8.17 |
| Optimizer | enabled, 200 runs |
| ONCHAINID dependency | `@onchain-id/solidity` 2.1.0 |

### 1.3 LLM Models

| Alias | Full model name | Input price (USD / MTok) | Output price (USD / MTok) | Price source |
|---|---|---|---|---|
| haiku | `claude-haiku-5-5` | \$0.10 | \$0.50 | Anthropic pricing page, checked 2026-11-18 |
| sonnet | `claude-sonnet-5-5` | \$2.00 | \$10.00 | Anthropic pricing page, checked 2026-11-18 |

> Prices are in `pipeline/llm_config.json`. Haiku 5.5 charges higher prices for prompts over 100 K tokens; this project never reaches that threshold.  
> No temperature was set (`"temperature": null` in `llm_config.json`).

### 1.4 Foundry Fuzz Settings

| Setting | Value | Location |
|---|---|---|
| Fuzz seed | `0x436f6d706c79` | `foundry.toml` |
| Invariant runs | 64 | `foundry.toml` |
| Invariant depth | 40 | `foundry.toml` |
| EVM version | london | `foundry.toml` |

---

## 2. Test Configurations

21 configurations were used. 8 are correct ("clean"), 13 have one seeded compliance bug each ("variants").

### 2.1 Clean Configurations

| ID | Description | Hooks overridden |
|---|---|---|
| C01 | Full baseline — all modules bound, default params | none |
| C02 | Second trusted claim issuer | `_deployClaimIssuer`, `_registerInvestors` |
| C03 | Same-identity transfer between wallets of one identity | `_afterSetUp` |
| C04 | Recovery address wallets | `_afterSetUp` |
| C05 | Country module configured differently | `_configure` |
| C06 | Investor registered to a second country | `_registerInvestors` |
| C07 | Halmos-only scenario | `_afterSetUp` |
| C08 | Pre-setup mint to country-408 wallet (before compliance bound) | `_addModules` |

> C03, C04, C07 have partial test coverage — tests that need the MaxBalanceModule are marked `-` in the variant table (not applicable). C08 is fully covered. This is expected and documented.

### 2.2 Variant Configurations (seeded bugs)

| ID | Rule violated | Bug type | Linked gold tests |
|---|---|---|---|
| V01 | K1, K2 | Config — wrong identity registry | G01a, G01b, G06c |
| V02 | K1, K2 | Config — wrong claim issuer | G01a, G01b, G06c |
| V03 | K2 | Code — revocation check bypassed | G06c |
| V04 | K1, K3 | Config — KYC topic removed | G01a, G01b, G02a, G02b, G06c |
| V05 | J1 | Config — restricted country changed | G03a, G03b, G07, G08 |
| V06 | J1 | Code — country check bypassed | G03a, G03b, G07, G08 |
| V07 | J1 | Config — country module unbound | G03a, G03b, G07, G08 |
| V08 | J1 | Config — country module unbound (alt) | G03a, G03b, G07, G08 |
| V09 | H1, H3 | Config — MaxBalanceModule unbound | G04, G05a, G05b, G09, G10 |
| V10 | H1, H3 | Code — wrong MaxBalance implementation | G04, G05a, G05b |
| V11 | H1 | Config — MaxBalanceModule unbound (Halmos path) | G04, G05b |
| V12 | H3 | Code — forcedTransfer skips tracker update | G05a, G05b |
| V13 | H1 | Config — cap set to max uint256 | G04, G05b, G10 |

---

## 3. Hand-Written Tests — Detection and False Alarms

**Source file:** `results/variant_table.md`

### 3.1 Summary

| Metric | Value |
|---|---|
| Variants caught | **13 / 13** (100%) |
| Variants missed | 0 |
| False alarms on clean configs | **0 / 8** (0%) |
| LLM cost | \$0.00 |
| Foundry run time (compile + test) | **88 s** |
| Forge suites run | 38 (21 invariant + 17 scenario) |
| Total test cases | 208 (63 clean gold + 145 variant) |

### 3.2 Per-Variant Detection (18 gold tests × 21 configs)

Columns are the 18 gold test groups. PASS = no failure on this config. FAIL = at least one failure. `–` = test not applicable (C03, C04, C07 lack the MaxBalanceModule-dependent tests).

| Config | G01a | G01b | G02a | G02b | G03a | G03b | G04 | G05a | G05b-p | G05b-s | G06a | G06b | G06c | G07 | G08 | G09 | G10 | G13 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | **clean** |
| C02 | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | **clean** |
| C03 | P | P | – | – | P | P | P | P | P | – | – | – | – | – | – | – | – | – | **clean** |
| C04 | P | P | – | – | P | P | P | P | P | – | – | – | – | – | – | – | – | – | **clean** |
| C05 | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | **clean** |
| C06 | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | **clean** |
| C07 | P | P | – | – | P | P | P | P | P | – | – | – | – | – | – | – | – | – | **clean** |
| C08 | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | P | **clean** |
| V01 | **F** | **F** | P | **F** | P | P | P | P | P | P | P | P | **F** | P | P | P | P | P | **caught** |
| V02 | **F** | **F** | P | **F** | P | P | P | P | P | P | P | P | **F** | P | P | P | P | P | **caught** |
| V03 | **F** | **F** | P | P | P | P | P | P | P | P | P | P | **F** | P | P | P | P | P | **caught** |
| V04 | **F** | **F** | **F** | **F** | P | P | P | P | P | P | P | **F** | **F** | P | P | P | P | P | **caught** |
| V05 | P | P | P | P | **F** | **F** | P | P | P | P | P | P | P | **F** | **F** | P | P | P | **caught** |
| V06 | P | P | P | P | **F** | **F** | P | P | P | P | P | P | P | **F** | P | P | P | P | **caught** |
| V07 | P | P | P | P | **F** | **F** | P | P | P | P | P | P | P | **F** | **F** | P | P | P | **caught** |
| V08 | P | P | P | P | **F** | **F** | P | P | P | P | P | P | P | **F** | **F** | P | P | P | **caught** |
| V09 | P | P | P | P | P | P | **F** | **F** | **F** | **F** | P | P | P | P | P | **F** | **F** | P | **caught** |
| V10 | P | P | P | P | P | P | **F** | **F** | **F** | **F** | P | P | P | P | P | **F** | P | P | **caught** |
| V11 | P | P | – | – | P | P | **F** | **F** | **F** | – | – | – | – | – | – | – | – | – | **caught** |
| V12 | P | P | P | P | P | P | **F** | **F** | **F** | P | P | P | P | P | P | P | P | P | **caught** |
| V13 | P | P | P | P | P | P | **F** | P | P | P | P | P | P | P | P | **F** | **F** | P | **caught** |

P = PASS, F = FAIL, – = not applicable.

---

## 4. AI-Generated Tests — Validity, Detection, Cost, Time

**Source files:** `results/benchmark_generated.md`, `results/benchmark_threeway.md`

### 4.1 Generation Parameters

| Parameter | Value |
|---|---|
| Rules used for generation | 10 (H1 H2 H3 H4 J1 J2 J3 K1 K2 K3) |
| Tests requested per rule | 4 |
| Total tests per model | 40 |
| Generation batches | 2 (d1: rules H1–H4 and K1–K3; d2: rules J1–J3) |
| Validity filter steps | (1) compile; (2) fails on clean baseline C01?; (3) vacuousness check on C01 |
| Filter outcome labels | KEEP (valid, non-vacuous) · VACUOUS · REJECT (fails on clean) |

### 4.2 Validity Results

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| **KEEP** (valid + non-vacuous) | **32 (80%)** | **32 (80%)** |
| VACUOUS | 8 (20%) | 8 (20%) |
| REJECT (failed on clean) | 0 (0%) | 0 (0%) |

### 4.3 Detection Results

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Variants detected | **12 / 13** | **12 / 13** |
| Variant missed | V11 | V11 |
| False alarms on clean configs (tests rejected) | **0 / 8** (0 of 40 tests) | **0 / 8** (0 of 40 tests) |

> **Why V11 is missed:** V11 unbinds the MaxBalanceModule. The generated H1 tests read the cap through the module's getter. With the module unbound, the getter is never reached, so no test fails. The hand-written G04 catches V11 because it uses the policy cap stored in the fixture, not in the module.

### 4.4 Cost and Time

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| LLM calls (live) | 11 (1 truncated) | 10 (0 truncated) |
| Input tokens | 88 231 | 80 278 |
| Output tokens | 52 594 | 22 454 |
| **Generation cost (USD)** | **\$0.0351** | **\$0.3851** |
| Cost per rule | \$0.0035 | \$0.0385 |
| Model time (seconds, all calls) | 236 | 163 |
| Foundry run time | 171 | 134 |
| **Total wall time** | **407 s** | **297 s** |
| Explainer cost per finding (Haiku, Phase 4.6) | ~\$0.0014 | n/a |

> **Generation only.** These costs cover test generation. Running the tests (Foundry) has zero LLM cost.  
> The 1 truncated Haiku call was `generator:H1:d1`; a retry produced a valid result.

### 4.5 Per-Variant Coverage by Generated Tests

| Variant | Caught by Haiku? | Caught by Sonnet? |
|---|---|---|
| V01 | yes | yes |
| V02 | yes | yes |
| V03 | yes | yes |
| V04 | yes | yes |
| V05 | yes | yes |
| V06 | yes | yes |
| V07 | yes | yes |
| V08 | yes | yes |
| V09 | yes | yes |
| V10 | yes | yes |
| **V11** | **NO** | **NO** |
| V12 | yes | yes |
| V13 | yes | yes |

---

## 5. LLM-Only Review — Detection, False Alarms, Cost, Time

**Source files:** `results/review_compare.md`, `results/review_triage.md`

### 5.1 Run Index

Three independent batches were run, each with two models. Each batch = one call per target (21 targets). Runs r1b and r1 share input; r2 uses an expanded code view that also includes `Token.init`, `setCompliance`, `setIdentityRegistry`, `bindToken`, and `getTokenBound`.

| Run ID | Code view | Model | Retries allowed |
|---|---|---|---|
| r1 | Standard | Haiku 5.5 | 1 (invalid JSON) |
| r1 | Standard | Sonnet 5.5 | 1 (invalid JSON) |
| r1b | Standard (same input as r1) | Haiku 5.5 | 1 |
| r1b | Standard (same input as r1) | Sonnet 5.5 | 1 |
| r2 | Expanded (adds init/bind calls) | Haiku 5.5 | 1 |
| r2 | Expanded | Sonnet 5.5 | 1 |

### 5.2 Detection Rate

A variant counts as detected when the reviewer returns a HIGH or MEDIUM finding linked to the correct rule.

> **Reading guidance:** always present **first-answer** and **after-retry** detection together. Sonnet's JSON format is not always reliable on first attempt — presenting only the post-retry number overstates reliability. Haiku had zero format failures in r1 and r1b and is the more format-reliable model.

| Run | Model | Invalid JSON targets | Detected before retry | Detected after retry |
|---|---|---|---|---|
| r1 | Haiku 5.5 | 0 | 13 / 13 | 13 / 13 |
| r1 | Sonnet 5.5 | 1 (V08) | 12 / 13 | **13 / 13** |
| r1b | Haiku 5.5 | 0 | 13 / 13 | 13 / 13 |
| r1b | Sonnet 5.5 | 2 (V01, V05) | 11 / 13 | **13 / 13** |
| r2 | Haiku 5.5 | 1 (C02) | 13 / 13 | 13 / 13 |
| r2 | Sonnet 5.5 | 3 (V02, V09, V13) | 10 / 13 | 12 / 13 |

> Detection is stable for Haiku and Sonnet on the standard code view (r1/r1b). Sonnet r2's expanded code view introduced new invalid JSON responses; after one retry, 12/13 were recovered. V09 remained invalid in r2 Sonnet +retry.

### 5.3 False Alarms on Clean Configurations

Three counting methods are used to allow fair comparison:

- **Frozen:** any HIGH or MEDIUM finding on a clean target, before any analysis.
- **Adjusted:** frozen, but stock-gap findings on S03/S04 are excluded from the numerator.
- **After triage:** true false alarms only, as classified by the project team reading each finding against the code (see `results/review_triage.md`).

| Run | Model | Frozen | Adjusted | After triage |
|---|---|---|---|---|
| r1 | Haiku 5.5 | 7 / 8 | 2 / 8 | 1 / 8 |
| r1b | Haiku 5.5 | 5 / 8 | 1 / 8 | 1 / 8 |
| r2 | Haiku 5.5 (+retry) | 4 / 8 | 1 / 8 | 0 / 8 |
| r1 | Sonnet 5.5 (+retry) | 1 / 8 | 1 / 8 | 0 / 8 |
| r1b | Sonnet 5.5 (+retry) | 1 / 8 | 1 / 8 | 0 / 8 |
| r2 | Sonnet 5.5 (+retry) | 1 / 8 | 0 / 8 | 0 / 8 |

**Run-to-run ranges (official runs r1 and r1b, same input):**

| Model | Frozen range | Adjusted range | After triage |
|---|---|---|---|
| Haiku 5.5 | 5–7 of 8 (63–88%) | 1–2 of 8 (13–25%) | 1 of 8 (13%) in both runs |
| Sonnet 5.5 | 1 of 8 (13%) in both runs | 1 of 8 (13%) in both runs | 0 of 8 (0%) in both runs |

### 5.4 Triage Classification of Clean-Config Findings

Manual triage by the project team (see `results/review_triage.md`). An independent evaluator should verify these labels.

| Category | Description | Which targets | Which runs |
|---|---|---|---|
| **Stock gap S03/S04** | Revoked claim re-added via twin signature or v-byte trick. Real dependency gap, proven by `StockGaps.t.sol`. | C01 C02 C03 C05 C06 C07 (Haiku r1); C01 C03 C04 (Haiku r2) | Haiku: all 3 runs. Sonnet: once (C06, r2 only) |
| **Real finding (C08)** | Country-408 wallet holds tokens minted before compliance was bound. Not a seeded bug; documented gap in C08's design. | C08 | Haiku r1, r2; Sonnet r1, r1b |
| **False alarm (missing input)** | J3 "token binding never happens" — `Token.init` was not in the code view, so the reviewer could not confirm the bind step. Fixed in r2 code view. | C04 (r1), C02 (r1b) | Haiku r1 and r1b only. Not present in r2 or any Sonnet run. |

### 5.5 Cost and Time per Run

Computed from `results/llm_ledger.jsonl` (live calls, tag prefix = `reviewer`).

| Run | Model | Calls | Input tokens | Output tokens | **Cost (USD)** | Model time (s) |
|---|---|---|---|---|---|---|
| r1 | Haiku 5.5 | 21 | 335 658 | 85 812 | **\$0.0765** | 797 |
| r1 | Sonnet 5.5 | 21 | 351 617 | 25 664 | **\$0.9599** | 244 |
| r1b | Haiku 5.5 | 21 | 335 658 | 86 024 | **\$0.0766** | 401 |
| r1b | Sonnet 5.5 | 21 | 367 603 | 26 207 | **\$0.9571** | 229 |
| r2 | Haiku 5.5 (+retry) | 22 | 369 707 | 81 646 | **\$0.0778** | 381 |
| r2 | Sonnet 5.5 (+retry) | 24 | 402 595 | 28 850 | **\$1.0937** | 257 |

> Model time = sum of API call times. Foundry is not used in the review approach.  
> r1b Sonnet cost (\$0.9571) differs slightly from \$0.9973 quoted in `benchmark_threeway.md` because the ledger records cost_usd (actual, with mock/replay zeroed) while the threeway table was written from the original_cost_usd column.

---

## 6. Three-Way Comparison Summary

**Source:** `results/benchmark_threeway.md`

| Method | Model | Variants detected | False alarms (after triage) | Cost (USD) | Total time |
|---|---|---|---|---|---|
| Hand-written Foundry tests | — | **13 / 13** | **0 / 8** | \$0.00 | 88 s |
| AI-generated tests | Haiku 5.5 | 12 / 13 | 0 / 8 | \$0.0351 | 407 s |
| AI-generated tests | Sonnet 5.5 | 12 / 13 | 0 / 8 | \$0.3851 | 297 s |
| LLM-only review (r1) | Haiku 5.5 | 13 / 13 | 1 / 8 | \$0.0765 | 797 s |
| LLM-only review (r1 +retry) | Sonnet 5.5 | 13 / 13 | 0 / 8 | \$0.9599 | 244 s |

---

## 7. Total API Spend

**Source:** `results/llm_ledger.jsonl` (323 records). Computed 2026-11-24.

### 7.1 By Model

| Model | Live calls | Input tokens | Output tokens | Cost (USD) |
|---|---|---|---|---|
| `claude-haiku-5-5` | 212 | 2 509 940 | 665 796 | \$0.3082 |
| `claude-sonnet-5-5` | 111 | 1 633 960 | 151 681 | \$3.3958 |
| **Total** | **323** | **4 143 900** | **817 477** | **\$3.7039** |

> Mock and replay calls recorded 0 cost. 25 mock calls + 36 replay calls = 61 non-live records.  
> 2 calls were truncated (1 Haiku generator d1; 1 Haiku reviewer r2 C02). Both received retries.

### 7.2 By Pipeline Stage

| Stage | Calls | Input tokens | Output tokens | Cost (USD) | Model time (s) |
|---|---|---|---|---|---|
| Generator | 33 | 264 128 | 101 667 | \$0.4230 | 416 |
| Reviewer | 239 | 3 737 163 | 623 816 | \$3.2415 | 2 309 |
| Explainer | 49 | 142 567 | 91 964 | \$0.0394 | 308 |
| Smoke / other | 2 | 42 | 30 | \$0.0000 | 1 |
| **Total** | **323** | **4 143 900** | **817 477** | **\$3.7039** | **3 034** |

> Generator and explainer totals include both Haiku and Sonnet calls across all batches. Reviewer total includes r1, r1b, and r2 for both models.

### 7.3 Generator Detail by Batch and Model

| Batch | Model | Calls | Truncated | Input | Output | Cost | Model time (s) |
|---|---|---|---|---|---|---|---|
| d1 | Haiku 5.5 | 5 | 1 | 43 437 | 21 890 | \$0.0153 | 101 |
| d2 | Haiku 5.5 | 1 | 0 | 7 953 | 5 285 | \$0.0034 | 24 |
| d1+d2 (blind) | Haiku 5.5 | 6 | 0 | 46 157 | 29 207 | \$0.0192 | 128 |
| d1+d2 | Sonnet 5.5 | 10 | 0 | 80 278 | 22 454 | \$0.3851 | 163 |

> "blind" = the generator was given only the policy text and fixture API, without being shown the target configuration. This is the production mode.

---

## 8. Hardhat Baseline (T-REX Own Tests)

Included for completeness. These confirm the pinned code is correct before any ComplyRWA tests run.

| Metric | Value |
|---|---|
| Test suite | Hardhat (T-REX's own suite) |
| Command | `npm ci && npx hardhat compile && npx hardhat test` |
| Passing | **777** |
| Failing | **0** |
| Run time | ~1 minute |

---

## 9. Notes on Reproducibility

1. **Fuzz seed is fixed.** All fuzz-dependent cells in the detection table are deterministic. The same FAIL/PASS pattern is reproduced on any machine with Foundry 1.8.7 and the same seed.
2. **LLM calls are cached.** Replay mode (`--mode replay`) returns cached responses at zero cost. Run-to-run variation in LLM outputs is real (see Section 5.3 ranges); the numbers in this document come from the saved official runs.
3. **Mock mode was used for development only.** Mock calls recorded 0 cost and are excluded from the totals in Sections 7.1–7.3.
4. **Price check status.** Prices in `pipeline/llm_config.json` were verified against Anthropic's pricing page on 2026-11-18. Re-verify before the final report submission if more than two weeks have passed.
5. **Model pinning.** Anthropic does not expose a version-pinned endpoint for Haiku 5.5 or Sonnet 5.5. If the underlying model weights change, results may differ. The only reproducibility guarantee is via the LLM cache.
6. **environment.md** is the authoritative version record. This file copies from it. If a tool version changes, update `docs/environment.md` first, then update Section 1 of this file.

---

*This document is part of the Phase 5 deliverables. All source data is in the `results/` folder. Do not modify `results/`, `results/llm_cache`, `pipeline/`, or `test/` without coordinating with the project lead.*
