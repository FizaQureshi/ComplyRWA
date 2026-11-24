# ComplyRWA Phase 5 — Evaluation Report

**Author:** Member 3 (Charvi)  
**Branch:** `charvi-reports`  
**Date drafted:** 2026-11-24  
**Pinned system:** T-REX 4.1.6 (commit `a09cfd3`), Solidity 0.8.17, Foundry 1.8.7, Halmos 0.3.3  

---

## 1. What ComplyRWA Does

ComplyRWA checks whether a tokenised real-world asset (a T-REX / ERC-3643 token) actually follows the compliance rules its issuer wrote. The issuer types in plain-English rules such as "only KYC-verified investors may receive tokens" or "no investor may hold more than 1 000 tokens." The pipeline converts those rules into executable Foundry test code, runs the tests against the token's on-chain configuration, and returns a report that explains every violation in plain language and tells the issuer how to fix it.

**What is new in Phase 5:** this document is the independent evaluation and write-up of Phases 3 and 4. No new pipeline runs are made; all numbers come from the saved results files in this repository.

---

## 2. What Was Measured

Three testing approaches were compared on the same 21 token configurations: 13 deliberately broken ones (V01–V13) and 8 correct ones (C01–C08).

| Approach | What it needs |
|---|---|
| **Hand-written Foundry tests** | A developer writes tests once; they run on every config |
| **LLM-generated tests** | The pipeline converts the policy text into tests; a validity filter removes bad ones |
| **LLM-only code review** | An LLM reads each config's code and reports findings directly, with no tests run |

The source files for this section are:
- `results/variant_table.md` (hand-written test results, all 21 configs × 18 tests)
- `results/benchmark_threeway.md` (three-way comparison table)
- `results/benchmark_generated.md` (generated-test quality detail)
- `results/review_compare.md` (all LLM review runs)
- `results/review_triage.md` (manual triage of false alarms on clean configs)

---

## 3. Main Results

### 3.1 Hand-Written Tests — the Baseline

| Metric | Result |
|---|---|
| Bugs caught | **13 of 13** (100%) |
| False alarms on the 8 clean configs | **0 of 8** (0%) |
| LLM cost | \$0 |
| Total time (compile + run) | 88 s |

The 18 hand-written gold tests (G01a–G13) form the answer key for this project. They were written by one person who also designed the variants, which is an acknowledged bias (see Section 7).

The full pass/fail table for all 21 configurations × 18 tests is in `results/variant_table.md`. Every variant (V01–V13) is caught by at least one linked test while every clean configuration (C01–C08) passes all 18 tests.

### 3.2 AI-Generated Tests

The pipeline is given only the five-rule policy text; it never sees the variant configurations. It generated 40 test functions (4 per rule × 10 rules) across two batches, run once with Haiku 5.5 and once with Sonnet 5.5.

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| Valid and non-vacuous (KEEP) | 32 / 40 = **80%** | 32 / 40 = **80%** |
| Vacuous (passed on clean but trivially) | 8 | 8 |
| Rejected (failed on clean config) | 0 | 0 |
| Bugs caught | **12 of 13** | **12 of 13** |
| False alarms on clean configs | **0 of 8** | **0 of 8** |
| Input / output tokens | 88 231 / 52 594 | 80 278 / 22 454 |
| **Cost (generation only)** | **\$0.035** | **\$0.385** |
| Model time | 236 s | 163 s |
| Total time (model + Foundry) | 407 s | 297 s |

**What is missed.** Both models miss V11 — a configuration where the MaxBalanceModule is unbound. The generated tests for rule H1 always use the module's own cap getter; because the module is not bound, the getter is never called, so no test fails. The hand-written G04 catches V11 because it reads the real policy cap from the fixture directly.

**Cost per rule.** At the per-rule level, Haiku costs \$0.0035 and Sonnet costs \$0.0385 — roughly an 11× difference for the same detection rate. The explainer adds about \$0.0014 per finding on Haiku (Phase 4 step 4.6).

**Validity filter.** The filter runs every candidate test against the clean baseline (C01) before accepting it. A test that fails there is rejected; a test that always passes on every input (vacuous) is flagged. 80% of generated tests survive both checks, which is in line with Phase 4's expectation of "most generated tests are useful."

### 3.3 LLM-Only Code Review

The reviewer LLM reads each configuration's code (with comments removed) and returns findings directly, without running any tests. Two models were used in two rounds (r1, r1b = same input repeated; r2 = expanded code view).

> **Important:** Sonnet's first answers were invalid JSON in several targets across runs (1 target in r1, 2 in r1b, 3 in r2). One retry was allowed per invalid answer. Detection rates **must be read with their pre-retry and post-retry figures together** — presenting only the post-retry number overstates reliability. The pre-retry rates show that Sonnet's JSON format is not always reliable on first attempt.

**Detection rates — official runs r1 (first answer / after one retry):**

| Model | First-answer detection | After one retry | Invalid JSON targets |
|---|---|---|---|
| Haiku 5.5 | **13/13** | 13/13 (no retries needed) | 0 |
| Sonnet 5.5 | **12/13** | **13/13** | 1 (V08) |

**Run-to-run stability (r1b — same input as r1, repeated):**

| Model | First-answer detection | After retry | Invalid JSON targets |
|---|---|---|---|
| Haiku 5.5 | **13/13** | 13/13 | 0 |
| Sonnet 5.5 | **11/13** | **13/13** | 2 (V01, V05) |

Both models detect all 13 bugs once retries on invalid JSON are allowed. Haiku is more reliable on first attempt (0 format failures in r1 and r1b). Sonnet's first-attempt detection varies: 12/13 in r1, 11/13 in r1b — all misses are format failures, not genuine non-detections.

**False-alarm rate (clean configs, r1 and r1b range):**

| Model | Frozen (any HIGH/MED on clean) | Adjusted (excl. stock gaps) | After triage (true false alarms) |
|---|---|---|---|
| Haiku 5.5 | 5–7 of 8 (63–88%) | 1–2 of 8 (13–25%) | 1 of 8 (13%) |
| Sonnet 5.5 | 1 of 8 (13%) | 1 of 8 (13%) | 0 of 8 (0%) |

Three categories of clean-config findings were identified by manual triage (see `results/review_triage.md`):

1. **Stock gap S03/S04** — revoked claims can be re-added with a twin signature or v-byte trick. This is a real dependency gap in ONCHAINID, proven by `StockGaps.t.sol`. Haiku reported it on 3–5 clean targets per run; Sonnet reported it once.
2. **Real finding (C08)** — C08 mints tokens to a restricted-country wallet before compliance is bound. The gold tests never count this because they only judge calls made after setup. The review correctly identifies it; it is not a false alarm.
3. **False alarm (missing input)** — Haiku once reported "token binding never happens" (J3) because `Token.init` and `setCompliance` were not in the code view the reviewer was shown. This is a prompt-engineering / input-preparation bug, not a model error.

**Important caveat:** the reviewer sees each configuration's own code, so it has an advantage over a blind audit. This makes the detection numbers an upper bound for a real production scenario.

---

## 4. Three-Way Summary

The table below shows the nuanced picture the brief requires. Detection rates for the LLM-only review are shown as **first-answer / after retry** — do not use the post-retry number alone.

| Method | Model | Bugs caught (first answer) | Bugs caught (after retry) | False alarms — frozen / adjusted / after triage | Cost (USD) |
|---|---|---|---|---|---|
| Hand-written Foundry tests | — | **13 / 13** | n/a | 0 / 0 / 0 of 8 | \$0 |
| AI-generated tests | Haiku 5.5 | 12 / 13 | n/a | 0 / 0 / 0 of 8 | \$0.035 |
| AI-generated tests | Sonnet 5.5 | 12 / 13 | n/a | 0 / 0 / 0 of 8 | \$0.385 |
| LLM-only review (r1) | Haiku 5.5 | **13 / 13** | n/a | 7 / 2 / 1 of 8 | \$0.077 |
| LLM-only review (r1) | Sonnet 5.5 | **12 / 13** | **13 / 13** | 1 / 1 / 0 of 8 | \$0.960 |
| LLM-only review (r1b repeat) | Haiku 5.5 | **13 / 13** | n/a | 5 / 1 / 1 of 8 | \$0.077 |
| LLM-only review (r1b repeat) | Sonnet 5.5 | **11 / 13** | **13 / 13** | 1 / 1 / 0 of 8 | \$0.997 |

> **False alarm columns:** "frozen" = any HIGH/MEDIUM on a clean target; "adjusted" = excluding known stock-gap findings (S03/S04); "after triage" = true false alarms only after the team read each finding. Triage labels have not yet been independently verified — this is one of the evaluator's tasks (Section 6.4).

**Plain-language takeaway:**

- **Hand-written tests** are the gold standard: 13/13 with zero false alarms, zero cost beyond developer time.
- **AI-generated tests** (both models) achieve 12/13 with zero false alarms and generation costs under \$0.40. Both miss V11 for the same structural reason (see Section 3.2). The two models give identical detection and validity results; Haiku at ~\$0.035 is roughly 11× cheaper than Sonnet at ~\$0.385 for the same outcome.
- **LLM-only review** finds all 13 bugs but requires human triage of false alarms. **Sonnet's pre-retry detection varies (12/13 and 11/13 on the same input), and these misses are entirely due to invalid JSON responses, not failure to identify the bug.** After one retry, both models reach 13/13. Haiku is more format-reliable (0 JSON failures) but produces more noise on clean configs (1 true false alarm per 8, vs 0 for Sonnet after triage).

---

## 5. Total API Spend

Computed from `results/llm_ledger.jsonl` (323 records across all phases):

| Model | Calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|
| claude-haiku-5-5 | 212 | 2 509 940 | 665 796 | \$0.31 |
| claude-sonnet-5-5 | 111 | 1 633 960 | 151 681 | \$3.40 |
| **Total** | **323** | **4 143 900** | **817 477** | **\$3.70** |

Prices used (from `pipeline/llm_config.json`, checked against Anthropic's pricing page on 2026-11-18): Haiku 5.5 at \$0.10 / MTok in and \$0.50 / MTok out; Sonnet 5.5 at \$2.00 / MTok in and \$10.00 / MTok out.

---

## 6. Independent Evaluation

### 6.1 Process

Five audit reports were chosen to cover the main finding patterns:

| Target | Pattern | Report path |
|---|---|---|
| C01 | Clean — nothing found | `results/demo_C01/report.md` |
| V04 | One cause, many symptoms (KYC topic removed) | `results/demo_V04/report.md` |
| V05 | Wrong-country restriction not enforced | `results/demo_V05/report.md` |
| V09 | Holding-limit module unbound | `results/demo_V09/report.md` |
| V12 | Hidden counter bug in forced-transfer | `results/demo_V12/report.md` |

Each evaluator was given the five `report.md` files and the following questionnaire. They were not told which targets are broken.

### 6.2 Questionnaire

> **Instructions:** You are a token issuer who does not know the technical internals of the system. Please read each report and answer the five questions below for each one. Use the 1–5 scale where 1 = not at all, 5 = completely.

| Q# | Question |
|---|---|
| Q1 | In your own words, what is the main problem this report describes? (Or: does it say everything is fine?) |
| Q2 | Do you understand what needs to be fixed, and who should fix it? (1 = no idea, 5 = very clear) |
| Q3 | Is the evidence given (failing test, reproduce steps) convincing to you? (1 = not convincing, 5 = very convincing) |
| Q4 | Is anything in the report confusing or unclear? Please note it. (1 = very confusing, 5 = perfectly clear) |
| Q5 | Overall, how actionable is this report for you as an issuer? (1 = I do not know what to do, 5 = I know exactly what to do) |

### 6.3 Results Table

> **Note on evaluator:** The evaluator should ideally be someone outside the project team who has basic familiarity with token issuance but no knowledge of the pipeline's internals. If no outside evaluator is available before the deadline, Member 2 or the project lead may be used as a fallback; this must be stated. **This table is a template — fill it in after the evaluation session and before the final submission.**

| Report | Evaluator | Q1 (summary in their words) | Q2 (fix clarity, /5) | Q3 (evidence, /5) | Q4 (clarity, /5) | Q5 (actionability, /5) | Notes |
|---|---|---|---|---|---|---|---|
| C01 | [name] | [their words] | — | — | — | — | |
| V04 | [name] | [their words] | /5 | /5 | /5 | /5 | |
| V05 | [name] | [their words] | /5 | /5 | /5 | /5 | |
| V09 | [name] | [their words] | /5 | /5 | /5 | /5 | |
| V12 | [name] | [their words] | /5 | /5 | /5 | /5 | |

### 6.4 Additional Items the Evaluator Can Check (time permitting)

The following checks have only been done by the person who wrote the bugs and the prompts. An independent check is valuable:

1. **`results/review_triage.md`** — the triage labels (stock gap / real finding / false alarm) on clean-config findings. The labels were assigned by the project team after seeing the LLM's output. An independent reader should decide whether they agree.
2. **Generated test validity** — do the 32 "KEEP" tests in `results/benchmark_generated.md` actually test what the corresponding rule text says? The validity filter only checks that a test compiles, is non-vacuous on the clean baseline, and does not fail on the clean baseline; it does not check semantic alignment.
3. **Explanation correctness** — does the plain-language explanation in each report's "Findings" section correctly describe what the failing test shows? Only two explanations (V02 and V12) were checked against the test code during Phase 4.

---

## 7. Limitations

The following limitations apply to all numbers in this report. They are stated honestly, not buried.

1. **Single pinned system.** Only T-REX 4.1.6 was tested. The pipeline's approach is designed to generalise to other ERC-3643 implementations, but no such generalisation has been verified.

2. **Three rule categories only.** KYC (K1–K5), jurisdiction (J1–J4) and holding-limit (H1–H4) cover the main compliance dimensions for real-world asset tokens. Other rule categories (transfer restrictions, lock-up periods, whitelist sizes) are out of scope.

3. **One person designed the bugs.** The 13 seeded variants were chosen by one author. A different set of bugs — especially subtler configuration errors or cross-module interactions — could give a different detection rate.

4. **Small clean-config set.** Eight clean configurations is a small sample for measuring false-positive rates. One false alarm equals 12.5%. The numbers should not be over-interpreted.

5. **AI results vary between runs.** The LLM-generated tests and LLM-only review results are from single or at most two runs per model. Run-to-run ranges are quoted where available (r1 and r1b for the review), but are not available for the generator. The generator was tested in two batches (d1 and d2).

6. **The reviewer sees its own code.** The LLM-only reviewer is given each configuration's own source code with comments removed. In a real blind audit, the reviewer would not have this advantage. The detection rates for the review approach are therefore an upper bound.

7. **Replay mode.** All demo runs use `--mode replay`; answers come from the LLM cache and do not reflect live API responses. Replay guarantees reproducibility but does not test the API path.

8. **MaxBalanceModule licence.** `MaxBalanceModule` (and its variants `MaxBalanceModuleV10`) are released under CC-BY-NC-4.0 (non-commercial). Any commercial deployment of ComplyRWA that includes or depends on this module requires a separate licence from the copyright holder.

---

## 8. Environment and Reproducibility

No tool versions changed during Phase 5. The environment record in `docs/environment.md` (last updated 2026-11-22) is current:

| Tool | Version |
|---|---|
| Python | 3.11.9 |
| Foundry (`forge`) | 1.8.7 |
| Halmos | 0.3.3 |
| Node.js | 20.20.2 |
| claude-haiku-5-5 | (Anthropic hosted, no version pinning) |
| claude-sonnet-5-5 | (Anthropic hosted, no version pinning) |

All saved results, the LLM cache (`results/llm_cache`), pipeline code and test files were left unmodified. If any of those change, the numbers above stop matching.

---

## 9. What Comes Next

| Item | Owner | Due |
|---|---|---|
| Evaluator name and contact confirmed | Member 3 (Charvi) | [date] |
| Questionnaire responses filled in (Section 6.3) | Member 3 (Charvi) | [date] |
| Demo recording or script finalised | Member 3 (Charvi) | [date] |
| Price check: confirm llm_config.json prices against Anthropic page | Member 3 (Charvi) | Before final submission |

---

*This report was prepared by Member 3. Full technical details are in `docs/Phase3.md` and `docs/Phase4.md`. Do not re-run the pipeline or modify the saved results without coordinating with the project lead.*
