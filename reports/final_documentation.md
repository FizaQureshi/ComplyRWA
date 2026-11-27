# ComplyRWA — Final Project Documentation

**Pinned system:** T-REX 4.1.6 (commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`), Solidity 0.8.17, Foundry 1.8.7, Halmos 0.3.3

---

## Project Overview

**What ComplyRWA does:**  
ComplyRWA checks whether a tokenised real-world asset (a T-REX / ERC-3643 security token) actually follows the compliance rules its issuer wrote in plain English. Rules such as "only KYC-verified investors may receive tokens," "no restricted-country investor may hold tokens," and "no investor may hold more than 1000 tokens" are converted automatically into executable Foundry test code, run against the token's on-chain configuration, and the results returned as a plain-language audit report.

**Rule scope:** 13 rules across three categories:
- **KYC** (K1–K5): investor identity, claim topics, trusted issuers, claim expiry, revocation
- **Jurisdiction** (J1–J4): country restriction, module binding, known agent exception
- **Holding limit** (H1–H4): per-identity cap, identity-spanning cap, balance tracking, cap value

**Default audit set (5 rules, used in all demos):** K1, K3, J1, H1, H3.  
**Full benchmark set (10 rules):** K1, K2, K3, J1, J2, J3, H1, H2, H3, H4.

---

## Phase 0 — Environment Setup

**Goal:** Install and verify all tools; pin the target system.

**Status:** Complete. See `docs/environment.md`.

| Tool | Version | Check command |
|---|---|---|
| OS | Windows (native, no WSL) | — |
| Python | 3.11.9 | `python --version` |
| Node.js | 20.20.2 (LTS) | `node -v` |
| npm | 10.8.2 | `npm -v` |
| Foundry (`forge`) | 1.8.7 (commit `985eeea`) | `forge --version` |
| Halmos | 0.3.3 | `halmos --version` |
| Hardhat | 2.14.0 | `npx hardhat --version` |

**Baselines:**
- T-REX's own Hardhat suite: **777 passing, 0 failing** (~1 min).
- `forge build`: compiler successful with Solidity 0.8.17 (warnings from third-party code only).
- Halmos smoke test: `[PASS]`, 1 path, 0.02 s.

**Fuzz settings (fixed for all invariant runs):** Seed `0x436f6d706c79`, 64 runs, depth 40, EVM `london`.

---

## Phase 1 — Code Study

**Goal:** Trace the transfer path through T-REX contracts and map dependencies.

**Status:** Complete. See `docs/Phase1.md`.

### The spine: check, move, notify
1. **Check** (read-only): freeze checks → `IdentityRegistry.isVerified(_to)` → `ModularCompliance.canTransfer(from, to, amt)` → `IModule.moduleCheck(...)`.
2. **Move**: `_transfer(...)` updates balances in storage.
3. **Notify**: `ModularCompliance.transferred(...)` → `IModule.moduleTransferAction(...)` updates module counters.

### Two enforcement paths
- **KYC path:** IdentityRegistry + IdentityRegistryStorage + ClaimTopicsRegistry + TrustedIssuersRegistry + Identity (ONCHAINID) + ClaimIssuer (5 contracts).
- **Rule path:** ModularCompliance + compliance modules (CountryRestrictModule, MaxBalanceModule).

> **Key insight:** Jurisdiction (country) is checked by a compliance module, not in the KYC path. The country is stored in IdentityRegistryStorage, but only compliance modules read it via `investorCountry()`.

**Licence note:** `MaxBalanceModule` is released under CC-BY-NC-4.0 (non-commercial). Any commercial use requires a separate licence.

---

## Phase 2 — Policy Catalogue

**Goal:** Fix the 13 rules, testable forms, and accepted decisions.

**Status:** Complete. See `docs/Phase2.md`.

### Four accepted decisions
- **D1 (`forcedTransfer`):** Judged per module and per policy. Skips `canTransfer` (read side) but hits `transferred` (write side). MaxBalance catches it; CountryRestrict does not (J4 known exception).
- **D2 (sender KYC):** K5 (revoked sender can still send) is in scope as "violated by stock T-REX."
- **D3 (same-identity move):** Moving tokens between two wallets of one identity when above cap is expected to be rejected by stock `moduleCheck`. Documented as a known false-positive trap.
- **D4 (expired KYC):** K4 is in scope as a known stock gap of T-REX.

### 13 rules summary
- **KYC:** K1 (fully verified receivers), K2 (revocation blocks receiving), K3 (required topics list not empty), K4 (expired KYC rejected — stock gap S01), K5 (revoked sender cannot send — stock gap S02).
- **Jurisdiction:** J1 (no restricted-country receivers), J2 (country change respected), J3 (country module bound and configured), J4 (`forcedTransfer` labelled as known exception).
- **Holding limit:** H1 (cap not exceeded), H2 (cap is per identity), H3 (module balances match real balances), H4 (cap set sensibly).

### Stock gaps (S01–S04)
- **S01 (K4):** Expired claim accepted (`isClaimValid` has no expiry logic). Proven by `StockGaps.t.sol` and G11.
- **S02 (K5):** Revoked sender can still send (`transfer` checks only receiver). Proven by `StockGaps.t.sol` and G12.
- **S03 (K2):** Revoked claim revived via twin signature (`s' = n - s`, flipped `v`). Proven by `StockGaps.t.sol` and G14.
- **S04 (K2):** Revoked claim revived via v-byte trick (0/1 instead of 27/28). Proven by `StockGapsVByte.t.sol`.

---

## Phase 3 — Gold Standard and Test Harness

**Goal:** Build the answer key and test bench for measuring AI pipeline results.

**Status:** Complete. See `docs/Phase3.md`.

### Deliverables
- `test/ComplyFixture.sol`: Shared fixture with override hooks.
- 18 gold tests (G01a–G14): Hand-written Foundry tests covering all 13 rules.
- 8 clean configurations (C01–C08): Correct setups to measure false alarms.
- 13 seeded variants (V01–V13): Broken setups to measure detection.
- Results table: 13/13 caught (100%), 0/8 false alarms (0%), 88 s run time.

### Clean configurations (from `docs/Phase3.md` §6)

| ID | What is different | Property suite | Scenario suite |
|---|---|---|---|
| C01 | Baseline | yes | yes |
| C02 | Topics 1 and 2 both required. Issuers X and Y both trusted for both topics. Tests AND across topics, OR across issuers | yes | yes |
| C03 | Alice holds 600 and her 500-token move between her own wallets was rejected (D3 trap) | yes | **no** |
| C04 | An agent `forcedTransfer` put 100 tokens in Carol's wallet (country 408) (D1/J4 trap) | yes | **no** |
| C05 | Cap 500; countries 408 and 643 restricted. Tests read numbers from policy, not constants | yes | yes |
| C06 | Bob's claim revoked, then re-issued with different data | yes | yes |
| C07 | Bob holds exactly 1000 (the cap), reached by receiving exactly 100 | yes | **no** |
| C08 | `MaxBalanceModule` bound to a token with existing holders (Carol 300, `a2` 100) using `batchPreSetModuleState` | yes | yes |

> **Why C03, C04, C07 have no scenario suite:** Scenario tests assume an empty start state. These three configurations start with balances already set, so scenario tests are skipped and only the property suite runs.

> **C08 note (open question for Fiza):** `review_triage.md` labels the AI finding on C08 as "Real" because Carol holds tokens minted before compliance binding. `Phase3.md` §6 considers that a legal setup step and calls flagging it a false alarm. The repo has a contradiction here; it is documented neutrally.

### 13 seeded variants (from `docs/Phase3.md` §7.2 and §7.3)

**Wave 1 — configuration only:**

| ID | Rule | What was changed | Linked tests |
|---|---|---|---|
| V04 | K3 | `ctr.removeClaimTopic(KYC_TOPIC)`, so the required topics list is empty | G02a, G02b, G01a, G01b |
| V05 | J1 | Restrict country `410` instead of `408` | G03a, G03b, G08 |
| V07 | J3 | Country module removed with `removeModule` after setup | G07, G08 |
| V08 | J3 | Country module bound, but no country ever restricted | G08, G03a |
| V09 | H1 | `MaxBalanceModule` removed with `removeModule` | G04, G05a, G05b-prop |
| V11 | H3 | Bob already holds 800; `batchPreSetModuleState(compliance, [idB], [0])` sets tracked balance to 0, then module added. Property suite only | G05a, G05b-prop, G04 |
| V13 | H4 | `setMaxBalance(type(uint256).max)` — cap set to maximum | G04, G09, G10 |

**Wave 2 — code copies:**

| ID | Rule | File | What was changed | Linked tests |
|---|---|---|---|---|
| V01 | K1 | `IdentityRegistryV01.sol` | `isVerified` returns true when **any one** required topic is satisfied (OR instead of AND) | G01a, G01b |
| V02 | K1 | `ClaimIssuerV02.sol` | `isClaimValid` always returns `true` | G01a, G01b |
| V03 | K2 | `ClaimIssuerV03.sol` | `isClaimValid` skips the `isClaimRevoked(sig) == false` check | G06c |
| V06 | J2 | `IdentityRegistryV06.sol` | `updateCountry` emits the event but never writes the new country | G07 |
| V10 | H2 | `MaxBalanceModuleV10.sol` | `_getIdentity` returns the wallet itself, so every wallet gets its own cap | G09, G04 |
| V12 | H3 | `TokenV12.sol` | `forcedTransfer` no longer calls `_tokenCompliance.transferred(...)` | G05b-prop |

---

## Phase 4 — The AI Pipeline

**Goal:** Build the generator, validity filter, code slicer, test executor, and explainer.

**Status:** Complete (steps 4.0–4.8). See `docs/Phase4.md`.

### Pipeline steps
- 4.0: Importable Cfg contracts and manifest `pipeline/configs.json`.
- 4.1: Test executor with clean output tables.
- 4.2: Validity filter (outcome labels: KEEP, VACUOUS, REJECT).
- 4.3: Slicer (11% to 35% of full source, comments stripped).
- 4.4: LLM module (mock, replay, live modes, caching, ledger).
- 4.5: Generator (turns policy text into executable tests).
- 4.6: Explainer (reproducible trace to plain-English findings).
- 4.7: CLI demo (`pipeline/demo.py`).
- 4.8: LLM-only review baseline and three-way benchmark.

### Benchmark results — AI-generated tests
Given 10 policy rules (H1–H4, J1–J3, K1–K3), 4 tests per rule = 40 tests evaluated per model. Haiku input tokens come from batches d1, d2 and e1 (11 calls); Sonnet from batch s1 (10 calls).

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests evaluated | 40 | 40 |
| Valid and non-vacuous (KEEP) | **32 / 40 = 80%** | **32 / 40 = 80%** |
| Vacuous | 8 | 8 |
| Rejected | 0 | 0 |
| Bugs detected | **12 / 13** | **12 / 13** |
| Bug missed | **V11** | **V11** |
| False alarms on clean configs | **0 of 40 tests rejected on clean** | **0 of 40 tests rejected on clean** |
| Cost (USD) | **\$0.0351** | **\$0.3851** |
| Model time | 236 s | 163 s |
| Total time (incl. Foundry) | 407 s | 297 s |

> **Why V11 is missed by both models:** V11 starts with Bob already holding 800 tokens and sets the module's tracked balance to 0 via `batchPreSetModuleState`. Scenario tests assume an empty start and are skipped on V11; only property tests run on it. The generated tests are scenario-style, so none run on V11, and nothing fails.

### Benchmark results — LLM-only review

> **Reading guidance:** Always present first-answer and after-retry rates together. Sonnet had invalid JSON responses on first attempt; presenting only post-retry rates overstates reliability.

| Run | Model | First-answer detection | After one retry | True false alarms (after triage) | Cost (USD) |
|---|---|---|---|---|---|
| r1 | Haiku 5.5 | **13/13** | — | 1/8 (C04) | \$0.0765 |
| r1 | Sonnet 5.5 | **12/13** | **13/13** | 0/8 | \$0.9599 |
| r1b | Haiku 5.5 | **13/13** | — | 1/8 (C02) | \$0.0766 |
| r1b | Sonnet 5.5 | **11/13** | **13/13** | 0/8 | \$0.9973 |

- **Clean false alarms:** Haiku produced 1 true false alarm in both runs (J3 "token not bound" because `Token.init` was omitted from r1/r1b input; resolved in r2). Sonnet had 0 true false alarms after triage in both runs.
- **Stock gaps S03/S04:** Reported on 3–5 clean targets by Haiku in each run; once by Sonnet (C06 in r2).

### Three-way comparison summary

| Method | First-answer detection | After retry | False alarms (after triage) | Cost |
|---|---|---|---|---|
| Hand-written Foundry tests | **13/13** | n/a | 0/8 | \$0 |
| AI-generated tests (Haiku) | 12/13 | n/a | 0/8 | \$0.035 |
| AI-generated tests (Sonnet) | 12/13 | n/a | 0/8 | \$0.385 |
| LLM-only review — Haiku r1 | **13/13** | n/a | 1/8 | \$0.077 |
| LLM-only review — Sonnet r1 | **12/13** | **13/13** | 0/8 | \$0.960 |

---

## Phase 5 — Evaluation and Write-Up

**Goal:** Write evaluation report, benchmark data, independent evaluation, demo script, final docs.

### Step 5.1 — Web Interface (MVP)

**Status: COMPLETE.** Merged into `master` in two pull requests (merge commits `270d4b1`, 24 Nov 2026 and `f799745`, 25 Nov 2026). Files: `web/app.py`, `web/requirements.txt`, `web/README.md`, and `.gitignore` entry `web/.venv/`. Checked by hand on all 21 targets and the error case (V99) on Windows, Python 3.10.

**What was built:**

| Part | What it does |
|---|---|
| Target dropdown | 21 entries shown as ID and name (e.g. `V07 – Bug: Country rule removed`). C03, C04, C07 and V11 carry the suffix `(not tested)` |
| Policy table | The 5 fixed rules K1, K3, J1, H1 and H3, read-only |
| Run audit | A progress list with the five step names that `demo.py` prints |
| Result banner | One of: failed / not tested / problems found / no problems with notes / no findings |
| Rule status tab | Counts, the rule table (rule, policy, tests, failed, status, severity, note), grouped findings, INFO lines, cost line |
| Findings tab | The finding text, direct evidence, failing tests, the side-effect flag and the reproducible test |
| Full report tab and download | `report.md` shown on the page; download button named after the target (e.g. `report_V04.md`) |
| Error screen | Stage and message when the audit fails |
| Blind audit option | A checkbox (sidebar → Advanced) that hides what each configuration changes |

**How the page works:**

1. Picks a target from a fixed dropdown — free text is never sent to the command.
2. Runs `python pipeline/demo.py --target <config> --mode replay` from the repo root (always replay; live mode costs money).
3. Checks the exit code first. Exit 0 → `report.json` has `"status": "ok"`. Non-zero → error screen shows the stage and message from `report.json`.
4. Reads only `results/demo_<target>/report.json` and `report.md`.

**Fields read from `report.json`:**

| Field | Used for |
|---|---|
| `target`, `model`, `mode` | Caption under the banner |
| `rules.<ID>` (policy, tests_run, failed, status, severity) | Rule status table |
| `groups` | Grouped findings list |
| `info` | INFO boxes |
| `findings.<ID>` (severity, text, direct_evidence, failing_tests, reproducible_test) | Findings tab and note column |
| `cost` | Cost line |

> **Side-effect note:** `findings.<ID>.direct_evidence.direct == 0` means every failure of that rule follows from another rule's problem. The page writes "side effect, not a separate problem" in the note column.

> **Not-tested warning:** C03, C04, C07 and V11 have every rule at status `NOT_RUN` and `tests_run` = 0. The page shows a warning that this is not a clean result, keyed to these four names specifically.

> **Field-name dependency:** The page depends on the `report.json` field names. If they change, the page must change. Member 1 has agreed to announce any change.

**Limits of the web interface:**
1. Only the 5 rules K1, K3, J1, H1 and H3 can be audited. The command takes no rule list.
2. The page shows saved evidence from replay mode; it does not run Foundry live.
3. The user cannot choose a local ERC-3643 project — only the pinned T-REX 4.1.6.
4. C03, C04, C07 and V11 are not tested by the saved results.
5. Blind mode is partial: it hides configuration names and help texts, but the dropdown still shows `(not tested)` for the four targets above.
6. One audit at a time (shared log file).
7. Hand testing only — no automated page tests in the repo.

**Open items (not built, do not affect any result):** a table of all 21 configurations in one view; quick-access buttons for the demo targets; short in-page explanations for terms such as "side effect" and "severity."

**Steps 5.2–5.5** (benchmark write-up, independent evaluation, evaluation report, demo script) are owned by Member 3 and written up in the evaluation report, not in this file.

---

### Limitations
1. **Hand-written tests are the answer key:** They were written by the same author as the variants, so their 100% detection rate is not an independent head-to-head evaluation.
2. **Single pinned system:** Only T-REX 4.1.6 tested.
3. **Three rule categories only:** KYC, jurisdiction, holding limit.
4. **13 variants designed by one person:** Covers core rules, but not all real-world edge cases.
5. **Small clean-config set:** 8 configurations; one false alarm equals 12.5%.
6. **No run-to-run range for generated tests:** Each model generated the benchmark suites in a single official run.
7. **Reviewer sees target code:** Detection rates are an upper bound compared to a true blind audit.
8. **Web demo interface limits:** The 5 demo rules are fixed and read-only; the app displays saved evidence in replay mode and does not run Foundry live; and it displays a "not tested" warning for C03, C04, C07, and V11 because they start with balances.
9. **C08 classification contradiction:** `review_triage.md` labels the C08 finding "Real" (pre-bind mint to Carol holds tokens), whereas `Phase3.md` §6 treats it as legal setup and flags it as a false alarm.
10. **MaxBalanceModule is CC-BY-NC-4.0:** Non-commercial licence only.

---

## Demo Guide

**Run order (from `pipeline/DEMO.md`):** C01 → V09 → V04.

### Web app (recommended)

```bash
git pull
cd web
py -m venv .venv
# Activate: Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Pick target from dropdown and click **Run audit**. No Foundry or API key needed (replay mode).

> Note: C03, C04, C07 and V11 show a "not tested" warning because they start with balances, so scenario tests skip them.

### Command line

```bash
python pipeline/demo.py --target C01 --mode replay
# Then inspect results/demo_C01/report.md
```

**Agreed safe Git workflow:** Run `git checkout -- results` before `git add reports/`.  
*Important:* Only run that checkout command after checking `git status` and confirming you have no results changes you need to preserve. It discards local changes inside `results/`.

### Demo talking points
- **C01 (Clean):** Show policy table and all-passed status. Point out INFO line for agent forcedTransfer known exception.
- **V09 (Holding limit removed):** Show H1 and H3 failures. Point to reproduction steps and suggested fix. Note that generation cost was under 4 cents for the full 10-rule benchmark.
- **V04 (One cause, many symptoms):** Show failures across K1, K3 and H3. Highlight the H3 note: *"All failing H3 tests are side effects of the KYC failure above. No separate holding-limit problem is shown."* Report groups findings by rule category rather than claiming proven root cause.

---

## Repository Layout

```
ComplyRWA/
  docs/
    Phase1.md           Code study and dependency map
    Phase2.md           Policy catalogue (13 rules, decisions D1–D4)
    Phase3.md           Gold standard and test harness
    Phase4.md           AI pipeline (steps 4.0–4.8)
    environment.md      Tool versions, fuzz settings, reproducibility
  pipeline/
    demo.py             End-to-end demo (--mode replay)
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
    demo_*/report.md    Audit reports for demo targets
  reports/              ← Phase 5 deliverables (charvi-reports branch)
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