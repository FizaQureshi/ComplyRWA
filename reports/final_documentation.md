# ComplyRWA — Final Project Documentation

**Assembled by:** Member 3 (Charvi)  
**Branch:** `charvi-reports`  
**Date:** 2026-11-24  
**Purpose:** Single-document summary of all five phases for the project record. Full technical detail is in `docs/Phase1.md` through `docs/Phase4.md`. This document combines the key findings, decisions, results, and status of each phase so a new reader can understand the whole project without reading four separate files.

---

## Project Overview

**What ComplyRWA does:**  
ComplyRWA checks whether a tokenised real-world asset (a T-REX / ERC-3643 security token) actually follows the compliance rules its issuer wrote in plain English. Rules such as "only KYC-verified investors may receive tokens," "no restricted-country investor may hold tokens," and "no investor may hold more than 1 000 tokens" are converted automatically into executable Foundry test code, run against the token's on-chain configuration, and the results returned as a plain-language audit report.

**Pinned target:** T-REX 4.1.6 (commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`), Solidity 0.8.17, Foundry 1.8.7, Halmos 0.3.3.

**Rule scope:** 13 rules across three categories:
- **KYC** (K1–K5): investor identity, claim topics, trusted issuers, claim expiry, revocation
- **Jurisdiction** (J1–J4): country restriction, module binding, known agent exception
- **Holding limit** (H1–H4): per-identity cap, identity-spanning cap, balance tracking, cap value

**Default audit set (5 rules, used in all demos and benchmarks):** K1, K3, J1, H1, H3.

---

## Phase 0 — Environment Setup

**Goal:** Install and verify all tools; pin the target system.

**Status:** Complete.

| Tool | Version |
|---|---|
| OS | Windows (native, no WSL) |
| Python | 3.11.9 |
| Node.js | 20.20.2 (LTS) |
| Foundry (`forge`) | 1.8.7 (commit `985eeea`) |
| Halmos | 0.3.3 |
| Hardhat | 2.14.0 |

**Baseline verification:**
- T-REX's own Hardhat suite: **777 tests passing, 0 failing**.
- `forge build`: compiles with 0 errors (warnings are from T-REX sources, not modified).
- Halmos smoke test: `[PASS]`, 1 path, 0.02 s.

**Fuzz settings (fixed for the whole project):**

| Setting | Value |
|---|---|
| Seed | `0x436f6d706c79` |
| Invariant runs | 64 |
| Invariant depth | 40 |
| EVM version | london |

Full record: `docs/environment.md`.

---

## Phase 1 — Code Study

**Goal:** Trace the transfer path through T-REX and draw the dependency map.

**Status:** Complete. See `docs/Phase1.md`.

**Key finding — The spine: check, move, notify**

Every token action (transfer, mint, burn) follows three steps:

1. **Check** (read-only): freeze checks → `IdentityRegistry.isVerified(to)` → `ModularCompliance.canTransfer(from, to, amt)` → each module's `moduleCheck`.
2. **Move**: `_transfer()` updates `_balances`.
3. **Notify**: `ModularCompliance.transferred()` → each module's `moduleTransferAction` updates counters.

**Two enforcement paths:**

| Path | What it checks | Contracts |
|---|---|---|
| KYC path | Is the receiver an eligible investor? | IdentityRegistry, IdentityRegistryStorage, ClaimTopicsRegistry, TrustedIssuersRegistry, Identity (ONCHAINID), ClaimIssuer |
| Rule path | Does this transfer respect the compliance rules? | ModularCompliance + N modules (CountryRestrictModule, MaxBalanceModule) |

**Key insight:** jurisdiction (country) is enforced by a compliance module, **not** the KYC path. A broken country module passes KYC checks silently. This explains why V05–V08 (country bugs) and V01–V04 (KYC bugs) need different test strategies.

**MaxBalanceModule licence note:** `MaxBalanceModule` is released under CC-BY-NC-4.0 (non-commercial). Any commercial use of ComplyRWA that includes this module requires a separate licence.

---

## Phase 2 — Policy Catalogue

**Goal:** Define exactly which rules ComplyRWA checks, with testable forms and known exceptions.

**Status:** Complete. See `docs/Phase2.md`.

**Four key decisions (all accepted):**

| # | Decision | Resolution |
|---|---|---|
| D1 | Is `forcedTransfer` exempt from all checks? | Judged per module and per policy. Skips `canTransfer` (read) but hits `transferred` (write). MaxBalance catches it; CountryRestrict does not (J4 known exception). |
| D2 | Are sender-side KYC checks in scope? | K5 (revoked sender can still send) is in scope as "intentionally violated by stock." |
| D3 | Same-identity move (600 held, cap 1 000, move 500 between wallets): rejected or passes? | Expected = rejected. The auditor does not report it as a bug. Documented as a known false-positive trap. |
| D4 | Is K4 (expired KYC claim) a real finding? | Yes, in scope, but flagged as a stock gap of T-REX (not a code bug the issuer introduced). |

**13 rules in full:**

| ID | Category | Plain-English rule | Status on stock T-REX |
|---|---|---|---|
| K1 | KYC | Only investors with a valid KYC claim from a trusted issuer may receive tokens | Holds |
| K2 | KYC | A revoked claim cannot be used to receive tokens | Holds (but see S03/S04 stock gaps) |
| K3 | KYC | At least one KYC claim topic must be required | Holds |
| K4 | KYC | An expired KYC claim must not allow receiving | **Stock gap S01** — violated by stock |
| K5 | KYC | A sender whose claim was revoked cannot send | **Stock gap S02** — violated by stock |
| J1 | Jurisdiction | Investors registered in a restricted country may not receive tokens | Holds |
| J2 | Jurisdiction | After `updateCountry` to a restricted country, the investor cannot receive | Holds |
| J3 | Jurisdiction | The country restriction module must be bound | Holds |
| J4 | Jurisdiction | `forcedTransfer` to a restricted country succeeds (agent exception) | Known exception, not a bug |
| H1 | Holding limit | No investor may hold more than the maximum allowed tokens | Holds |
| H2 | Holding limit | Two wallets of one identity share one cap | Holds |
| H3 | Holding limit | The module's tracked balance must equal the real token balance | Holds |
| H4 | Holding limit | The cap equals the policy number | Holds |

**Stock gaps (not seeded, present in stock T-REX):**

| ID | Description | Proven by |
|---|---|---|
| S01 | Expired claim not rejected | `GoldSpecial.t.sol` G11 fails on stock |
| S02 | Revoked sender can still send | `GoldSpecial.t.sol` G12 fails on stock |
| S03 | Revoked claim revived via twin signature | `StockGaps.t.sol` |
| S04 | Revoked claim revived via v-byte (0 or 1) | `StockGapsVByte.t.sol` |

---

## Phase 3 — Gold Standard and Test Harness

**Goal:** Build the hand-written answer key and test fixture that Phase 4 is measured against.

**Status:** Complete. Detection 13/13, false alarms 0/8. See `docs/Phase3.md`.

### What was built

| Deliverable | Purpose |
|---|---|
| `test/ComplyFixture.sol` | Shared fixture with override hooks for all 21 configurations |
| Gold tests G01–G14 (`test/gold/`) | 18 hand-written test functions, the answer key |
| Clean configs C01–C08 (`test/clean/`, `test/configs/`) | 8 correct setups — measure false positives |
| Variant configs V01–V13 (`test/variants/`, `variants/`) | 13 seeded bugs — measure detection |
| `results/variant_table.md` | 21-config × 18-test detection table |

### Gold tests (18 test functions across 5 suites)

| Group | Rules | Type | Key assertion |
|---|---|---|---|
| G01a/b | K1 | Invariant | After any successful transfer/mint, receiver is KYC-verified |
| G02a/b | K3 | Scenario | Topics list is non-empty; unclaimed wallet cannot receive |
| G03a/b | J1 | Invariant | After any successful transfer/mint, receiver's country is not restricted |
| G04 | H1 | Invariant | Every identity's real balance ≤ policy cap |
| G05a/G05b-prop/G05b-rec | H3 | Invariant + Scenario | Tracked balance equals real balance |
| G06a/b/c | K2 | Scenario | Each revocation path blocks receiving |
| G07 | J2 | Scenario | `updateCountry` to restricted blocks future transfers |
| G08 | J3 | Scenario | Country module is bound and configured correctly |
| G09 | H2 | Scenario | Two wallets of one identity share one cap |
| G10 | H4 | Scenario | Cap equals the policy number |
| G11/G12/G14 | K4/K5/K2 | Special | Fail on stock (stock gaps S01/S02/S03) |
| G13 | J4 | Scenario | `forcedTransfer` to restricted country is a known exception |

### 13 seeded variants

| ID | Rule | Bug type | Catch method |
|---|---|---|---|
| V01 | K1, K2 | Config — wrong identity registry | G01a, G01b, G06c |
| V02 | K1, K2 | Config — wrong claim issuer | G01a, G01b, G06c |
| V03 | K2 | Code copy — revocation check bypassed | G06c |
| V04 | K1, K3 | Config — KYC topic removed | G01a, G01b, G02a, G02b, G06c |
| V05 | J1 | Config — restricted country changed | G03a, G03b, G07, G08 |
| V06 | J1 | Code copy — country check bypassed | G03a, G03b, G07, G08 |
| V07 | J1 | Config — country module unbound | G03a, G03b, G07, G08 |
| V08 | J1 | Config — country module unbound (alt) | G03a, G03b, G07, G08 |
| V09 | H1, H3 | Config — MaxBalanceModule unbound | G04, G05a, G05b, G09, G10 |
| V10 | H1, H3 | Code copy — wrong MaxBalance implementation | G04, G05a, G05b |
| V11 | H1 | Config — MaxBalanceModule unbound (Halmos path) | G04, G05b |
| V12 | H3 | Code copy — `forcedTransfer` skips tracker | G05a, G05b |
| V13 | H1 | Config — cap set to max uint256 | G04, G05b, G10 |

### Phase 3 results

| Metric | Result |
|---|---|
| Variants caught by a linked test | 13 / 13 (100%) |
| Clean configs with any false alarm | 0 / 8 (0%) |
| Forge run time (compile + test) | 88 s |

---

## Phase 4 — The AI Pipeline

**Goal:** Build the pipeline that converts policy text into tests, runs them, and explains failures.

**Status:** Complete (steps 4.0–4.8). See `docs/Phase4.md`.

### Pipeline steps

| Step | What it does | LLM? |
|---|---|---|
| 4.0 | Cfg contracts importable; manifest `pipeline/configs.json` | No |
| 4.1 | Executor — runs any test file on every config, produces table | No |
| 4.2 | Validity filter — rejects tests that don't compile, fail on clean, or are vacuous | No |
| 4.3 | Code slicer — extracts only the functions each rule needs | No |
| 4.4 | LLM interface and prompts (mock → replay → live) | Yes |
| 4.5 | Generator — policy text to candidate tests, then filter | Yes |
| 4.6 | Explainer — template + LLM for each failing test | Yes |
| 4.7 | End-to-end demo script (`pipeline/demo.py`) | Explainer only |
| 4.8 | LLM-only review baseline (three-way benchmark) | Yes |

### Key design decisions

- **Generator sees only the clean pinned code** — never the variants or gold tests.
- **Validity filter has three outcomes:** KEEP (valid, non-vacuous), VACUOUS (always passes), REJECT (fails on clean baseline).
- **Explainer is blind by default** — does not know the configuration label.
- **Invalid JSON gets one retry**, same rule for both models. First-run numbers stay official.
- **r1 is the official review run**; r1b is a repeat on the same input (noise measurement); r2 uses an expanded code view (sensitivity check, never mixed into headline).
- **Manual triage** (`results/review_triage.md`) is kept separate from official numbers and needs independent verification (Phase 5 task).

### Phase 4 benchmark results — AI-generated tests

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| Valid and non-vacuous (KEEP) | 32 / 40 = **80%** | 32 / 40 = **80%** |
| Vacuous | 8 | 8 |
| Rejected (failed on clean) | 0 | 0 |
| Bugs detected | **12 / 13** | **12 / 13** |
| Bug missed | V11 (both models) | V11 (both models) |
| False alarms on 8 clean configs | 0 / 8 | 0 / 8 |
| Generation cost | \$0.035 | \$0.385 |
| Model time | 236 s | 163 s |
| Total time (model + Foundry) | 407 s | 297 s |

> **Why V11 is missed:** V11 unbinds the MaxBalanceModule. Generated H1 tests read the cap through the module's getter — with the module unbound, the getter is never reached. G04 catches V11 because it reads the policy cap from the fixture, not the module.

### Phase 4 benchmark results — LLM-only review

> Detection rates are shown as first-answer / after one retry. Present both; post-retry alone overstates reliability.

| Run | Model | First-answer detection | After retry | True false alarms (after triage) | Cost |
|---|---|---|---|---|---|
| r1 (official) | Haiku 5.5 | **13/13** | — | 1 / 8 | \$0.077 |
| r1 (official) | Sonnet 5.5 | **12/13** | **13/13** | 0 / 8 | \$0.960 |
| r1b (repeat) | Haiku 5.5 | **13/13** | — | 1 / 8 | \$0.077 |
| r1b (repeat) | Sonnet 5.5 | **11/13** | **13/13** | 0 / 8 | \$0.997 |

**Run-to-run false alarm ranges (r1 and r1b, same input):**

| Model | Frozen range | Adjusted range | After triage |
|---|---|---|---|
| Haiku 5.5 | 5–7 of 8 (63–88%) | 1–2 of 8 (13–25%) | 1 of 8 (13%) in both runs |
| Sonnet 5.5 | 1 of 8 (13%) in both runs | 1 of 8 (13%) in both runs | 0 of 8 in both runs |

### Three-way comparison

| Method | Model | First-answer detection | After retry | False alarms (after triage) | Cost |
|---|---|---|---|---|---|
| Hand-written Foundry tests | — | **13/13** | n/a | 0/8 | \$0 |
| AI-generated tests | Haiku 5.5 | 12/13 | n/a | 0/8 | \$0.035 |
| AI-generated tests | Sonnet 5.5 | 12/13 | n/a | 0/8 | \$0.385 |
| LLM-only review (r1) | Haiku 5.5 | **13/13** | n/a | 1/8 | \$0.077 |
| LLM-only review (r1) | Sonnet 5.5 | **12/13** | **13/13** | 0/8 | \$0.960 |

### Total API spend (all phases combined)

Computed from `results/llm_ledger.jsonl` (323 records):

| Model | Calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|
| `claude-haiku-5-5` | 212 | 2 509 940 | 665 796 | \$0.31 |
| `claude-sonnet-5-5` | 111 | 1 633 960 | 151 681 | \$3.40 |
| **Total** | **323** | **4 143 900** | **817 477** | **\$3.70** |

---

## Phase 5 — Evaluation and Write-Up

**Goal:** Independent evaluation, evaluation report, benchmark data, demo script.

**Status:** In progress. Deliverables committed to `charvi-reports` branch.

### Deliverables

| File | Description | Status |
|---|---|---|
| `reports/evaluation_report.md` | Short evaluation report with results, methodology, limitations | ✅ Done |
| `reports/benchmark_data.md` | Full benchmark data: detection, false alarms, validity, cost, time, versions | ✅ Done |
| `reports/evaluator_questionnaire.md` | Questionnaire and results template for the independent evaluator | ✅ Done |
| `reports/demo_script.md` | Five-minute customer demo script (C01 → V09 → V04) | ✅ Done |
| `reports/final_documentation.md` | This file — combined phase notes | ✅ Done |
| Evaluator session | Show 5 reports to an independent person; record answers | ⬜ Pending |

### Independent evaluation

**Reports shown to evaluator (5):**

| Target | Pattern |
|---|---|
| C01 | Clean — nothing found |
| V04 | One cause, many symptoms (KYC topic removed) |
| V05 | Wrong-country restriction not enforced |
| V09 | Holding-limit module unbound |
| V12 | Hidden counter bug (forcedTransfer skips tracker) |

**Questionnaire (5 questions, 1–5 scale where stated):**

1. In your own words, what is wrong? (or: does the report say everything is fine?)
2. Do you understand what needs to be fixed and who should fix it? (1–5)
3. Is the evidence given convincing? (1–5)
4. Is anything confusing or unclear? (open text; also rated 1–5)
5. How actionable is this report for you as an issuer? (1–5)

Results table: see `reports/evaluator_questionnaire.md` (template ready, to be filled after session).

**Additional evaluator checks (time permitting):**
1. Verify triage labels in `results/review_triage.md` — currently only the project team has done this.
2. Check whether the 32 "KEEP" generated tests actually test what the rule text says.
3. Check whether the plain-language explanations in reports match what the failing tests show.

### Limitations (required by brief)

1. **Single pinned system.** Only T-REX 4.1.6 tested.
2. **Three rule categories only.** KYC, jurisdiction, holding limit. Other categories out of scope.
3. **One person designed the bugs.** 13 variants chosen by one author.
4. **Small clean set.** 8 configurations; one false alarm = 12.5%.
5. **AI results vary between runs.** Run-to-run ranges quoted where available.
6. **Reviewer sees its own code.** Detection rates are an upper bound for a real blind audit.
7. **Replay mode in demo.** All demo runs use cached answers; the live API path is not tested.
8. **MaxBalanceModule is CC-BY-NC-4.0.** Non-commercial only.

---

## Demo Instructions

**Run order (from `pipeline/DEMO.md`):** C01 → V09 → V04.

### Web app (recommended)

```bash
git pull
cd web
py -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Pick a target in the dropdown and press **Run audit**. No Foundry, no API key needed.

> C03, C04, C07, V11 show "not tested" — expected and documented.

### Command line

```bash
python pipeline/demo.py --target C01 --mode replay
# Then open results/demo_C01/report.md
```

After any run: `git checkout -- results` to discard ledger changes. Do not commit `results/`.

### Demo talking points

| Step | Target | Key point |
|---|---|---|
| 1 | C01 | "Nothing is wrong here, and the audit finds nothing." Show policy table and all-pass result. |
| 2 | V09 | "The holding-limit module was removed. The cap is gone." Show H1 and H3 findings, suggested fix. |
| 3 | V04 | "One KYC setting broken → three rules fail. The report groups K1 and K3 as the cause, H3 as a side effect." Show the side-effect flag. |

---

## Repository Layout (Phase 5 state)

```
ComplyRWA/
  docs/
    Phase1.md           Code study and dependency map
    Phase2.md           Policy catalogue (13 rules, decisions D1–D4)
    Phase3.md           Gold standard and test harness
    Phase4.md           AI pipeline (steps 4.0–4.8)
    environment.md      Tool versions, fuzz settings, reproducibility
  pipeline/
    demo.py             End-to-end demo (--mode replay for zero cost)
    DEMO.md             Demo run order
    llm_config.json     Model aliases and prices
    configs.json        Manifest of all 21 configurations
  results/
    variant_table.md    Gold-test detection table (do not modify)
    benchmark_threeway.md   Three-way comparison (do not modify)
    benchmark_generated.md  Generated-test quality detail (do not modify)
    review_compare.md   All LLM review runs (do not modify)
    review_triage.md    Manual triage of false alarms (do not modify)
    llm_ledger.jsonl    API spend record (do not commit changes)
    llm_cache/          Cached LLM responses for replay (do not modify)
    demo_*/report.md    Audit reports for the five demo targets
  reports/              ← Member 3 deliverables (charvi-reports branch)
    evaluation_report.md
    benchmark_data.md
    evaluator_questionnaire.md
    demo_script.md
    final_documentation.md
  test/                 Hand-written Foundry tests (do not modify)
  variants/             Code-copy variants (do not modify)
  web/                  Streamlit web app (merged into master)
```

---

*This document was assembled by Member 3 from `docs/Phase1.md`, `docs/Phase2.md`, `docs/Phase3.md`, `docs/Phase4.md`, and `docs/environment.md`. It does not replace those files — refer to them for the full record of decisions, problems, and intermediate results.*
