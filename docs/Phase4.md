# ComplyRWA: Phase 4 Report (The AI Pipeline)

**Goal of Phase 4:** build the pipeline that turns an issuer's plain-English policy into executable Foundry tests, filters them, runs them on every configuration, and explains what failed.

**Status so far:** steps 4.0 to 4.3 are COMPLETE. Steps 4.4 to 4.7 are not started.

Pinned system: T-REX tag `4.1.6`, commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`, Solidity `0.8.17`, Foundry `1.8.7`, Halmos `0.3.3` (see `environment.md`).

> **How to read this file.** Section 1 is the step list. Section 2 covers step 4.0, section 3 step 4.1, section 4 step 4.2, section 5 step 4.3. Section 6 records design decisions. Section 7 is the status and what comes next. Steps are added here as they close.

---

## 1. Phase 4 build order

Everything that needs no LLM comes first, so the LLM choice can wait until step 4.4.

| Step | What | Needs LLM? | State |
|---|---|---|---|
| 4.0 | Prepare: importable Cfg contracts and a manifest | No | **Done** |
| 4.1 | Executor: run any test file on every configuration, same table | No | **Done** |
| 4.2 | Validity filter: reject tests that do not compile, fail on clean, or are vacuous | No | **Done** |
| 4.3 | Code slicer | No | **Done** |
| 4.4 | LLM interface and prompts (mock/replay first) | Yes | |
| 4.5 | Generator: policy text to candidate tests, then the filter | Yes | |
| 4.6 | Explainer (template fallback) | Yes | |
| 4.7 | End-to-end demo script | Yes | |

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

**Status: COMPLETE.** Commit: _fill in after committing_. Files: `pipeline/slicer.py`, `pipeline/slice_map.json`, `pipeline/fixture_facts.md`, and the generated `pipeline/slices/`.

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

## 6. Design decisions for Phase 4 (agreed)

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

---

## 7. Status and next

- [x] 4.0 Cfg contracts importable, manifest written and checked
- [x] 4.1 Executor reproduces the Phase 3 table
- [x] 4.2 Validity filter: gold 16 KEEP / 2 VACUOUS / 0 REJECT, bad tests rejected
- [x] 4.3 Code slicer: 13 rule slices, no comments, 11% to 35% of the full source
- [ ] 4.4 LLM interface and prompts (next)
- [ ] 4.5 to 4.7

Commits: step 4.0 `c9763d9`, step 4.1 `35ad477`, step 4.2 `bc193dd`, step 4.3 _fill in after committing_.