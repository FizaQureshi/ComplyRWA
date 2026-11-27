# ComplyRWA Phase 5 — Evaluation Report (DRAFT)

**Author:** Member 3 (Charvi) · **Branch:** `charvi-reports` · **Date:** 2026-11-24  
**Pinned system:** T-REX 4.1.6 (`a09cfd3`), Solidity 0.8.17, Foundry 1.8.7, Halmos 0.3.3

---

## 1. What ComplyRWA Does

ComplyRWA checks whether a tokenised real-world asset (T-REX / ERC-3643) token actually follows the compliance rules its issuer wrote in plain English. The issuer types rules such as "only KYC-verified investors may receive tokens" or "no investor may hold more than 1 000 tokens." The pipeline converts those rules into executable Foundry test code, runs the tests against the token's on-chain configuration, and returns a plain-language report explaining every violation and how to fix it.

**What is new in Phase 5:** This document is the evaluation write-up of Phases 3 and 4. No new pipeline runs are made; all numbers come from saved results files in this repository.

---

## 2. Benchmark Results

Three approaches were compared on 21 token configurations: 13 deliberately broken (V01–V13) and 8 correct (C01–C08). Full numbers and configuration breakdowns are in `reports/benchmark_data.md`.

### Method and Scoring Definitions
From `results/benchmark_threeway.md`:
- **Detected ("caught"):** For hand-written and generated tests, a variant counts when a linked or any test fails on that variant while passing on every clean configuration. For LLM review, a variant counts when the model reports a HIGH or MEDIUM finding on a linked rule.
- **False alarm:** For tests, any test that fails on a clean configuration is rejected (so clean configs suffer 0 false positives). For LLM review, any HIGH or MEDIUM finding on a clean configuration is counted (frozen = all flags; adjusted = excluding known ONCHAINID stock gaps S03/S04; after triage = true false alarms only).

### Hand-written tests (baseline)
13/13 bugs caught · 0/8 false alarms · \$0 LLM cost · 88 s Foundry run (compile + test). These tests form the answer key.

### AI-generated tests
The pipeline was given 10 rules (H1–H4, J1–J3, K1–K3) and generated 4 tests per rule = 40 tests total per model. (The 5-rule demo audits generate 20 tests; the 10-rule benchmark generates 40).

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| Valid and non-vacuous (KEEP) | **32 / 40 = 80%** | **32 / 40 = 80%** |
| Vacuous | 8 | 8 |
| Rejected (failed on clean config) | 0 | 0 |
| Bugs caught | **12 / 13** | **12 / 13** |
| False alarms on clean configs | **0 of 40 tests rejected for failing on a clean configuration** | **0 of 40 tests rejected for failing on a clean configuration** |
| Generation cost | **\$0.035** | **\$0.385** |
| Model time | 236 s | 163 s |

80% of generated tests are valid and non-vacuous, exceeding the 70% project target. The cost per rule is \$0.0035 (Haiku) vs \$0.0385 (Sonnet) — roughly 11× more expensive for the same result. Haiku's tokens (88,231 input) come from batches d1, d2 and e1 (11 calls); Sonnet's from batch s1 (10 calls).

**Why V11 is missed by both models.** V11 starts with Bob already holding 800 tokens and sets the module's tracked balance to 0 via `batchPreSetModuleState`. Scenario tests assume an empty start and are skipped on V11; only property tests run on it. The generated tests are scenario-style, so none run on V11, and nothing fails.

### LLM-only review

> **Always read first-answer and after-retry rates together.** Presenting only the post-retry number overstates reliability.

| Run | Model | First-answer detection | After one retry | True false alarms (after triage) | Cost |
|---|---|---|---|---|---|
| r1 (official) | Haiku 5.5 | **13/13** | — | 1/8 (C04) | \$0.077 |
| r1 (official) | Sonnet 5.5 | **12/13** | **13/13** | 0/8 | \$0.960 |
| r1b (repeat) | Haiku 5.5 | **13/13** | — | 1/8 (C02) | \$0.077 |
| r1b (repeat) | Sonnet 5.5 | **11/13** | **13/13** | 0/8 | \$0.997 |

Haiku had zero JSON format failures. Sonnet's misses before retry were format failures (invalid JSON). In the sensitivity run r2 (expanded code view), Sonnet reached 12/13 even after retry (V09 failed formatting twice). Across runs r1 and r1b, Haiku's false alarms on clean configurations were 5–7 of 8 (63–88%) frozen, 1–2 of 8 (13–25%) after excluding stock-gap findings, and 1 of 8 after manual triage. Sonnet had 1 of 8 frozen (C08), 1 of 8 adjusted, and 0 of 8 after triage in both runs.

---

## 3. Three-Way Summary

| Method | First-answer detection | After retry | False alarms (after triage) | Cost |
|---|---|---|---|---|
| Hand-written Foundry tests | **13/13** | n/a | 0 of 8 configurations | \$0 |
| AI-generated tests (Haiku) | 12/13 | n/a | 0 of 40 tests rejected on clean | \$0.035 |
| AI-generated tests (Sonnet) | 12/13 | n/a | 0 of 40 tests rejected on clean | \$0.385 |
| LLM-only review — Haiku r1 | **13/13** | n/a | 1 of 8 configurations | \$0.077 |
| LLM-only review — Sonnet r1 | **12/13** | **13/13** | 0 of 8 configurations | \$0.960 |

**Plain-language takeaway:** Hand-written tests detect 13/13 with zero false alarms. AI-generated tests (Haiku) achieve 92% detection (12/13) at \$0.035 with no false alarms. Sonnet costs 11× more for identical detection and validity on this benchmark. The LLM-only review reaches 13/13 in r1/r1b but requires human triage: Haiku's raw false-alarm rate on clean configs is 63–88% before triage (13–25% after excluding stock gaps, dropping to 13% after manual triage). Sonnet's first-answer detection is 10–12/13 across runs due to invalid JSON, and in run r2 it remained 12/13 even after retry.

---

## 4. Independent Evaluation

**Evaluator:** Poorvi — independent reviewer, outside the project team. The evaluator read the five reports without being told in advance which described a problem or what the bugs were.  
**Full record:** `reports/independent_evaluation.md` — contains per-report Q1–Q5 answers, all three deep-dive checks, and the results summary.

**Five reports shown:** C01 (clean), V04 (KYC bypassed), V05 (wrong country restricted), V09 (holding limit removed), V12 (forced transfer skips tracker). Each read cold from `results/demo_<target>/report.md`.

| Report | Q1 (problem found?) | Q2 Fix clarity | Q3 Evidence | Q4 Clarity | Q5 Actionable | Key feedback |
|---|---|---|---|---|---|---|
| Report A (C01) | No problem — all clean | N/A | N/A | 5/5 | 5/5 | "forcedTransfer" needs a one-line gloss for non-technical readers |
| Report B (V04) | Yes — KYC bypassed; side-effect H3 correctly identified | 4/5 | 5/5 | 4/5 | 4/5 | "direct evidence: 0 of 1" is counterintuitive; "idA" needs introduction |
| Report C (V05) | Yes — country restriction not enforced | 4/5 | 5/5 | 5/5 | 4/5 | Clearest failing report |
| Report D (V09) | Yes — cap and tracker both broken | 4/5 | 5/5 | 4/5 | 4/5 | Symptom hint excellent; "0 != 500" needs lay explanation |
| Report E (V12) | Yes — forced transfer skips tracker | 5/5 | 5/5 | 5/5 | 5/5 | Most precisely diagnosed report |

**Average scores:**

| Question | Average |
|---|---|
| Q2 Fix clarity (failing reports B–E) | **4.25 / 5** |
| Q3 Evidence (failing reports B–E) | **5.00 / 5** |
| Q4 Report clarity (all five) | **4.60 / 5** |
| Q5 Actionability (all five) | **4.40 / 5** |

**Key findings:**
- Evidence quality is high across all reports: exact assertion failure values, numbered reproduction steps, inline test code (Q3 = 5.0/5).
- Fix clarity is good but not complete: reports name which functions to inspect and suggest where to look, but do not state the precise configuration value that is wrong. A developer intermediary is needed for a non-technical issuer (Q2 = 4.25/5).
- Side-effect handling in V04 works: H3 is correctly identified as a side effect of the KYC failure, and the note "All failing H3 tests are side effects of the KYC failure above. No separate holding-limit problem is shown" prevents false root-cause chasing.
- Technical vocabulary (forcedTransfer, idA, identity balance, CAP) is used without definition. A short glossary would bring several reports from 4/5 to 5/5 on clarity.
- Report E (V12) is the best-written problem report: one rule, one test, concrete numbers (75 ≠ 50), named function (`forcedTransfer`), specific fix.
- Deep-dive: triage labels in `review_triage.md` are consistent and defensible. The K1 test coverage has a known gap (untrusted-issuer scenario not covered). The V12 "What went wrong" paragraph matches the reproduction steps exactly (minor note: "both wallets" phrasing could be clarified).

---

## 5. Limitations

1. **Hand-written tests are the answer key:** They were written by the same author as the variants, so their 100% detection rate is not an independent head-to-head evaluation.
2. **Single pinned system:** Only T-REX 4.1.6 tested.
3. **Three rule categories only:** KYC, jurisdiction, holding limit.
4. **13 variants designed by one person:** Covers core rules, but not all real-world edge cases.
5. **Small clean-config set:** 8 configurations; one false alarm equals 12.5%.
6. **No run-to-run range for generated tests:** Each model generated the benchmark suites in a single official run.
7. **Reviewer sees target code:** Detection rates are an upper bound compared to a true blind audit.
8. **Web demo interface limits:**
   - The 5 demo rules are fixed and read-only.
   - The web app displays saved evidence in replay mode and does not run Foundry live.
   - The web app displays a "not tested" warning for C03, C04, C07, and V11 because they start with balances.
   - Blind mode is partial: it hides configuration names and help texts, but the dropdown still shows "(not tested)" for those four targets.
   - The page depends on the `report.json` field names; if they change, the page must change (Member 1 has agreed to announce changes).
   - One audit at a time (shared log file); no automated page tests in the repo.
9. **C08 classification contradiction:** `review_triage.md` labels the C08 finding "Real" (pre-bind mint to Carol holds tokens), whereas `Phase3.md` §6 treats it as legal setup and flags it as a false alarm.
10. **Licences:** Files derived from T-REX are GPL-3.0, and MaxBalanceModule is CC-BY-NC-4.0 (non-commercial licence only).

---

## 6. Price Check and API Spend

Prices in `pipeline/llm_config.json`: Haiku 5.5 at \$0.10/MTok in, \$0.50/MTok out; Sonnet 5.5 at \$2.00/MTok in, \$10.00/MTok out.  
**[TODO: verify against Anthropic's official pricing page and record your own check date here before final submission.]** (Team check was 2026-11-18).

Total API spend from `results/llm_ledger.jsonl` (262 live calls across 323 total records): **\$3.70** (Haiku \$0.31, Sonnet \$3.40; per-model figures are independently rounded).

---

## 7. Environment

No tool versions changed during Phase 5. Pinned environment: Python 3.11.9, Foundry 1.8.7, Halmos 0.3.3, Node.js 20.20.2. Full record in `docs/environment.md`. Protected files (`results/`, `results/llm_cache/`, `pipeline/`, `test/`) were not intended to be modified during Phase 5 report work.

> *Full technical detail is in `docs/Phase3.md` and `docs/Phase4.md`.*
