# ComplyRWA: Phase 4 Report (The AI Pipeline)

**Goal of Phase 4:** build the pipeline that turns an issuer's plain-English policy into executable Foundry tests, filters them, runs them on every configuration, and explains what failed.

**Status so far:** steps 4.0 to 4.6 are COMPLETE. Steps 4.7 and 4.8 are not started.

Pinned system: T-REX tag `4.1.6`, commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`, Solidity `0.8.17`, Foundry `1.8.7`, Halmos `0.3.3` (see `environment.md`).

> **How to read this file.** Section 1 is the step list. Section 2 covers step 4.0, section 3 step 4.1, section 4 step 4.2, section 5 step 4.3. Section 6 covers step 4.4, section 7 step 4.5, section 8 step 4.6. Section 9 records design decisions. Section 10 is the status and what comes next. Steps are added here as they close.

---

## 1. Phase 4 build order

Everything that needs no LLM came first. Steps 4.4 to 4.6 were built with Haiku 5.5 as the default model.

| Step | What | Needs LLM? | State |
|---|---|---|---|
| 4.0 | Prepare: importable Cfg contracts and a manifest | No | **Done** |
| 4.1 | Executor: run any test file on every configuration, same table | No | **Done** |
| 4.2 | Validity filter: reject tests that do not compile, fail on clean, or are vacuous | No | **Done** |
| 4.3 | Code slicer | No | **Done** |
| 4.4 | LLM interface and prompts (mock/replay first) | Yes | **Done** |
| 4.5 | Generator: policy text to candidate tests, then the filter | Yes | **Done** |
| 4.6 | Explainer (template fallback) | Yes | **Done** |
| 4.7 | End-to-end demo script | Yes | **Done** |
| 4.8 | LLM-only review baseline (for the three-way benchmark) | Yes | |

---

## 2. Step 4.0: Prepare

**Goal:** make the Phase 3 configurations reusable by a program, without changing any Phase 3 result.

**Status: COMPLETE.** Commit `c9763d9`.

### 2.1 Why it was needed

In Phase 3 each configuration (C01 to C08, V01 to V13) was a small `Cfg` contract inside a test file, glued by hand to the gold tests. Phase 4 must run **new tests** on **every** configuration automatically, so a program needs to know which configurations exist, what each one changes, and which gold suites exist for it.

### 2.2 What was done

| # | File | Action |
|---|---|---|
| 1 | `test/configs/CleanCfgs.sol` | New. `Cfg01` to `Cfg08` |
| 2 | `test/configs/VariantCfgs.sol` | New. `CfgV01` to `CfgV13` |
| 3 | `test/clean/CleanConfigs.t.sol` | Replaced. Imports the Cfg contracts, only combines them with the gold suites |
| 4 | `test/variants/Wave1.t.sol` | Replaced. V04, V05, V07, V08, V09, V11, V13 |
| 5 | `test/variants/Wave2.t.sol` | Replaced. V01, V02, V03, V06, V10, V12 |
| 6 | `pipeline/configs.json` | New. The manifest (21 entries) |
| 7 | `pipeline/check_manifest.py` | New. Checks the manifest against the Solidity text |

Example of the glue that remains in a test file (V05):

```solidity
contract V05_Invariants is GoldInvariantsTest, CfgV05 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV05) { CfgV05._configureModules(); }
}
```

Two facts about this glue matter later: every hook the `Cfg` overrides must be re-stated with `override(ComplyFixture, <Cfg>)`, and an **invariants** suite also re-states `setUp` because `GoldInvariantsTest` declares its own.

### 2.3 The manifest (`pipeline/configs.json`)

Each entry holds: `id`, `kind` (clean or variant), `type` (variants: C code copy or G configuration only), `cfg_contract`, `cfg_file`, `rule`, `description`, `hooks` (name, params, args, returns), `linked_tests` (variants) and `gold_suites` (invariants and/or scenarios, with contract name and file). The top-level `columns` list gives the 18 table columns in order.

Hooks per configuration:

| Config | Hooks overridden |
|---|---|
| C01 | none |
| C02 | `_deployClaimIssuer`, `_registerInvestors` |
| C03, C04, C07 | `_afterSetUp` |
| C05 | `_configure` |
| C06 | `_registerInvestors` |
| C08 | `_addModules` |
| V01 | `_newIdentityRegistry`, `_deployClaimIssuer`, `_registerInvestors` |
| V02 | `_newClaimIssuer(address admin)`, `_registerInvestors` |
| V03 | `_newClaimIssuer(address admin)` |
| V04 | `_deployClaimIssuer` |
| V05, V07, V08, V09, V13 | `_configureModules` |
| V06 | `_newIdentityRegistry` |
| V10 | `_maxBalanceImpl` |
| V11 | `_addModules` |
| V12 | `_newToken` |

### 2.4 The "38 gold suites"

It counts combined test contracts, not gold tests.

| Group | Configurations | Suites |
|---|---|---|
| Clean, invariants and scenarios | C01, C02, C05, C06, C08 | 10 |
| Clean, invariants only | C03, C04, C07 | 3 |
| Variants, invariants and scenarios | V01 to V10, V12, V13 | 24 |
| Variants, invariants only | V11 | 1 |
| **Total** | 21 configurations | **38** |

"Invariants only" means the start state already has balances, so scenario tests (which assume an empty start) are not run there.

### 2.5 Proof

| Check | Result |
|---|---|
| Clean log | 16 suites, 79 passed, 0 failed |
| Special log | 3 failed (G11, G12, G14, stock gaps) |
| Variants log | 25 suites, 145 total, 109 passed, 36 failed |
| `make_table.py` | 13 caught, 0 not caught, 100%; 8 clean, 0 false positives |
| `git diff` on `variant_table.md` and `variant_table.csv` | No output (identical to Phase 3) |
| `check_manifest.py` | `MANIFEST OK: 8 clean + 13 variants, 38 gold suites, all hooks match the code` |

### 2.6 Limits

The manifest check is text-only (the forge runs are the real proof). The manifest repeats information that also lives in the Solidity files, so `check_manifest.py` must be re-run if a `Cfg` changes.

---

## 3. Step 4.1: Executor

**Goal:** run any test contract on every configuration and write the same table as `make_table.py`.

**Status: COMPLETE.** Commit `35ad477`. File: `pipeline/executor.py`.

### 3.1 How it works

1. It reads the test contract and decides its **kind**: a contract with `invariant_` functions is an *invariants* suite, any other is a *scenarios* suite. It also notes whether the contract declares its own `setUp`.
2. For each configuration whose manifest entry lists that kind under `gold_suites`, it writes a wrapper contract into `test/generated/Wrappers.t.sol`:

   ```solidity
   contract Gen_<Test>_<ConfigID> is <Test>, <CfgContract> {
       function setUp() public override(<Test>, ComplyFixture) { <Test>.setUp(); }   // only if the test declares setUp
       function <hook>(<params>) internal override(ComplyFixture, <CfgContract>) [returns (<type>)] { [return] <CfgContract>.<hook>(<args>); }
   }
   ```
   The hook lines come from the manifest, so the generated text matches the hand-written Wave 1 and Wave 2 lines.
3. It deletes `cache/invariant` (stale fuzz failures, Phase 3 section 11.3), then runs `forge test --match-path "test/generated/*"` with the settings in `foundry.toml` (same fuzz seed).
4. It feeds the log to `make_table.py`, so parsing and verdicts are the Phase 3 ones. Only the mapping from wrapper name to configuration id is new.
5. It **deletes the wrappers** afterwards (unless `--keep`), so a plain `forge test` still gives the Phase 3 counts.
6. It writes `forge.log`, `table.csv`, `table.md` and `run_info.json` (wrapper count and seconds) to the output folder.

If forge cannot compile, the executor stops with exit code 2 and prints the last 40 lines. A test contract that overrides fixture hooks, or is not found, makes it stop with an error before running anything.

Command:

```
python pipeline/executor.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/exec_gold
```

### 3.2 Proof: the executor reproduces Phase 3

The gold tests were run through the **generated** wrappers instead of the hand-written ones.

| Check | Expected | Observed |
|---|---|---|
| Wrappers generated | 38 (21 invariants + 17 scenarios) | 38 |
| `diff results/exec_gold/table.csv results/variant_table.csv` | no output | No output (byte-identical) |
| Summary | 13 caught, 0 not caught; 8 clean, 0 false positives | Same |
| Forge totals | 38 suites, 172 passed, 36 failed, 208 total | Same |
| `test/generated` after the run | empty | Empty |
| Plain clean run afterwards | 79 passed | 79 passed |

The 208 is the 63 clean gold tests plus the 145 variant tests. The 63 is the 79 clean tests minus 16 non-gold ones (Smoke 1, StockGaps 4, C01 baseline 11).

### 3.3 Time (baseline for the benchmark criterion)

| Measure | Value |
|---|---|
| Forge run including compile | 87.7 s |
| Forge test run alone | 33.2 s (198.7 s CPU) |

### 3.4 Observations

1. **The forge log format** (from `results/exec_gold/forge.log`):
   - A scenario test prints `[PASS] test_X() (gas: N)` or `[FAIL: reason] test_X() (gas: N)`.
   - An invariants suite prints a header `<Wrapper> invariants:` followed by one line per invariant: `[PASS] invariant_X` or `[FAIL: reason] invariant_X`.
   - A failing invariant also prints a `[Sequence]` block with the shrunk call sequence (handler function, calldata, arguments). Step 4.6 (the explainer) can use this as the reproducible transaction sequence.
   - Failing invariant sequences are saved to `cache/invariant/failures`, which is why the executor deletes that folder before each run.
2. **Fuzz-dependent cells reproduced exactly.** Because the fuzz seed is fixed in `foundry.toml` and does not depend on the contract name, even the fuzz-dependent cells (Phase 3 section 11.2) came out identical.
3. **Cosmetic message.** `make_table.py` prints "Wrote results/variant_table.csv ..." but the executor moves those files into the output folder. The real files are `table.csv` and `table.md` there.
4. **Compile errors are all-or-nothing in one run.** One broken wrapper stops the whole forge run. Step 4.2 handles this by re-running candidates one at a time.

### 3.5 Limits

1. The table (`make_table.py`) only knows test names of the form `test_G01a_...` or `invariant_G01a_...`. Step 4.2 uses its own parser and does not have this limit.
2. A test contract must not override fixture hooks (names starting with `_`) and must define `setUp` itself or inherit it from `ComplyFixture`.
3. Candidate test files must live **outside** `test/` (for example `candidates/<batch>/`), because forge compiles everything under `test/` on every run, and one broken candidate there would break all Phase 3 commands. Wrappers in `test/generated/` are temporary and the folder is cleared on every run.

---

## 4. Step 4.2: Validity filter

**Goal:** decide which candidate tests are worth keeping, using only running code (no LLM).

**Status: COMPLETE.** Commit: `bc193dd`. Files: `pipeline/validity_filter.py`, `candidates/bad/BadTests.sol`, `candidates/bad/BadCompile.sol`.

### 4.1 The three outcomes

Every test function in a candidate contract gets one outcome:

| Outcome | Rule | Meaning |
|---|---|---|
| REJECT | The contract does not compile, **or** the test fails on any clean configuration, **or** it produced no result | The test is not valid: a correct test must pass on correct setups |
| VACUOUS | Passes on every clean configuration and on **every variant it ran on** | Valid, but it never detects any seeded bug. This is "unproven", not necessarily wrong: the rule it guards may not be broken by any of the 13 variants |
| KEEP | Passes on all clean configurations and fails on at least one variant | Valid and non-vacuous |

The project criterion "at least 70% valid and non-vacuous" is measured as **KEEP divided by tests judged**. "Valid (not rejected)" is reported next to it.

Two **notes** are recorded next to the outcome and do not change it:
- `no visible assertion`: no `assert*`, `require`, `expectRevert` or `revert` in the test body or in a helper function of the same contract. An assertion inside another contract (for example a handler) is not visible from the test source, so this cannot decide the outcome.
- `ran on x/8 clean, y/13 variants`: scenario tests skip configurations whose start state has balances (C03, C04, C07, V11).

### 4.2 How it works

1. It runs all candidates together through `pipeline/executor.py` (step 4.1), one output folder `joint/`.
2. If that run cannot compile, it runs **each candidate alone**. A candidate that fails to compile is rejected as a whole ("does not compile"); the others keep their results.
3. It reads each `forge.log` with its own parser. The formats were taken from the real log:
   - run header: `Ran N test(s) for <path>:<Wrapper>`, or `Encountered N failing test(s) in <path>:<Wrapper>`
   - invariants header: `<Wrapper> invariants:` or `<Wrapper> invariants (runs: ...)`
   - result line: `[PASS] name` or `[FAIL: reason] name`, where name starts with `test` or `invariant`
   - a wrapper is named `Gen_<Test>_<ConfigID>`, which gives the test contract and the configuration. FAIL always wins when a result appears twice (forge repeats failures in a summary).
4. It classifies each test and writes `report.md`, `report.csv`, `report.json` and `matrix.csv` (test by configuration, P / F / -).

It does not need test names of the form `G01a`: the real test name is the key.

Candidate files must live outside `test/` (here `candidates/<batch>/`), because forge compiles everything under `test/` on every run. They import the fixture as `"../../test/ComplyFixture.sol"`.

### 4.3 Proof A: the gold tests

```
python pipeline/validity_filter.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/filter_gold
```

| Measure | Expected (from the Phase 3 table) | Observed |
|---|---|---|
| Tests judged | 18 | 18 |
| KEEP | 16 | 16 |
| VACUOUS | 2 (G06a, G13) | 2 (`test_G06a_deleteIdentityBlocksReceiving`, `test_G13_forcedTransferToRestrictedCountryIsKnownException`) |
| REJECT | 0 | 0 |
| Valid and non-vacuous | | 16 of 18 = 89% |
| Time | | executor 85.7 s (with compile), whole filter 86.2 s |

Why the two VACUOUS results are expected: G13 is the known-exception test (it passes on every configuration by design), and G06a checks that `deleteIdentity` blocks receiving, which none of the 13 variants breaks. Both pass on all 12 variants they ran on (scenario tests do not run on V11). **The human gold set therefore scores 89% on the Phase 4 measure. This is the reference for the AI-generated tests.**

### 4.4 Proof B: deliberately bad tests

```
python pipeline/validity_filter.py --tests candidates/bad/BadTests.sol:BadTests candidates/bad/BadCompile.sol:BadCompile --out results/filter_bad
```

| Test | Expected | Observed |
|---|---|---|
| `test_BAD1_failsEverywhere` (`assertTrue(false)`) | REJECT, fails on clean | REJECT, fails on C01 C02 C05 C06 C08 |
| `test_BAD2_noAssertion` | VACUOUS | VACUOUS |
| `test_BAD3_alwaysTrue` (`assertTrue(true)`) | VACUOUS | VACUOUS |
| `BadCompile` (calls a missing function) | REJECT, does not compile | REJECT, does not compile |

The joint run failed with exit 2, so the fallback ran each candidate alone, as designed. Time: executor 28.4 s, whole filter 33.7 s. `git status` showed no change under `test/`.

### 4.5 Observations

1. **The filter separates "bad test" from "unproven test".** Without the VACUOUS class, G06a and G13 would be counted as failures of the human gold set.
2. **Fails on clean uses 5 of 8 clean configurations for scenario tests** (C03, C04, C07 start with balances), and invariants use all 8. Scenario evidence on clean setups is therefore a little weaker.
3. **Results depend on the fixed fuzz seed** in `foundry.toml` for invariant tests (Phase 3 limit 2). A generated invariant might kill a variant under one seed and not another.

### 4.6 Limits

1. VACUOUS depends on the 13 chosen variants. A correct test for a rule that is not seeded cannot be told apart from a useless one.
2. "No visible assertion" only sees the test contract's own source.
3. A candidate contract must compile on its own, must not override fixture hooks, and must define `setUp` itself or inherit it from `ComplyFixture` (executor limits).
4. The filter does not judge whether a test matches the issuer's rule text. A test can be KEEP and still check the wrong thing. The independent evaluator (Phase 5) covers this.

---

## 5. Step 4.3: Code slicer

**Goal:** cut the pinned contracts down to the functions each rule needs, with comments removed, so that an LLM gets a small and honest view of the code.

**Status: COMPLETE.** Commit: `ff80f4a`. Files: `pipeline/slicer.py`, `pipeline/slice_map.json`, `pipeline/fixture_facts.md`, and the generated `pipeline/slices/`.

### 5.1 Why

- A full source file is large (the files behind one rule are about 6,000 to 20,000 approximate tokens). Most of it is irrelevant to a single rule.
- Phase 1 found copy-pasted NatSpec in `MaxBalanceModule` (the `moduleCheck` comment is the `CountryAllowModule` text, and the action functions say "no action required"). An LLM reads comments, so the slicer **removes all comments** and the model sees code only.

### 5.2 How it works

1. `pipeline/slice_map.json` holds **26 units** (named groups of functions in one contract: file, contract, function names) and the **13 rules**, each a list of units in transfer-path order (Token, registries, ONCHAINID, compliance, modules). Rule titles are the Phase 2 titles. `default_audit` lists K1, K3, J1, H1, H3.
2. For each rule the units are merged per contract. The slicer then adds, **from the same contract and automatically**:
   - helper functions and modifiers that an included function calls (unqualified calls only) or uses,
   - `error` declarations that an included function mentions,
   - the contract's own state variable declarations.
3. Comments are removed by a small scanner that respects string literals. Function bodies are kept exactly as they are.
4. `--check` verifies that every name in the map exists in the pinned source. `--all` writes one slice per rule, `_fixture_api.txt`, `index.json` and `sizes.md`, and checks that no comment marker remains.
5. `_fixture_api.txt` is `test/ComplyFixture.sol` without function bodies: the members, helper signatures, hooks and the fixture's own comments (they are accurate).
6. `pipeline/fixture_facts.md` is a short written summary of facts that live **inside** fixture function bodies and so are lost in the summary: who is registered, who holds a KYC claim, countries, who may call what, revert messages. It was written from the fixture source.

Commands:

```
python pipeline/slicer.py --check
python pipeline/slicer.py --all
python pipeline/slicer.py --rule K1
```

### 5.3 Results (on the project owner's machine)

| Check | Result |
|---|---|
| `--check` | `SLICE MAP OK: 26 units, 13 rules` |
| Comment check | OK, no comments in any slice |
| Independent check | Identical sizes in a separate run against a fresh clone of the pinned tag (`a09cfd3`) and ONCHAINID 2.1.0 |
| Average slice | 2,227 approximate tokens (full source files: 12,304) |
| Fixture summary | 1,119 approximate tokens |

Approximate tokens are characters divided by 4, a rough guide only.

| Rule | Files | Slice ~tokens | Full files ~tokens | Slice is |
|---|---|---|---|---|
| K1 | 7 | 3,105 | 20,151 | 15% |
| K2 | 5 | 3,534 | 16,668 | 21% |
| K3 | 3 | 2,034 | 10,036 | 20% |
| K4 | 4 | 2,795 | 14,154 | 20% |
| K5 | 2 | 1,305 | 8,698 | 15% |
| J1 | 5 | 2,306 | 16,758 | 14% |
| J2 | 4 | 1,707 | 13,895 | 12% |
| J3 | 2 | 1,460 | 5,915 | 25% |
| J4 | 3 | 1,334 | 11,602 | 11% |
| H1 | 3 | 2,307 | 11,906 | 19% |
| H2 | 3 | 1,804 | 12,054 | 15% |
| H3 | 3 | 4,110 | 11,906 | 35% |
| H4 | 2 | 1,162 | 6,219 | 19% |

A slice is 11% to 35% of the full source files. H3 is the largest because it needs the preset functions. A prompt for one rule is roughly the slice, the fixture summary, the fixture facts and the instructions, which is about 4,000 to 6,000 input tokens (an estimate, to be measured in step 4.4).

### 5.4 Observations

1. **ONCHAINID version.** The line numbers of `isClaimValid`, `getRecoveredAddress`, `addClaim` and `getClaim` on the owner's machine match ONCHAINID 2.1.0 exactly. This supports the open item from Phase 3 (limit 7) that the installed version should be recorded in `environment.md`.
2. **The generator sees the clean pinned code only.** It never sees the variants (`variants/`) or the gold tests. This stops the answer key from leaking into the generated tests.
3. **Slices keep the real revert strings** (for example `"Transfer not possible"`), which step 4.6 needs because that message is the same for KYC and rule failures.
4. **A first version of the comment check was wrong.** It flagged the slicer's own `// =====` file marker lines. It was fixed before the final run, and the slices themselves never contained comments.

### 5.5 Limits

1. State that a contract inherits from a separate storage contract (`TokenStorage`, `IRStorage`, `CTRStorage`, `MCStorage`) is not in the slice, because the slicer reads only the contract named in the map. Tests use public functions and the fixture, so this should not matter. If the generator is confused by it, those contracts can be added as units.
2. The map is curated by hand. If a rule changes, the map must be updated (`--check` catches wrong names but not missing functions).
3. Helper inclusion follows unqualified calls by name. It can include an extra helper or miss a call written as `this.f()` or `super.f()`.
4. The slices describe stock code. They are not made for the variant copies.

---

## 6. Step 4.4: LLM interface and prompts

**Goal:** one place where the pipeline talks to an LLM, with a spending cap, saved answers and a cost record, plus the prompts.

**Status: COMPLETE.** Commit `68b6df9` (together with the first K1 run). Files: `pipeline/llm.py`, `pipeline/llm_config.json`, `pipeline/prompts.py`, `pipeline/prompts/generator.md`, `pipeline/prompts/explainer.md`, `pipeline/mock/`, `pipeline/prompt_size.py`, `pipeline/test_llm_interface.py`.

### 6.1 How it works

| Part | What it does |
|---|---|
| Modes | **mock** (no network, no cost, answer from `pipeline/mock/<task>.txt`), **replay** (answers only from the saved cache, a miss is an error), **live** (cache first, a miss calls the API and saves the answer) |
| Cache | `results/llm_cache/<hash>.json`, one file per answer (text, tokens, cost, stop reason). The key covers model, prompts, token limit and temperature. These files are committed, so the benchmark can be replayed for free |
| Ledger | `results/llm_ledger.jsonl`, one line per call: tag, model, tokens, `cost_usd` (money paid), `original_cost_usd` (cost when the answer was first made, used for the benchmark), stop reason, seconds |
| Budget guard | Before every live call the worst-case cost is checked against `session_cap_usd` (15) and the hard stop (115). Worst case uses input tokens x 1.7 and the full output limit |
| Key | Read only from the environment variable `ANTHROPIC_API_KEY`. Never stored in a file. `grep -rl "sk-ant" pipeline results candidates` found nothing. A key that was shown once in a chat during setup was revoked and replaced |
| Prompts | `llm.render(task, **values)` fills `pipeline/prompts/<task>.md` (system part, a `---USER---` line, user part). A missing `{{NAME}}` is an error, so a typo is never sent to the model |
| Config | `pipeline/llm_config.json`: aliases `haiku` = `claude-haiku-5-5` and `sonnet` = `claude-sonnet-5-5`, prices, `temperature`, budget (planned 100, soft limit 80, hard stop 115, absolute max 120, session cap 15) |

Prices (USD per million tokens): Haiku 5.5 is 0.10 in and 0.50 out. Sonnet 5.5 is 2.00 in and 10.00 out. These come from public pages and one confirmation on Anthropic's pricing page. Check them again before the final report.

### 6.2 What happened

1. **Environment.** The `python` in Git Bash was MSYS2's and had no `pip`. A separate venv was built: `~/.venvs/complyrwa` (Python 3.11.9, `anthropic` 2.8.0). Use `PY=~/.venvs/complyrwa/Scripts/python.exe`.
2. **Two designs were merged.** An earlier design (2026-11-18: `llm_config.json`, `prompts/`, `mock/`, `prompt_size.py`) and a second one (2026-11-20) overlapped. The earlier prompt design was kept because its rules avoid false alarms on clean configurations (use `CAP` and `RESTRICTED`, never assume zero balances). A first version of the prompt told the model to use the numbers 408 and 1000, which would have failed on clean configuration C05 (cap 500).
3. **Live smoke test.** Haiku answered "ok" for $0.000005. Haiku 5.5 **rejects the temperature setting**, so `temperature` is `null` in the config. Because of this, a repeated call can give a different answer. The saved cache makes `--mode replay` exact.
4. **Token estimate.** Characters / 4 under-counts. K1's real input was 9,316 tokens against an estimate of about 6,000, so the worst-case factor was raised from 1.3 to 1.7.
5. **Prompt size.** `prompt_size.py` estimates 4,083 to 7,036 tokens per rule (average about 5,150). Real input is about 1.5 times higher.

### 6.3 Proof

`test_llm_interface.py`: 8 offline checks pass (cost math, aliases, template rendering, mock file choice, replay miss and hit, budget block, answer parser, fixture-name clash).

### 6.4 Limits

1. Prices must be re-checked against the official page.
2. The ledger is per machine. Spending on other machines is not added up.
3. With `temperature` off, new live calls are not repeatable. Use the cache.

---

## 7. Step 4.5: Generator

**Goal:** policy rule text to candidate Foundry tests, then the validity filter (step 4.2).

**Status: COMPLETE.** Commits `68b6df9`, `eaefdc6`, `474cad1`. The Sonnet batch and the benchmark summary were committed by the project owner (hash not recorded here). Files: `pipeline/generator.py`, `pipeline/benchmark_summary.py`, `candidates/<batch>/`, `results/filter_<batch>/`, `results/benchmark_generated.md` and `.json`.

### 7.1 How it works

1. For each rule, `prompts.generator_prompt` fills `generator.md` with the rule text, the code slice, the fixture API and the fixture facts, and asks for 4 tests. The generator never sees the variants or the gold tests.
2. One model call per rule. The raw answer is saved to `candidates/<batch>/raw/`.
3. `prompts.extract_solidity` pulls out the code and renames the contract to `Cand_<rule>_<batch>`. A file is **skipped before running** if it defines `setUp`, an `invariant_` function, a function name that already exists in the fixture, a test with arguments, `vm.ffi`, or has no test or no code block. Skipped files go to `candidates/<batch>/rejected/` and count as invalid.
4. All usable files of the batch go through `pipeline/validity_filter.py`. Output: `results/filter_<batch>/report.md`.

The rule ID for each policy line is **chosen by the issuer** (decision 9). There is no automatic matching of free text to rule IDs.

```
python pipeline/generator.py --mode live --model haiku --rules default --batch d1
python pipeline/generator.py --mode replay --rules K1 K2 --batch d1      (free)
python pipeline/benchmark_summary.py --group Haiku=d1,d2,e1 --group Sonnet=s1
```

### 7.2 Batches

| Batch | Model | Rules | Result |
|---|---|---|---|
| mock1 | mock | K1 | 4 judged: 3 KEEP, 1 VACUOUS (checks the whole chain for free) |
| b1 | Haiku | K1 | 5 judged: 4 KEEP, 1 VACUOUS. $0.0028 (first real run) |
| d1 | Haiku | K1 K3 J1 H1 H3 | 16 judged: 13 KEEP, 3 VACUOUS. **H1 gave an empty answer** (6,000 output tokens used, stop reason `max_tokens`, file size 0) |
| d2 | Haiku | H1 (retry, limit 12,000) | 4 judged: 4 KEEP |
| e1 | Haiku | K2 J2 J3 H2 H4 | 20 judged: 15 KEEP, 5 VACUOUS |
| s1 | Sonnet | the same 10 rules | First run: 5 of 10 files skipped by an over-strict name check (helpers like `_amt`). After the fix, a free replay judged all 10 files |

K4 and K5 were not generated: stock T-REX violates them, so a correct test fails on clean configurations and would be REJECT. J4 is a known-exception trap, not an audit rule.

### 7.3 Benchmark (10 rules, same prompt, `results/benchmark_generated.md`)

| Measure | Haiku 5.5 (d1, d2, e1) | Sonnet 5.5 (s1) |
|---|---|---|
| Tests judged | 40 | 40 |
| KEEP / VACUOUS / REJECT | 32 / 8 / 0 | 32 / 8 / 0 |
| Valid and non-vacuous | 80% | 80% |
| Variants killed by a generated test | 12 of 13 (not V11) | 12 of 13 (not V11) |
| LLM calls (failed = cut off) | 11 (1 failed) | 10 (0 failed) |
| Input / output tokens | 88,231 / 52,594 | 80,278 / 22,454 |
| Cost, all calls | $0.0351 | $0.3851 |
| Cost per rule | $0.0035 | $0.0385 |
| Model time (seconds) | 236 | 163 |

- **Clearance criterion** (at least 70% valid and non-vacuous): met by both. If Haiku's lost first H1 attempt counts as 4 invalid tests, Haiku is 32 of 44 = 73%, still met.
- **False positives:** 0 REJECT among 80 tests. They ran on 5 of the 8 clean configurations (scenario tests skip C03, C04, C07), so this evidence is a little weaker than for the gold set.
- **Cost:** Sonnet is about 11 times more expensive and scored the same. **Haiku is the default model.** Sonnet stays as the comparison column.
- All numbers come from one run per model with one prompt.

### 7.4 Fixes made along the way

| Problem | Fix |
|---|---|
| Haiku answer empty after 6,000 output tokens | Default output limit raised to 12,000. Probable cause: hidden reasoning uses the tokens (evidence: an empty file, and 1,500 to 1,900 output tokens for about 300 visible words later; not proven) |
| Check rejected any helper function starting with `_` (5 Sonnet files wasted) | Replaced by a check for a name that already exists in the fixture API |
| Token estimate too low | Worst-case factor 1.3 changed to 1.7 |

### 7.5 Observations

1. **VACUOUS tests are mostly "normal case still works" tests.** Each rule has one or two. They guard against over-blocking and cannot kill a seeded bug. Two are unproven rather than useless (for example `H4_capIsNotZero`, because no variant sets the cap to 0).
2. **"Kills a variant" is not "kills its own rule's variant".** The J1 tests use `ir.updateCountry(b, RESTRICTED)` as setup, so they also fail on V06 (a J2 bug). Three of the four H3 tests fail only on V09 and V10 (H1 and H2 bugs). A stricter rule-specific measure would score lower.
3. **V11 is not reachable** by scenario tests (it starts with balances). The human gold set found it only through random-sequence property tests.
4. **K3 test is stricter than the policy.** `test_K3_requiredTopicsNonEmptyAndIncludeKyc` demands the KYC topic specifically, but the policy says only "at least one topic". It passes on all clean configurations, but could raise a false alarm on a correct configuration that requires a different topic.
5. **H1 "normal case" tests read the module's own counter** (`_idBalance` calls `maxBalanceModule.getIDBalance`), so they mix an H3-style check into H1.
6. The prompt's rules were followed well: tests use `CAP`, compare balances with their starting values, check real balances and use the fixture helpers.

### 7.6 Limits

1. The filter shows that a test runs and kills a variant, not that it checks the right thing. The independent evaluator (Phase 5) covers this.
2. 13 variants chosen by the author, 8 clean configurations (Phase 3 limits still apply).
3. Live results are not repeatable (temperature off). Replay from the cache is.

---

## 8. Step 4.6: Explainer

**Goal:** turn failing generated tests into short audit findings for an issuer who is not a Solidity expert.

**Status: COMPLETE, with the known limits in 8.5.** Files: `pipeline/explainer.py`, `pipeline/prompts/explainer.md` (version 2), `pipeline/mock/explainer.txt`, `results/explain_<batches>_<mode>/`. The 4.6 files and result folders are not committed yet (the previous commit step covered 4.5).

### 8.1 How it works

1. It reads `results/filter_<batch>/joint/forge.log` and finds which generated test failed on which configuration.
2. **One finding per (configuration, rule).** All failing tests of one rule on one configuration go into one call, so three failing tests with one cause give one finding.
3. The model sees: the policy text, the failing test functions plus the helper functions in the file, the fixture facts, the `[FAIL: reason]` lines, and the known exceptions (an agent's `forcedTransfer` to a restricted country; the same-identity cap rejection). It does not see the code slice. K4 and K5 are not listed as known exceptions because Phase 2 gave them no severity.
4. Scenario tests give only a one-line reason (for example `next call did not revert as expected` or `idA tracked != real: 75 != 50`), no call sequence. The reproduction steps come from the test source.
5. **Blind mode (default):** the model is not told what the configuration changes, which is all a real audit knows. **Reveal mode** (`--reveal-config`) adds the true description from `configs.json`. It leaks the cause and is only for comparison.
6. **Automatic checks** on every answer, shown as warnings: a severity on the first line, the five headings in order, at most 250 words, and every backticked function name must appear in the input given to the model.

```
python pipeline/explainer.py --mode live --model haiku --batch d1 e1 --configs V04 V05 V09 V12 V13
python pipeline/explainer.py --mode live --model haiku --batch d1 --configs V05 V12 --reveal-config
```

### 8.2 Runs

| Run | Prompt | Result |
|---|---|---|
| V05 and V12, blind and reveal | v1 | All four answers over the word limit (284, 290, 300, 303 words). Steps used code names (`ir`, `CAP`). The model never learned the real amounts |
| V04, V05, V09, V12, V13, blind (batches d1, e1) | v2 | 12 findings, **12 pass both automatic checks**, cost $0.0163 (about $0.0014 each), 1,553 to 4,359 output tokens each |

Prompt v2 changes: the first line is exactly `Severity: X`; at most 6 reproduction steps with one representative test written out; the fixture facts are added with an instruction to use real names and amounts; word target 200; the revert-message rule is one sentence.

### 8.3 What was checked by hand

| Check | Result |
|---|---|
| Blind V05 | Says the cause is not known. It does not name the wrong country code |
| Reveal V05 | Says 410 instead of 408 is the likely cause and admits the constant is not shown |
| V12 | Tracked 75 against real 50 after `forcedTransfer`: matches the test source (mint `CAP/10`, burn a quarter, `forcedTransfer` a quarter). Blind infers that the tracker was not updated, reveal says `forcedTransfer` does not call `transferred`, which matches V12 |
| V05 J1 steps | The report says `ir.updateCountry(b, RESTRICTED)`. The source has exactly that call at lines 17, 35 and 73 |

### 8.4 Cost

About $0.0014 per finding on Haiku. All 13 variants once would cost a few cents.

### 8.5 Known limits

1. **The automatic checks catch format and invented function names, not wrong reasoning.** Only two reports were compared with the test source by hand.
2. **Code names remain** in most findings (for example `CAP / 10`, `ir.updateCountry`, helper functions such as `_revokeClaim` or `_idBalance` listed as affected functions), although the prompt asks for real names. Several findings say a cap value "is not given". Keeping code names in the reproduction steps does help a developer reproduce the finding.
3. **No root-cause grouping.** V04 (empty topic list) gives four findings (H3, K1, K2, K3) with one cause. A finding for a rule is sometimes a side effect (the V04 H3 finding is really a KYC problem).
4. **Every finding is HIGH.** No seeded variant produces a MEDIUM (token unusable) case, and the INFO path (known exceptions) is not exercised because those tests pass.
5. **The explainer sees only tests that failed**, with no call sequence for scenario tests.
6. Output is 1,500 to 2,400 tokens for about 200 to 300 visible words, which again suggests hidden reasoning (not proven).

---

## 9. Step 4.7: End-to-end demo

**Goal:** show policy input → generated property → executed test → counterexample → audit report in one command.

**Status: COMPLETE.** Files: `pipeline/demo.py`, `pipeline/DEMO.md`, `candidates/probe/ProbeJ4.sol`, `results/demo_<config>/report.md` and `report.json`, `results/filter_probe/`.

### How it works
1. Policy input: the 5 default rules (K1, K3, J1, H1, H3), rule IDs chosen by the issuer.
2. Generated properties: tests from the saved batches d1 and d2 (d2 replaces the empty H1 answer of d1).
3. Executed tests: results on the target configuration are read from the saved filter matrices. They are not re-run live.
4. Counterexamples: failing tests and reasons are read from the saved forge logs. The explainer writes one finding per failing rule. It only runs if a test failed.
5. Report: rule status table, findings grouped by symptom (K, J or H rules), the reproducible test the explainer names, the INFO line, and cost.

### Rules added in the report (all symptom-based, so the audit stays blind)
- A failure message of the form "0 != N" on an H1 test is labelled a side effect (the module's counter did not move) and left out of the direct-evidence count.
- If a KYC rule fails and an H3 test fails without a "tracked != real" message, it is labelled a side effect of the KYC failure.
- If all tracked balances stay at 0 on every failing H3 test, a hint is printed to check `compliance.getModules()`.
- The INFO line (forcedTransfer to a restricted country, agent-only) comes from a fixed probe test, not from the policy.

### Results
| Target | Rules failing | Groups | LLM cost this run |
|---|---|---|---|
| C01 (clean) | none | none | $0 |
| V09 | H1, H3 | Holding limit (direct evidence H1 2 of 4, H3 4 of 4) | $0.0018 paid |
| V04 | K1, K3, H3 | KYC, and H3 marked as a side effect (0 of 1 direct) | $0 (cached) |

The known-exception probe (`test_J4_forcedTransferToRestrictedCountrySucceeds`) passes on all 12 variants it ran on (VACUOUS, as intended).

### Limits
1. Test results are reused, not re-run, so the demo shows the pipeline on saved evidence.
2. Grouping is by rule category, tuned to the seeded bugs. An unknown bug could appear as a separate group.
3. The explainer still says the cap value "is not given", because the audit is blind.
4. The target must be one of the pinned configurations (C01 to C08, V01 to V13).
5. Only 3 targets have been run. V11 is not reachable by generated scenario tests.



## 10. Design decisions for Phase 4 (agreed)

1. **Kind detection is automatic** (invariants or scenarios), so scenario tests skip C03, C04, C07 and V11.
2. **Wrappers are deleted after each run**, so Phase 3 counts stay valid.
3. **Candidate tests live in `candidates/`**, outside `test/`, and import the fixture as `"../../test/ComplyFixture.sol"`.
4. **Step 4.2 has its own log parser** that keeps the real test name, so generated tests need no special naming.
5. **Three outcomes for a test:**
   - REJECT: does not compile, or fails on any clean configuration (this is "valid").
   - VACUOUS: passes on every variant it ran on.
   - KEEP: passes on all clean configurations and fails on at least one variant.
6. **VACUOUS means unproven, not wrong.** A correct test for a rule that none of the 13 variants breaks is labelled VACUOUS and listed separately for review.
7. **"No visible assertion" is a note, not an outcome.** An assertion inside a handler in another contract cannot be seen from the test source, so it would give wrong labels if it decided the outcome.
8. **The generator sees only the clean pinned code** (slices, fixture summary and facts), never the variants or the gold tests.
9. **The issuer picks the rule ID** for each policy line (a list in the CLI or web page, text pre-filled and editable). No classifier in the MVP.
10. **Haiku 5.5 is the default model.** Sonnet 5.5 is the comparison column.
11. **Generated tests are plain `test_` functions with no arguments.** No fuzz tests, no invariant functions, no handlers.
12. **The explainer is blind by default.** Reveal mode is for comparison only.
13. **One finding per (configuration, rule).**
14. **Spending is capped** at `session_cap_usd` 15 per machine, within the team plan of 100 (hard stop 115).
15. **Step 4.8 is added:** an LLM-only vulnerability review baseline, to complete the three-way benchmark.

---

## 11. Status and next

- [x] 4.0 Cfg contracts importable, manifest written and checked
- [x] 4.1 Executor reproduces the Phase 3 table
- [x] 4.2 Validity filter: gold 16 KEEP / 2 VACUOUS / 0 REJECT, bad tests rejected
- [x] 4.3 Code slicer: 13 rule slices, no comments, 11% to 35% of the full source
- [x] 4.4 LLM interface and prompts: mock, replay, live, cache, ledger, cap
- [x] 4.5 Generator: 10 rules, Haiku and Sonnet each 32 of 40 KEEP (80%), 12 of 13 variants, 0 REJECT
- [x] 4.6 Explainer: 12 findings pass the automatic checks (known limits in 8.5)
- [x] 4.7 End-to-end demo script: policy input, generated property, executed test, counterexample, audit report
- [ ] 4.8 LLM-only review baseline: Haiku and Sonnet read the same slices and policy rules and list vulnerabilities without running tests; score against the 13 variants; time and token cost

**To commit before 4.7:** `pipeline/explainer.py`, `pipeline/prompts/explainer.md`, `pipeline/mock/explainer.txt`, `results/explain_*`, `results/llm_cache`, `results/llm_ledger.jsonl`.

**Ideas for 4.7:** run the whole chain for the 5 default rules on one chosen configuration; group findings by cause; show a MEDIUM or INFO case in the demo if a suitable configuration can be built (for example `forcedTransfer` to a restricted country).

**Total spent through 4.6 (ledger on the owner's machine):** $0.4435 of the $20 credit (ledger summary printed after the 12-finding explainer run).