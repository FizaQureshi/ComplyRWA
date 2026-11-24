# ComplyRWA Phase 5 — Evaluation Report

**Author:** Member 3 (Charvi) · **Branch:** `charvi-reports` · **Date:** 2026-11-24  
**Pinned system:** T-REX 4.1.6 (`a09cfd3`), Solidity 0.8.17, Foundry 1.8.7, Halmos 0.3.3

---

## 1. What ComplyRWA Does

ComplyRWA checks whether a tokenised real-world asset (T-REX / ERC-3643) token actually follows the compliance rules its issuer wrote in plain English. The issuer types rules such as "only KYC-verified investors may receive tokens" or "no investor may hold more than 1 000 tokens." The pipeline converts those rules into executable Foundry test code, runs the tests against the token's on-chain configuration, and returns a plain-language report explaining every violation and how to fix it.

**What is new in Phase 5:** this document is the independent evaluation and write-up of Phases 3 and 4. No new pipeline runs are made; all numbers come from saved results files.

---

## 2. Benchmark Results

Three approaches were compared on 21 token configurations: 13 deliberately broken (V01–V13) and 8 correct (C01–C08). Full numbers are in `reports/benchmark_data.md`.

### Hand-written tests (baseline)
13/13 bugs caught · 0/8 false alarms · \$0 cost · 88 s total. These tests form the answer key.

### AI-generated tests
The pipeline was given 10 rules (H1–H4, J1–J3, K1–K3) and generated 4 tests per rule = 40 tests total per model. The 5-rule demo audits generate 20 tests; the 10-rule benchmark generates 40.

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| Valid and non-vacuous (KEEP) | **32 / 40 = 80%** | **32 / 40 = 80%** |
| Vacuous | 8 | 8 |
| Rejected (failed on clean config) | 0 | 0 |
| Bugs caught | **12 / 13** | **12 / 13** |
| False alarms on 8 clean configs | **0 / 8** | **0 / 8** |
| Generation cost | **\$0.035** | **\$0.385** |
| Model time | 236 s | 163 s |

80% of generated tests are valid and non-vacuous, exceeding the 70% project target. The cost per rule is \$0.0035 (Haiku) vs \$0.0385 (Sonnet) — roughly 11× more expensive for the same result. Haiku's tokens come from batches b1, d1, d2 and e1; Sonnet's from batch s1.

**Why V11 is missed by both models.** V11 starts with Bob already holding 800 tokens and sets the module's tracked balance to 0 via `batchPreSetModuleState`. Scenario tests assume an empty start and are skipped on V11 — only property tests run on it. The generated tests are scenario-style, so none run on V11, and nothing fails.

### LLM-only review

> **Always read first-answer and after-retry rates together.** Presenting only the post-retry number overstates reliability.

| Run | Model | First-answer detection | After one retry | True false alarms (after triage) | Cost |
|---|---|---|---|---|---|
| r1 (official) | Haiku 5.5 | **13/13** | — | 1/8 (C04) | \$0.077 |
| r1 (official) | Sonnet 5.5 | **12/13** | **13/13** | 0/8 | \$0.960 |
| r1b (repeat) | Haiku 5.5 | **13/13** | — | 1/8 (C02) | \$0.077 |
| r1b (repeat) | Sonnet 5.5 | **11/13** | **13/13** | 0/8 | \$0.997 |

Haiku had zero JSON format failures. Sonnet's misses before retry are all format failures, not genuine non-detections. Run-to-run false-alarm ranges: Haiku 5–7/8 frozen, 1/8 after triage (both runs); Sonnet 1/8 frozen, 0/8 after triage (both runs).

---

## 3. Three-Way Summary

| Method | First-answer detection | After retry | False alarms (after triage) | Cost |
|---|---|---|---|---|
| Hand-written Foundry tests | **13/13** | n/a | 0/8 | \$0 |
| AI-generated tests (Haiku) | 12/13 | n/a | 0/8 | \$0.035 |
| AI-generated tests (Sonnet) | 12/13 | n/a | 0/8 | \$0.385 |
| LLM-only review — Haiku r1 | **13/13** | n/a | 1/8 | \$0.077 |
| LLM-only review — Sonnet r1 | **12/13** | **13/13** | 0/8 | \$0.960 |

**Plain-language takeaway:** Hand-written tests are the gold standard. AI-generated tests (Haiku) achieve 92% detection at \$0.035 with no false alarms — competitive at a small fraction of human writing time. Sonnet costs 11× more for identical results on this benchmark. The LLM-only review reaches 13/13 but requires a human to triage false alarms; Haiku's raw false-alarm rate on clean configs is 63–88% before triage.

---

## 4. Independent Evaluation

Five reports were shown to an independent evaluator: C01 (clean), V04, V05, V09, V12. The evaluator rated each on understandability (Q2), evidence quality (Q3), report clarity (Q4) and actionability (Q5) on a 1–5 scale.

| Report | Q1 (what is wrong, in their words) | Q2 | Q3 | Q4 | Q5 | Notes |
|---|---|---|---|---|---|---|
| C01 | [evaluator answer] | — | — | — | — | |
| V04 | [evaluator answer] | /5 | /5 | /5 | /5 | |
| V05 | [evaluator answer] | /5 | /5 | /5 | /5 | |
| V09 | [evaluator answer] | /5 | /5 | /5 | /5 | |
| V12 | [evaluator answer] | /5 | /5 | /5 | /5 | |

**Evaluator:** [name, role, relationship to project — state if outsider or team fallback]  
Full questionnaire and results: `reports/evaluator_questionnaire.md`.

---

## 5. Limitations

1. **Single pinned system.** Only T-REX 4.1.6 tested.
2. **Three rule categories only.** KYC, jurisdiction, holding limit.
3. **One person designed the bugs.** 13 variants chosen by one author.
4. **Small clean-config set.** 8 configurations; one false alarm = 12.5%.
5. **AI results vary between runs.** Run-to-run ranges quoted where available (r1 and r1b).
6. **Reviewer sees its own code.** Detection rates are an upper bound for a real blind audit.
7. **Replay mode in demo.** All demo runs use cached answers; the live API path is not tested.
8. **MaxBalanceModule is CC-BY-NC-4.0.** Non-commercial only.

---

## 6. Price Check and API Spend

Prices in `pipeline/llm_config.json`: Haiku 5.5 at \$0.10/MTok in, \$0.50/MTok out; Sonnet 5.5 at \$2.00/MTok in, \$10.00/MTok out. **[TODO: verify against Anthropic pricing page and record your own check date here before final submission.]** The team's last check was 2026-11-18.

Total API spend (from `results/llm_ledger.jsonl`, 262 live calls across 323 total records): **\$3.70** (Haiku \$0.31, Sonnet \$3.40).

---

## 7. Environment

No tool versions changed during Phase 5. Full record: `docs/environment.md`. All saved results, `results/llm_cache`, pipeline code and test files were left unmodified.

> *Full technical detail is in `docs/Phase3.md` and `docs/Phase4.md`. Do not re-run the pipeline or modify saved results without coordinating with the project lead.*
