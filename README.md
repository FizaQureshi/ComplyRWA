# ComplyRWA

**AI-assisted policy verification and compliance-bypass detection for tokenized Real-World Assets (RWAs).**

ComplyRWA is a pre-deployment security auditor for tokens built on **ERC-3643 / T-REX**. An issuer writes a few plain-English compliance rules (for example, "Only KYC-verified investors from approved jurisdictions may receive tokens"). ComplyRWA turns those rules into executable Foundry tests, runs them against the token's contracts, and reports any transfer that breaks the issuer's intended policy.

---

## Table of contents

1. [The problem](#1-the-problem)
2. [What ComplyRWA does](#2-what-complyrwa-does)
3. [What is in this repository](#3-what-is-in-this-repository)
4. [Pinned target system](#4-pinned-target-system)
5. [Repository layout](#5-repository-layout)
6. [Setup](#6-setup)
7. [How to use the repository](#7-how-to-use-the-repository)
8. [Benchmark results](#8-benchmark-results)
9. [Project documents](#9-project-documents)
10. [Known limits](#10-known-limits)
11. [Licence notes](#11-licence-notes)

---

## 1. The problem

Issuers of tokenized RWAs configure complex transfer rules: who is KYC-verified, which countries are allowed, how much one investor may hold. In ERC-3643 these rules are spread over several contracts (`Token`, `IdentityRegistry`, `ModularCompliance` and its modules).

A mistake in the **configuration** can let a forbidden transfer through even when each contract looks secure on its own. Examples:

- The list of required KYC claims is empty, so *every* registered wallet counts as "verified".
- A compliance module is removed, and the rule it enforced silently disappears.
- A holding limit is set to the maximum number, so it limits nothing.
- A wrong country code is restricted, so the intended country is still allowed.

These are hard to spot by reading code. ComplyRWA finds them by running tests.

## 2. What ComplyRWA does

ComplyRWA has five parts:

| Part | What it does |
|---|---|
| Policy-to-Invariant Generator | Turns 3 to 5 plain-English rules into Solidity/Foundry tests (using an LLM) |
| Cross-Contract Analyzer | Cuts the contracts down to the functions each rule needs (a "code slicer") |
| Automated Security Validator | Runs tests on many configurations and filters out bad tests |
| Counterexample Explainer | Turns a failing test into a readable report |
| Issuer-facing MVP | CLI or web page: pick a project, enter rules, get a report |

## 3. What is in this repository

- A **pinned ERC-3643 (T-REX) setup** with Foundry and Halmos environments.
- A **policy catalogue**: 13 rules in three categories (KYC, jurisdiction, holding limit).
- A **hand-written answer key**: 18 Foundry tests covering all 13 rules.
- A **test fixture** that builds a working ERC-3643 system in one call.
- **8 clean (correct) configurations** and **13 seeded vulnerable variants**, plus 3 confirmed gaps in stock T-REX/ONCHAINID.
- A **benchmark table** showing which test catches which variant.
- **Pipeline tools** (Python): an executor, a validity filter and a code slicer.

### The three policy categories

| Category | Component checked | Rules |
|---|---|---|
| KYC | `IdentityRegistry` (and the registries behind it) | K1 to K5 |
| Jurisdiction | `CountryRestrictModule` | J1 to J4 |
| Holding limit | `MaxBalanceModule` | H1 to H4 |

The default audit uses five rules that cover all three categories: **K1, K3, J1, H1, H3**.

## 4. Pinned target system

All results depend on these exact versions. Please do not change them without updating `environment.md`.

| Item | Value |
|---|---|
| Target | T-REX (ERC-3643) by Tokeny, https://github.com/TokenySolutions/T-REX |
| Tag | `4.1.6` |
| Commit | `a09cfd38aa257d56db7ff9c90f30e65f125a141b` |
| Solidity | 0.8.17 (optimizer on, 200 runs) |
| Foundry (`forge`) | 1.8.7 |
| Halmos | 0.3.3 |
| Node.js | 20 LTS (20.20.2 used) |
| Python | 3.11 (3.11.9 used) |
| Hardhat | 2.14.0 (comes from T-REX's `package.json`) |

The `T-REX/` folder is **never modified**. Any changed contract is a copy inside `variants/`.

## 5. Repository layout

```
ComplyRWA/
  foundry.toml            Foundry settings (fixed fuzz seed, runs, depth)
  environment.md          Exact tool versions and install notes
  T-REX/                  Pinned T-REX code (cloned separately, git-ignored)
  variants/               Copied-and-changed contracts used for seeded bugs
  test/
    ComplyFixture.sol     Shared fixture: builds the clean baseline (C01)
    gold/                 Hand-written answer-key tests (G01 to G14)
    clean/                Clean configurations C02 to C08
    configs/              Importable configuration contracts (CleanCfgs, VariantCfgs)
    variants/             Wave1.t.sol (config-only) and Wave2.t.sol (code copies)
  candidates/             Candidate tests (outside test/ on purpose)
  pipeline/
    configs.json          Manifest of all 21 configurations
    check_manifest.py     Checks the manifest against the Solidity code
    executor.py           Runs a test file on every configuration
    validity_filter.py    Classifies tests as KEEP, VACUOUS or REJECT
    slicer.py             Builds small, comment-free code slices per rule
    slice_map.json        Which functions belong to which rule
    fixture_facts.md      Short summary of the fixture for an LLM
    slices/               Generated slices
  results/                Logs and result tables
  scripts/make_table.py   Builds the variant-by-test table
```

## 6. Setup

The project was developed on **Windows (native, no WSL)** using Git Bash and PowerShell. The steps below follow that setup. Linux and macOS should work in a similar way but have not been tested.

### 6.1 Install the tools

1. **Git**, **Node.js 20 LTS** (for example through nvm-windows), **Python 3.11**, and optionally VS Code.
   Use Node 20 LTS. Newer "Current" releases of Node are not what Hardhat expects.
2. **Foundry.** In Git Bash:
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```
   If `forge: command not found` appears, add Foundry to your PATH (adjust the user name):
   ```bash
   export PATH="$PATH:/c/Users/<your-user>/.foundry/bin"
   ```
   Add the same line to `~/.bashrc` to keep it.
3. **Halmos** (in its own virtual environment, PowerShell):
   ```powershell
   python -m venv "$HOME\.venvs\halmos"
   & "$HOME\.venvs\halmos\Scripts\Activate.ps1"
   pip install halmos
   ```
   On Windows `pip install halmos` may fail while building `safe-pysha3` (it needs a C++ compiler). The workaround used in this project is to run `pip install halmos --no-deps` and then install the dependencies by hand with the `eth_hash[pycryptodome]` backend. See `environment.md` for details.
   Halmos is part of the toolchain for symbolic checks; the tests in this repository run with Foundry.

### 6.2 Clone this repository

```bash
git clone <this-repository-url> ComplyRWA
cd ComplyRWA
```

### 6.3 Get the pinned T-REX code

`T-REX/` is git-ignored, so each person clones it into the project folder:

```bash
git clone https://github.com/TokenySolutions/T-REX.git
cd T-REX
git checkout tags/4.1.6
git rev-parse HEAD        # must print a09cfd38aa257d56db7ff9c90f30e65f125a141b
npm ci
npx hardhat compile
cd ..
```

Optional check: `npx hardhat test` inside `T-REX/` should show **777 passing, 0 failing** (about 1 minute).

### 6.4 Compile with Foundry

From the repository root:

```bash
forge build
```

This should end with "Compiler run successful". Warnings come from T-REX and library code, which is left unmodified, so they can be ignored.

### 6.5 Check that everything works

```bash
forge test --no-match-contract GoldSpecial --no-match-path "test/variants/*"
```

Expected: **79 tests passed, 0 failed** (the clean configurations plus the smoke and baseline tests).

## 7. How to use the repository

All commands run from the repository root in Git Bash. Foundry's `bin` folder must be on your PATH.

### 7.1 Reproduce the Phase 3 benchmark

```bash
# 1. Clean set: expect 79 passed, 0 failed
forge test --no-match-contract GoldSpecial --no-match-path "test/variants/*" > results/clean.log 2>&1

# 2. Special set (G11, G12, G14): all 3 must FAIL, because they show gaps in stock T-REX/ONCHAINID
forge test --match-contract GoldSpecial > results/special.log 2>&1

# 3. Seeded variants (delete stale fuzz failures first)
rm -rf cache/invariant
forge test --match-path "test/variants/*" > results/all_variants.log 2>&1

# 4. Build the variant-by-test table
python scripts/make_table.py results/all_variants.log results/clean.log
```

Expected: 145 variant tests (109 passed, 36 failed), 13 of 13 variants caught, 0 of 8 clean configurations with a false alarm. Output files: `results/variant_table.csv` and `results/variant_table.md`.

> Always delete `cache/invariant` before a benchmark run. Foundry may otherwise replay old failures instead of fuzzing fresh.

### 7.2 Run any test file on every configuration (executor)

```bash
python pipeline/executor.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/exec_gold
```

It generates temporary wrapper contracts, runs forge on all configurations, writes `table.csv` and `table.md`, and deletes the wrappers again. Running the gold tests this way gives a table identical to Phase 3.

### 7.3 Judge candidate tests (validity filter)

```bash
python pipeline/validity_filter.py --tests test/gold/GoldInvariants.t.sol:GoldInvariantsTest test/gold/GoldScenarios.t.sol:GoldScenariosTest --out results/filter_gold
```

Every test gets one outcome:

| Outcome | Meaning |
|---|---|
| **REJECT** | Does not compile, or fails on a clean configuration (a correct test must pass on correct setups) |
| **VACUOUS** | Valid, but passes on every variant, so it never detects any seeded bug ("unproven", not necessarily wrong) |
| **KEEP** | Passes on all clean configurations and fails on at least one variant |

For the hand-written gold set the result is 16 KEEP, 2 VACUOUS, 0 REJECT. Your own candidate tests must live in `candidates/<batch>/` (not in `test/`) and import the fixture as `"../../test/ComplyFixture.sol"`.

### 7.4 Build the code slices

```bash
python pipeline/slicer.py --check     # verifies the slice map against the pinned source
python pipeline/slicer.py --all       # writes one slice per rule into pipeline/slices/
python pipeline/slicer.py --rule K1   # a single rule
```

A slice contains only the functions a rule needs, with all comments removed (T-REX has some copy-pasted comments that would mislead an LLM). Slices are 11% to 35% of the full source size.

### 7.5 Check the configuration manifest

```bash
python pipeline/check_manifest.py
```

Re-run this whenever a configuration contract changes.

## 8. Benchmark results

| Measure | Target | Result |
|---|---|---|
| Seeded vulnerable variants | 12 to 15 | 13 (V01 to V13) |
| Detection rate (hand-written tests) | at least 75% | 13 of 13 = 100% |
| False-positive rate (clean configurations) | at most 15% | 0 of 8 = 0% |
| Gold tests (hand-written invariants) | at least 8 | 18 covering 13 rules |
| Valid and non-vacuous (gold set) | reference for generated tests | 16 of 18 = 89% |

### Stock gaps confirmed by tests

These are behaviours of stock T-REX/ONCHAINID, not bugs we added:

| ID | Rule | Gap |
|---|---|---|
| S01 | K4 | An expired KYC claim is still accepted (no on-chain expiry check) |
| S02 | K5 | A holder whose KYC was revoked can still send tokens (only the receiver is checked) |
| S03 | K2 | A revoked claim can be revived by re-adding it with a "twin" signature (a gap in the ONCHAINID dependency) |

### Known exception

`forcedTransfer` (an agent-only function) skips the read-side compliance checks. `MaxBalanceModule` still catches it, but `CountryRestrictModule` does not. The auditor must label this as a **known exception**, not as a vulnerability.

## 9. Project documents

Longer write-ups of each phase:

| File | Content |
|---|---|
| `environment.md` | Exact versions, install notes, problems and fixes |
| `Phase1.md` | Study notes on the transfer path through `Token`, `IdentityRegistry`, `ModularCompliance` and the modules |
| `Phase2.md` | Policy catalogue: 13 rules, seeded variants, clean configurations |
| `Phase3.md` | Gold tests, fixture, results table, how the rates were calculated |
| `Phase4.md` | The AI pipeline (executor, validity filter, code slicer) |

## 10. Known limits

- Tied to **one pinned implementation** (T-REX 4.1.6) and three policy categories.
- The 13 variants were chosen by the project authors, so they are not an exhaustive bug list.
- Property (fuzz) results depend on the fixed seed and 64 runs set in `foundry.toml`. Scenario results do not.
- The clean set has only 8 configurations, so one false alarm would already be 12.5%.

## 11. Licence notes

- T-REX is GPL-3.0 (Tokeny). Files in `variants/` are copies derived from it.
- `MaxBalanceModule` is also under CC-BY-NC-4.0, so `variants/MaxBalanceModuleV10.sol` carries the same non-commercial restriction. This matters if ComplyRWA is ever commercialised.
- Add a `LICENSE` file for this repository's own code once the project owners decide on a licence.
