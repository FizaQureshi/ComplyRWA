# ComplyRWA — Benchmark Data Record

**Purpose:** Single reference for all detection, false-alarm, validity, cost, time, model and tool version numbers used in the Phase 5 evaluation report. All numbers come from saved results files; no pipeline runs were made.

---

## 0. How to Reproduce

```bash
cat results/variant_table.md           # hand-written test detection table
cat results/benchmark_threeway.md      # three-way comparison
cat results/benchmark_generated.md     # generated-test quality
cat results/review_compare.md          # all LLM review runs and costs
cat results/review_triage.md           # manual triage of false alarms

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

> After any replay run: `git checkout -- results`. Do not commit `results/`.

---

## 1. Tool and Model Versions

### 1.1 Development Tools

| Tool | Version | Check command |
|---|---|---|
| OS | Windows (native, no WSL) | — |
| Git | 2.37.3.windows.1 | `git --version` |
| Node.js | 20.20.2 (LTS) | `node -v` |
| npm | 10.8.2 | `npm -v` |
| Python | 3.11.9 | `python --version` (venv active) |
| Foundry (`forge`) | **1.8.7** (commit `985eeea`) | `forge --version` |
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
| ONCHAINID | `@onchain-id/solidity` 2.1.0 |

### 1.3 LLM Models

| Alias | Full model name | Input (USD/MTok) | Output (USD/MTok) | Price source |
|---|---|---|---|---|
| haiku | `claude-haiku-5-5` | \$0.10 | \$0.50 | Anthropic pricing page, team check 2026-11-18; **Member 3 to verify and record own date before final submission** |
| sonnet | `claude-sonnet-5-5` | \$2.00 | \$10.00 | Same |

> No temperature was set (`"temperature": null` in `pipeline/llm_config.json`).

### 1.4 Foundry Fuzz Settings

| Setting | Value |
|---|---|
| Fuzz seed | `0x436f6d706c79` |
| Invariant runs | 64 |
| Invariant depth | 40 |
| EVM version | london |

---

## 2. Test Configurations

### 2.1 Clean Configurations (from `docs/Phase3.md` §6)

| ID | What is different | Property suite | Scenario suite |
|---|---|---|---|
| C01 | Baseline | yes | yes |
| C02 | Topics 1 and 2 both required; issuers X and Y both trusted for both topics | yes | yes |
| C03 | Alice holds 600 and her 500-token move between her own wallets was rejected (D3 trap) | yes | **no** |
| C04 | An agent `forcedTransfer` put 100 tokens in Carol's wallet (country 408) (D1/J4 trap) | yes | **no** |
| C05 | Cap 500; countries 408 and 643 restricted | yes | yes |
| C06 | Bob's claim revoked, then re-issued with different data | yes | yes |
| C07 | Bob holds exactly 1000 (the cap) | yes | **no** |
| C08 | MaxBalanceModule bound to a token with existing holders (Carol 300, `a2` 100) using `batchPreSetModuleState` | yes | yes |

> **Why C03, C04, C07 have no scenario suite:** those configurations start with balances already set. Scenario tests assume an empty start and are skipped on them. Only property tests run.

> **C08 note (open question for Fiza):** `review_triage.md` labels the C08 finding (AI flagging the pre-bind mint to Carol) as "Real." `Phase3.md` §6 calls the same pre-bind mint a legal setup step and says flagging it is a false alarm. The repo contradicts itself — please confirm which label is correct.

### 2.2 Variant Configurations (from `docs/Phase3.md` §7.2 and §7.3)

**Wave 1 — configuration only:**

| ID | Rule | What was changed | Linked tests |
|---|---|---|---|
| V04 | K3 | `ctr.removeClaimTopic(KYC_TOPIC)` — required topics list is empty | G02a, G02b, G01a, G01b |
| V05 | J1 | Restrict country `410` instead of `408` | G03a, G03b, G08 |
| V07 | J3 | Country module removed with `removeModule` after setup | G07, G08 |
| V08 | J3 | Country module bound, but no country ever restricted | G08, G03a |
| V09 | H1 | `MaxBalanceModule` removed with `removeModule` | G04, G05a, G05b-prop |
| V11 | H3 | Bob already holds 800; `batchPreSetModuleState(compliance, [idB], [0])` sets tracked balance to 0, then module added. Property suite only | G05a, G05b-prop, G04 |
| V13 | H4 | `setMaxBalance(type(uint256).max)` — cap set to maximum | G04, G09, G10 |

**Wave 2 — code copies:**

| ID | Rule | File | What was changed | Linked tests |
|---|---|---|---|---|
| V01 | K1 | `IdentityRegistryV01.sol` | `isVerified` returns true when **any one** required topic satisfied (OR instead of AND) | G01a, G01b |
| V02 | K1 | `ClaimIssuerV02.sol` | `isClaimValid` always returns `true` | G01a, G01b |
| V03 | K2 | `ClaimIssuerV03.sol` | `isClaimValid` skips the `isClaimRevoked(sig) == false` check | G06c |
| V06 | J2 | `IdentityRegistryV06.sol` | `updateCountry` emits the event but never writes the new country | G07 |
| V10 | H2 | `MaxBalanceModuleV10.sol` | `_getIdentity` returns the wallet itself — every wallet gets its own cap instead of sharing one per identity | G09, G04 |
| V12 | H3 | `TokenV12.sol` | `forcedTransfer` no longer calls `_tokenCompliance.transferred(...)` | G05b-prop |

---

## 3. Hand-Written Tests — Detection and False Alarms

**Source:** `results/variant_table.md`

| Metric | Value |
|---|---|
| Variants caught by a linked test | **13 / 13** (100%) |
| False alarms on clean configs | **0 / 8** (0%) |
| LLM cost | \$0 |
| Foundry run time (compile + test) | 88 s |
| Forge suites | 38 (21 invariant + 17 scenario) |
| Total test cases | 208 (63 clean gold + 145 variant) |

Full pass/fail table: `results/variant_table.md`. Reproduced in `reports/evaluation_report.md` §2.

---

## 4. AI-Generated Tests — Validity, Detection, Cost, Time

**Source:** `results/benchmark_generated.md`, `results/benchmark_threeway.md`

### 4.1 Generation Parameters

| Parameter | Value |
|---|---|
| Rules used | 10 (H1 H2 H3 H4 J1 J2 J3 K1 K2 K3) |
| Tests per rule | 4 |
| Total tests per model | **40** |
| Haiku batches | d1 (K1 K3 J1 H1 H3), d2 (H1 retry), e1 (K2 J2 J3 H2 H4) — 11 calls |
| Sonnet batch | s1 (all 10 rules) — 10 calls |
| Validity filter | (1) compile; (2) fails on clean baseline C01?; (3) vacuousness check on C01 |

> **Note on batch counts:** Haiku's 88,231 input tokens are the sum of batches d1 + d2 + e1 (11 calls, 1 truncated). Sonnet's 80,278 tokens are from batch s1 (10 calls, 0 truncated). Batch b1 was an earlier trial and is not part of the benchmark.

### 4.2 Validity Results

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Tests generated | 40 | 40 |
| **KEEP** (valid + non-vacuous) | **32 (80%)** | **32 (80%)** |
| VACUOUS | 8 | 8 |
| REJECT (failed on clean) | 0 | 0 |

80% validity exceeds the 70% project target.

### 4.3 Detection

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Variants detected | **12 / 13** | **12 / 13** |
| Variant missed | **V11** | **V11** |
| False alarms on clean configs | **0 / 8** | **0 / 8** |

**Why V11 is missed by both models.** V11 starts with Bob already holding 800 tokens and sets the module's tracked balance to 0 via `batchPreSetModuleState`. Scenario tests assume an empty start and are skipped on V11 — only property tests run on it. The generated tests are scenario-style, so none run on V11, and nothing fails.

### 4.4 Cost and Time

| Metric | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| LLM calls (live) | 11 (1 truncated — `generator:H1:d1`) | 10 (0 truncated) |
| Input tokens | 88,231 | 80,278 |
| Output tokens | 52,594 | 22,454 |
| **Generation cost** | **\$0.0351** | **\$0.3851** |
| Cost per rule | \$0.0035 | \$0.0385 |
| Model time | 236 s | 163 s |
| Foundry run time | 171 s | 134 s |
| **Total wall time** | **407 s** | **297 s** |

### 4.5 Generator Batch Detail (Haiku, from `results/llm_ledger.jsonl`)

| Batch | Rules covered | Calls | Truncated | Input tokens | Output tokens | Cost |
|---|---|---|---|---|---|---|
| b1 (earlier trial) | K1 (earlier trial, not in benchmark) | 1 | 0 | 9,316 | 3,788 | \$0.0028 |
| d1 | K1 K3 J1 H1 H3 | 5 | 1 | 43,437 | 21,890 | \$0.0153 |
| d2 | H1 (retry) | 1 | 0 | 7,953 | 5,285 | \$0.0034 |
| e1 | K2 J2 J3 H2 H4 | 5 | 0 | 36,841 | 25,419 | \$0.0164 |
| **s1 (Sonnet)** | **all 10 rules** | **10** | **0** | **80,278** | **22,454** | **\$0.3851** |

---

## 5. LLM-Only Review — Detection, False Alarms, Cost, Time

**Source:** `results/review_compare.md`, `results/review_triage.md`

### 5.1 Run Index

| Run ID | Code view | Targets |
|---|---|---|
| r1 | Standard | 21 (all configs) |
| r1b | Standard (same input as r1, `--sample 1`) | 21 |
| r2 | Expanded — also shows `Token.init`, `setCompliance`, `setIdentityRegistry`, `bindToken`, `getTokenBound` | 21 |

One retry allowed per invalid JSON response. First-run numbers stay official.

### 5.2 Detection Rate

> **Always present first-answer and after-retry rates together.** Presenting only the post-retry rate overstates reliability. Haiku had zero format failures in r1 and r1b and is the more format-reliable model.

| Run | Model | First-answer detection | After one retry | Invalid JSON targets |
|---|---|---|---|---|
| r1 | Haiku 5.5 | **13/13** | — (no retry needed) | 0 |
| r1 | Sonnet 5.5 | **12/13** | **13/13** | 1 (V08) |
| r1b | Haiku 5.5 | **13/13** | — (no retry needed) | 0 |
| r1b | Sonnet 5.5 | **11/13** | **13/13** | 2 (V01, V05) |
| r2 | Haiku 5.5 | **13/13** | 13/13 | 1 (C02, truncated) |
| r2 | Sonnet 5.5 | **10/13** | **12/13** | 3 (V02, V09, V13) |

### 5.3 False Alarms on Clean Configurations (from `results/review_triage.md`)

**Per-run table:**

| Run | Stock gap on | Real (C08) | False alarm | Frozen | Adjusted | After triage |
|---|---|---|---|---|---|---|
| Haiku r1 | C01 C02 C03 C06 C07 | C08 | C04 | 7 of 8 | 2 of 8 | 1 of 8 |
| Haiku r1b | C01 C03 C05 C07 | none | C02 | 5 of 8 | 1 of 8 | 1 of 8 |
| Haiku r2 (+retry) | C02 C03 C04 | C08 | none | 4 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r1 (+retry) | none | C08 | none | 1 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r1b (+retry) | none | C08 | none | 1 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r2 (+retry) | C06 | none | none | 1 of 8 | 0 of 8 | 0 of 8 |

> Frozen = any HIGH/MEDIUM on a clean target. Adjusted = frozen, excluding stock-gap findings. After triage = true false alarms only.

**Triage label definitions:**

| Label | Meaning |
|---|---|
| Stock gap (S03/S04) | K2 finding about revoked claims revived via twin signature or v-byte trick. Real ONCHAINID dependency gap, proven by `StockGaps.t.sol` and `StockGapsVByte.t.sol` |
| Real (C08) | J1 on C08. Pre-bind mint to Carol (country 408). `review_triage.md` labels this "Real"; `Phase3.md` calls it a legal setup step and says flagging it is a false alarm. **Contradictory — ask Fiza.** Reported neutrally here. |
| False alarm (missing input) | J3 "setup never binds the token." `Token.init` calls `setCompliance`, which binds the token, but that code was not shown to the reviewer in r1/r1b. The error appeared in Haiku r1 (C04) and r1b (C02). Not present in r2 (expanded code view). |

**Run-to-run ranges (r1 and r1b, same input):**

| Model | Frozen | Adjusted | After triage |
|---|---|---|---|
| Haiku 5.5 | 5–7 of 8 (63–88%) | 1–2 of 8 (13–25%) | 1 of 8 (13%) in both runs |
| Sonnet 5.5 | 1 of 8 (13%) in both runs | 1 of 8 (13%) in both runs | 0 of 8 in both runs |

### 5.4 Cost and Time per Run (from `results/review_compare.md`)

| Run | Model | Cost (USD) | Time (s) |
|---|---|---|---|
| r1 | Haiku 5.5 | \$0.0765 | 797 |
| r1 | Sonnet 5.5 (first) | \$0.9197 | 237 |
| r1 +retry | Sonnet 5.5 | \$0.9599 | 244 |
| r1b | Haiku 5.5 | \$0.0766 | 401 |
| r1b | Sonnet 5.5 (first) | \$0.9122 | 217 |
| r1b +retry | Sonnet 5.5 | \$0.9973 | 236 |
| r2 | Haiku 5.5 (first) | \$0.0730 | 352 |
| r2 +retry | Haiku 5.5 | \$0.0778 | 380 |
| r2 | Sonnet 5.5 (first) | \$0.9642 | 232 |
| r2 +retry | Sonnet 5.5 | \$1.0937 | 257 |

Costs and times copied directly from `results/review_compare.md`.

---

## 6. Three-Way Comparison Summary

| Method | Model | First-answer detection | After retry | False alarms (after triage) | Cost (USD) |
|---|---|---|---|---|---|
| Hand-written Foundry tests | — | **13/13** | n/a | 0/8 | \$0 |
| AI-generated tests | Haiku 5.5 | 12/13 | n/a | 0/8 | \$0.0351 |
| AI-generated tests | Sonnet 5.5 | 12/13 | n/a | 0/8 | \$0.3851 |
| LLM-only review (r1) | Haiku 5.5 | **13/13** | n/a | 1/8 | \$0.0765 |
| LLM-only review (r1) | Sonnet 5.5 | **12/13** | **13/13** | 0/8 | \$0.9599 |
| LLM-only review (r1b) | Haiku 5.5 | **13/13** | n/a | 1/8 | \$0.0766 |
| LLM-only review (r1b) | Sonnet 5.5 | **11/13** | **13/13** | 0/8 | \$0.9973 |

---

## 7. Total API Spend

**Source:** `results/llm_ledger.jsonl` — 323 total records (262 live, 25 mock, 36 replay). Mock and replay calls record \$0 cost.

### 7.1 By Model — all records (incl. mock and replay, $0)

| Model | Live calls | Input tokens | Output tokens | Cost (USD) |
|---|---|---|---|---|
| `claude-haiku-5-5` | 212 | 2,509,940 | 665,796 | \$0.3082 |
| `claude-sonnet-5-5` | 111 | 1,633,960 | 151,681 | \$3.3958 |
| **Total** | **323** | **4,143,900** | **817,477** | **\$3.7039** |

> Note: Rounded summary figures ($0.31 for Haiku, $3.40 for Sonnet, $3.70 total) are independently rounded from the exact ledger values.

### 7.2 By Pipeline Stage

| Stage | Calls | Input tokens | Output tokens | Cost (USD) |
|---|---|---|---|---|
| Generator | 33 | 264,128 | 101,667 | \$0.4230 |
| Reviewer | 239 | 3,737,163 | 623,816 | \$3.2415 |
| Explainer | 49 | 142,567 | 91,964 | \$0.0394 |
| Smoke / other | 2 | 42 | 30 | \$0.0000 |
| **Total** | **323** | **4,143,900** | **817,477** | **\$3.7039** |

### 7.3 Generator Batch Detail (live calls, from `results/llm_ledger.jsonl`)

| Batch | Model | Calls | Truncated | Input tokens | Output tokens | Cost |
|---|---|---|---|---|---|---|
| b1 (earlier trial, not in benchmark) | Haiku 5.5 | 1 | 0 | 9,316 | 3,788 | \$0.0028 |
| d1 | Haiku 5.5 | 5 | 1 | 43,437 | 21,890 | \$0.0153 |
| d2 | Haiku 5.5 | 1 | 0 | 7,953 | 5,285 | \$0.0034 |
| e1 | Haiku 5.5 | 5 | 0 | 36,841 | 25,419 | \$0.0164 |
| s1 | Sonnet 5.5 | 10 | 0 | 80,278 | 22,454 | \$0.3851 |

---

## 8. Hardhat Baseline

| Metric | Value |
|---|---|
| Test suite | Hardhat (T-REX's own suite) |
| Command | `npm ci && npx hardhat compile && npx hardhat test` |
| Passing | **777** |
| Failing | **0** |

---

## 9. Reproducibility Notes

1. **Fuzz seed is fixed.** All fuzz-dependent cells reproduce on any machine with Foundry 1.8.7 and the same seed.
2. **LLM calls are cached.** Replay mode returns cached responses at zero cost.
3. **Mock mode was development only.** Mock calls record \$0 and are excluded from totals.
4. **Price check.** Prices in `pipeline/llm_config.json` were last verified by the team on 2026-11-18. Member 3 must re-verify against the Anthropic pricing page and record their own check date before final submission.
5. **Model pinning.** Anthropic does not expose a version-pinned endpoint. Reproducibility beyond cached results is not guaranteed if model weights change.
6. **`environment.md`** is the authoritative version record. Update it first if any tool version changes, then update Section 1 of this file.


