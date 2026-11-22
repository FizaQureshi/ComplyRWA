# ComplyRWA: Phase 3 Report (Gold Standard and Harness)

**Goal of Phase 3:** build the answer key and the test bench that Phase 4 (the AI pipeline) will be measured against.

**Status: COMPLETE.** 13 of 13 seeded variants are caught, 0 of 8 clean configurations produce a false alarm, and the three stock gaps are confirmed.

Pinned system: T-REX tag `4.1.6`, commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`, Solidity `0.8.17`, Foundry `1.8.7`, Halmos `0.3.3` (see `environment.md`).

> **How to read this file.** Section 1 explains what Phase 3 was for. Sections 2 to 8 describe what was built, in the order it was built. Sections 9 and 10 explain how the detection rate and the false-positive rate were calculated. Section 11 holds the observations to record. Section 12 lists the problems met and how they were solved. Sections 13 to 15 cover reproduction, limits and the hand-off to Phase 4.

---

## 1. What Phase 3 was about

Phase 2 fixed *what* ComplyRWA checks: 13 rules (K1 to K5, J1 to J4, H1 to H4) in three categories (KYC, jurisdiction, holding limit). Phase 3 turns those rules into running code so we can later answer one question honestly: **"Does the AI-generated test suite find the bugs that a human-written suite finds?"**

The phase description in the project plan says: *hand-write correct Foundry tests, build a test fixture, create 12-15 vulnerable variants plus clean configs.* Phase 3 therefore produced five things:

| # | Deliverable | Purpose |
|---|---|---|
| 1 | A shared **fixture** | Builds a working ERC-3643 system in one call, with hooks so a variant can change one part |
| 2 | **Gold tests** (G01 to G14) | Hand-written tests that say what "correct" means for each rule |
| 3 | **Clean configurations** (C01 to C08) | Correct setups that must *not* raise findings. They measure false positives |
| 4 | **Seeded variants** (V01 to V13) | Deliberately broken setups. They measure detection |
| 5 | A **results table** and script | Variant-by-test evidence for the project's clearance criteria |

The clearance criteria this phase supports (from the project brief):

- 12 to 15 seeded vulnerable variants, with at least 75% of the reproducible ones detected.
- At most 15% false positives on a separate set of non-vulnerable configurations.
- At least 8 executable invariants (here hand-written; Phase 4 repeats this with an LLM).

---

## 2. Inputs from Phase 2

Phase 3 started from three lists written in Phase 2:

- **Default audit set (5 rules):** K1, K3, J1, H1, H3. These give the 9 default gold tests.
- **Extended set (5 rules):** K2, J2, J3, H2, H4.
- **Special rules:** K4, K5, J4 (known exception) and the K2 twin-signature case.
- **Variant plan:** V01 to V13 (13 seeded variants) plus stock gaps S01 to S03 (S04 was added later, after Phase 4 step 4.8).
- **Clean plan:** C01 to C08.
- **Decisions D1 to D4**, all accepted:
  - D1: `forcedTransfer` is judged per module and per policy.
  - D2: K5 (revoked sender can still send) is in scope as "violated by stock".
  - D3: moving 500 tokens between two wallets of one identity (600 held, cap 1000) is *expected to be rejected*.
  - D4: K4 (expired KYC) is in scope as a stock gap.

---

## 3. Repository layout after Phase 3

```
ComplyRWA/
  foundry.toml                     fuzz seed, runs, depth are fixed here
  T-REX/                           pinned code, never modified
  variants/                        copied-and-changed contracts (Wave 2)
    IdentityRegistryV01.sol        V01
    IdentityRegistryV06.sol        V06
    ClaimIssuerV02.sol             V02
    ClaimIssuerV03.sol             V03
    MaxBalanceModuleV10.sol        V10
    TokenV12.sol                   V12
  test/
    ComplyFixture.sol              shared fixture, builds clean baseline C01
    Smoke.t.sol                    signing and recovery smoke test
    C01_Baseline.t.sol             baseline checks (C01, C03, C04, C07 scenarios)
    StockGaps.t.sol                S01, S02, S03 proven as passing "gap" tests
    StockGapsVByte.t.sol           S04 (added after Phase 4), passing "gap" test
    gold/
      GoldHandler.sol              random-action driver with ground truth
      GoldInvariants.t.sol         7 property tests
      GoldScenarios.t.sol          11 scenario tests
      GoldSpecial.t.sol            G11, G12, G14 (expected to fail on stock)
    clean/CleanConfigs.t.sol       C02 to C08
    variants/
      Wave1.t.sol                  config-only variants
      Wave2.t.sol                  code-copy variants
  results/
    clean.log, special.log, all_variants.log, wave1.log, wave2*.log
    variant_table.csv, variant_table.md
  scripts/make_table.py
```

**Rule kept from Phase 0:** `T-REX/` stays untouched. Every changed contract is a copy in `variants/`.

**Licence note.** The copied files are derived from T-REX (GPL-3.0). `MaxBalanceModule` is also CC-BY-NC-4.0, so `MaxBalanceModuleV10.sol` carries the same non-commercial restriction. This matters only if ComplyRWA is ever commercialised.

---

## 4. The fixture (`test/ComplyFixture.sol`)

The fixture builds the clean baseline **C01** in `setUp()`. Every build step is `internal virtual`, so a variant overrides only the step it changes.

### 4.1 The cast (same as Phase 2)

| Actor | Wallets | Identity | Country | KYC |
|---|---|---|---|---|
| Alice | `a1`, `a2` | `idA` (shared) | 356 (India) | valid |
| Bob | `b` | `idB` | 356 | valid |
| Carol | `c` | `idC` | 408 (restricted) | valid |
| Mallory | `m` | `idM` | 356 | **registered, no claim** |

Policy numbers (variables so clean configs can change them): required topic `1`, restricted country `408`, cap `1000`. A fresh T-REX token starts paused, so the fixture calls `unpause()`.

### 4.2 Setup order

`_configure()` → `_makeActors()` → `_deployRegistries()` → `_deployClaimIssuer()` → `_deployComplianceAndToken()` → `_registerInvestors()` → `_wireModules()` → `unpause()` → `_afterSetUp()`.

`_wireModules()` runs `_deployModules()`, `_addModules()`, `_configureModules()`.

### 4.3 Hooks

| Hook | Added in | Used by |
|---|---|---|
| `_configure` | Step 3 | C05 (cap 500, countries 408 and 643) |
| `_afterSetUp` | Step 3 | C03, C04, C07 (special start states) |
| `_deployModules`, `_addModules`, `_configureModules` | Step 3 | C08, V05, V07, V08, V09, V11, V13 |
| `_deployClaimIssuer`, `_registerInvestors` | Step 3 | C02, C06, V01, V02, V04 |
| `_restrictCountry(country)`, `_setCap(cap)` (helpers) | Step 4a | Wave 1 variants |
| `_newIdentityRegistry()` | Step 4c | V01, V06 |
| `_newClaimIssuer(admin)` | Step 4c | V02, V03 |
| `_maxBalanceImpl()` | Step 4c | V10 |
| `_newToken()` | Step 4c | V12 |

Every hook was added as a **small separate change**, and the clean run was repeated afterwards. It always showed **79 passed**, which proves the hook changed nothing for the clean set. (After Phase 4 the clean run shows **80**, because S04 added one test; see section 10.3.)

### 4.4 Fixture rules learned from the pinned code

- Bind the token to the compliance contract **before** adding `MaxBalanceModule` (`Token.init` already does this).
- Modules are UUPS upgradeable: deploy each behind `ModuleProxy` and call `initialize()`.
- Claims are signed with `vm.sign` over exactly the hash `isClaimValid` rebuilds (data hash plus the `"\x19Ethereum Signed Message:\n32"` prefix). No second prefix.
- `ClaimIssuer` is deployed directly with `new ClaimIssuer(admin)`, and the signer key needs purpose 3.
- Revocation is keyed by the raw signature bytes, so a revoked claim re-issued with identical data stays revoked. Clean config C06 therefore re-issues with **different** data.

---

## 5. The gold tests

**18 tests cover all 13 rules.** P = property (fuzzed random sequences). S = scenario (fixed steps).

### 5.1 Default set (rules K1, K3, J1, H1, H3): 9 tests

| ID | Rule | What it asserts | Type |
|---|---|---|---|
| G01a | K1 | After any successful `transfer`/`transferFrom`, the receiver is KYC-verified | P |
| G01b | K1 | After any successful `mint`/`forcedTransfer`, the receiver is KYC-verified | P |
| G02a | K3 | The required topics list is not empty | S |
| G02b | K3 | A registered wallet with no claim (Mallory) cannot receive by `transfer` or `mint` | S |
| G03a | J1 | After any successful `transfer`/`transferFrom`, the receiver's country is not restricted | P |
| G03b | J1 | After any successful `mint`, the receiver's country is not restricted | P |
| G04 | H1 | After any action, every identity's **real** balance is at most the **policy** cap | P |
| G05a | H3 | After `transfer`/`transferFrom`, tracked balance equals real balance for every identity | P |
| G05b | H3 | After `mint`/`burn`/`forcedTransfer`, tracked equals real (property). `recoveryAddress` has its own scenario | P + S |

### 5.2 Extended set (K2, J2, J3, H2, H4): 5 tests

| ID | Rule | What it asserts |
|---|---|---|
| G06a/b/c | K2 | Each revocation route blocks receiving: (a) `deleteIdentity`, (b) trusted issuer removed, (c) claim revoked at the issuer |
| G07 | J2 | After `updateCountry(wallet, 408)`, a transfer to that wallet reverts |
| G08 | J3 | The country module is in `getModules()`, `isModuleBound` is true, and its restricted list matches the policy (408 yes; 356 and 840 no) |
| G09 | H2 | Two wallets of one identity share one cap: Bob sending 600 to `a2` (while `a1` holds 600) must revert |
| G10 | H4 | The cap equals the policy number. Probed through `canTransfer`: exactly the cap is allowed, cap + 1 is blocked |

### 5.3 Special set (K4, K5, J4, K2 twin signature): 4 tests

| ID | Rule | Expected on stock T-REX |
|---|---|---|
| G11 | K4: an expired claim must be rejected | **Fails** (stock gap S01) |
| G12 | K5: a sender whose claim was revoked cannot send | **Fails** (stock gap S02) |
| G13 | J4: `forcedTransfer` to a restricted country succeeds and is labelled "known exception" | **Passes** |
| G14 | K2: a revoked claim cannot be revived by re-adding it with a twin signature | **Fails** (stock gap S03) |

G01 to G10 and G13 must pass on every clean configuration. G11, G12 and G14 are kept **out** of the default run so they never disturb the false-positive measure. They are run separately (`GoldSpecial`).

### 5.4 Design rules that make the tests meaningful

1. **Tests judge against the policy, not against the configuration.** G01 to G04 use ground truth kept by the harness (who is KYC-verified, who is in country 408, the policy cap 1000). If a test asked the registry or module, a broken registry or module would simply agree with itself and variants such as V01 or V13 would go unnoticed.
2. **G04 uses real balances and the policy cap.** Checking the module's tracked balance against the module's own cap would miss V09 (module removed) and V13 (cap set to the maximum).
3. **G09 is a scenario and G04 is the general property.** They would otherwise check the same thing.
4. **G10 probes behaviour,** because `MaxBalanceModule` has no public getter for its cap.
5. **G05b is two tests** (random-action property and the `recoveryAddress` scenario). The results table lists them as separate columns, `G05b-prop` and `G05b-rec`.
6. **`forcedTransfer` is not checked for J1.** It is a known exception (D1, J4).
7. **The same-identity trap (D3)** is covered by clean config C03. The expected rejection is *not* reported as a bug.

### 5.5 The handler (`GoldHandler.sol`)

The handler is the random driver for the property tests.

- **Actions fuzzed (7):** `mint`, `transfer`, `transferFrom`, `forcedTransfer`, `burn`, `revokeKyc`, `setRestricted`.
- **Ground truth kept (ghost state):** which identity has valid KYC, which wallet is in a restricted country.
- **Amount limits:** mint amounts are bounded to `1 .. cap + 200`, so the fuzzer can push an identity over the cap. Transfer amounts are bounded to the sender's balance.
- **Violation counters (all must stay 0):** `k1Transfer`, `k1MintForced`, `j1Transfer`, `j1Mint`, `h3Transfer`, `h3Other`.
- **A property fails when an action succeeds although the ground truth says it must not.**
- **H3 check** covers every identity, including identities that start with balances, and reads the module's counters even after the module is removed.

**Handler defect found and fixed (Step 2).** The first call table showed the fuzzer calling the setup functions `addIdentity` and `addWallet` (about 20% of calls). That could overwrite the ground truth with random values and cause false findings. Fixed two ways: the setup functions accept only the test contract, and `GoldInvariants.t.sol` excludes them with `excludeSelector`. After the fix the call table lists exactly the 7 action functions with 0 reverts.

### 5.6 Fuzz settings (`foundry.toml`)

| Setting | Value |
|---|---|
| Fuzz seed | `0x436f6d706c79` |
| Invariant runs | 64 |
| Invariant depth | 40 (so 2,560 calls per invariant suite) |

Fixed settings make repeated runs give identical results. Every detection number in this report depends on them.

### 5.7 Early mutation check (sandbox only)

Before building the real variants, five quick mutants checked that the gold tests "have teeth": V04, V05, V07, V09, V13. All five were caught by the expected tests. This is how the G01 to G04 design (rule 1 and 2 above) was validated.

---

## 6. Clean configurations C01 to C08

They live in `test/C01_Baseline.t.sol` (C01) and `test/clean/CleanConfigs.t.sol` (C02 to C08). Each is a small `Cfg` contract that overrides one hook, combined with the property suite (`_Invariants`) and, where the start state allows, the scenario suite (`_Scenarios`).

| ID | What is different | Property suite | Scenario suite |
|---|---|---|---|
| C01 | Baseline | yes | yes |
| C02 | Topics 1 and 2 both required. Issuers X and Y both trusted for both topics. Tests AND across topics, OR across issuers | yes | yes |
| C03 | Alice holds 600 and her 500-token move between her own wallets was rejected (D3 trap) | yes | no |
| C04 | An agent `forcedTransfer` put 100 tokens in Carol's wallet (country 408) (D1/J4 trap) | yes | no |
| C05 | Cap 500; countries 408 and 643 restricted. Tests read the numbers from the policy, not from constants | yes | yes |
| C06 | Bob's claim revoked, then re-issued with **different** data | yes | yes |
| C07 | Bob holds exactly 1000 (the cap), reached by receiving exactly 100. Tests that the check uses `>` not `>=` | yes | no |
| C08 | `MaxBalanceModule` bound to a token that already has holders (Carol 300, `a2` 100), with a **correct** preset via `batchPreSetModuleState` | yes | yes |

**Why some have no scenario suite:** the scenario tests assume an empty start. C03, C04 and C07 start with balances, so only the property suite runs. Their scenario facts are checked in `C01_Baseline.t.sol` instead.

**C08 start state (note).** The start state mints 300 tokens to Carol (country 408) **before** the country module is bound. No rule can block this at that moment, so it is a legal setup step and not a bypass. Only after that is `MaxBalanceModule` bound with a correct preset. A reviewer that flags the mint to Carol as a jurisdiction bypass is raising a false alarm (this is what Sonnet's one clean false positive in step 4.8 was). C08 is documented, not changed, so no Phase 3 result moves.

**A false positive found in a gold test (not a contract).** On C08, G13 failed because it assumed Carol starts with 0 tokens. That was a flaw in the test. G13 now compares against Carol's starting balance. This is the kind of mistake the clean set exists to catch.

**Result:** all 8 clean configurations pass every gold test (see section 10).

---

## 7. Seeded variants V01 to V13

**Type codes:** C = code change in a copy, G = configuration only. Variants were built in two waves.

### 7.1 Method used for every variant

1. Write a small abstract `CfgVxx` contract that overrides **one** fixture hook.
2. Write `Vxx_Invariants` (property suite) and `Vxx_Scenarios` (scenario suite) that combine the gold suite with the `Cfg`. Because of Solidity's diamond inheritance, each class also re-states the override with `override(ComplyFixture, CfgVxx)`.
3. Run the variant and compare the failures with a prepared "should fail" table.
4. Variants that start with balances (V11) get only the property suite.

Copies are needed for Wave 2 because `isVerified`, `updateCountry`, `isClaimValid`, `forcedTransfer` and `_getIdentity` are **not** `virtual` in the pinned code, so inheriting does not work. Each copy has its imports rewritten to the `T-REX/contracts/...` and `@onchain-id/...` style.

### 7.2 Wave 1: configuration only (`test/variants/Wave1.t.sol`)

| ID | Rule | What was changed |
|---|---|---|
| V04 | K3 | `ctr.removeClaimTopic(KYC_TOPIC)`, so the required topics list is empty |
| V05 | J1 | Restrict country `410` instead of `408` |
| V07 | J3 | Country module removed with `removeModule` after setup |
| V08 | J3 | Country module bound, but no country ever restricted |
| V09 | H1 | `MaxBalanceModule` removed with `removeModule` |
| V11 | H3 | Bob already holds 800; `batchPreSetModuleState(compliance, [idB], [0])` then `addModule`. Property suite only |
| V13 | H4 | `setMaxBalance(type(uint256).max)` |

Findings from Wave 1:
- `batchPreSetModuleState` **accepts a preset of 0**, so the alternative build (`presetCompleted()` with nothing preset) was not needed for V11.
- The first "should fail" table was too short. It missed secondary failures, for example V04 also fails G06b and G06c (with no topics, removing the issuer or revoking a claim blocks nobody) and V05/V07/V08 also fail G07. The table was corrected before the run and then matched exactly.

### 7.3 Wave 2: code copies (`test/variants/Wave2.t.sol`, files in `variants/`)

| ID | Rule | File | What was changed |
|---|---|---|---|
| V01 | K1 | `IdentityRegistryV01.sol` | `isVerified` returns true when **any one** required topic is satisfied (OR instead of AND). Logic moved into `_topicOk` per topic |
| V02 | K1 | `ClaimIssuerV02.sol` | `isClaimValid` always returns `true` |
| V03 | K2 | `ClaimIssuerV03.sol` | `isClaimValid` skips the `isClaimRevoked(sig) == false` check |
| V06 | J2 | `IdentityRegistryV06.sol` | `updateCountry` emits the event but never writes the new country |
| V10 | H2 | `MaxBalanceModuleV10.sol` | `_getIdentity` returns the wallet itself, so every wallet gets its own cap |
| V12 | H3 | `TokenV12.sol` | `forcedTransfer` no longer calls `_tokenCompliance.transferred(...)` |

Specific design decisions:

- **V01 uses Mallory, not Bob.** Phase 2's example gave Bob only topic 1. But the handler's ground truth marks Bob as verified and Mallory as not. If Bob lacked topic 2 the tests would still call him verified and miss the bug. So in V01 two topics are required, Alice, Bob and Carol hold both, and **Mallory holds topic 1 only**.
- **V02 needs a fake claim that gets added.** `Identity.addClaim` requires the sender to be a claim-key holder (Mallory's wallet is the management key of her own identity) and then calls `isClaimValid` on the issuer, reverting with "invalid claim" if false. The stock issuer refuses a fake claim, but the V02 issuer accepts it. So in V02, Mallory adds a topic 1 claim signed by a random key (`keccak256("not-the-issuer")`).
- **V06 changed from the Phase 2 wording.** Phase 2 said "module uses the country stored at registration". The pinned module reads the country live, so that variant would be artificial. **Decision: Option B**, a copied registry whose `updateCountry` does nothing. Phase 2's J2 card already lists "variant registry ignores `updateCountry`". **Phase2.md section 7 row V06 must be updated** (see section 15).
- **V10 side effect.** The harness reads the module counter by identity, but V10 writes it by wallet. So G05a and G05b also fail on V10. These are real symptoms (the counter no longer matches), recorded as extra failures with this reason.
- **V12 needs a copied Token** because the stock token has no path that skips `transferred`.

### 7.4 Stock gaps S01 to S04 (no build needed)

| ID | Rule | Stock behaviour | Proven by |
|---|---|---|---|
| S01 | K4 | An expired claim is still accepted (`isClaimValid` has no expiry logic) | `StockGaps.t.sol` (passes as a "gap shown" test) and G11 (fails) |
| S02 | K5 | A sender whose claim was revoked can still send (`transfer` checks only `isVerified(_to)`) | `StockGaps.t.sol` and G12 (fails) |
| S03 | K2 | A revoked claim is revived when the investor re-adds it with the twin signature (`s' = n - s`, flipped `v`), because revocation is keyed by exact signature bytes | `StockGaps.t.sol` and G14 (fails) |
| S04 | K2 | A revoked claim is revived when the investor re-adds it with the same `r` and `s` but a different `v` byte (0/1 instead of 27/28), for the same reason: revocation is keyed by exact signature bytes. Added after Phase 4 step 4.8 | `StockGapsVByte.t.sol` (`test_S04` passes as a "gap shown" test). No gold test (G14 covers the twin-signature case only) |

S03 and S04 are gaps of the ONCHAINID dependency (2.1.0), not of T-REX code. S01 to S04 are **not** counted in the 13 variants or in the detection rate.

---

## 8. Final results table

Source: `results/all_variants.log` (variants, fresh fuzz, 145 tests: 109 passed, 36 failed) and `results/clean.log` (79 passed, 0 failed), parsed by `scripts/make_table.py` into `results/variant_table.md`.

`-` means that suite was not run for that configuration.

| config | G01a | G01b | G02a | G02b | G03a | G03b | G04 | G05a | G05b-prop | G05b-rec | G06a | G06b | G06c | G07 | G08 | G09 | G10 | G13 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | clean |
| C02 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | clean |
| C03 | PASS | PASS | - | - | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | - | - | - | - | clean |
| C04 | PASS | PASS | - | - | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | - | - | - | - | clean |
| C05 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | clean |
| C06 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | clean |
| C07 | PASS | PASS | - | - | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | - | - | - | - | clean |
| C08 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | clean |
| V01 | FAIL | FAIL | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V02 | FAIL | FAIL | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V03 | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V04 | FAIL | FAIL | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V05 | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | CAUGHT (linked) |
| V06 | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V07 | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | CAUGHT (linked) |
| V08 | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | CAUGHT (linked) |
| V09 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | CAUGHT (linked) |
| V10 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | CAUGHT (linked) |
| V11 | PASS | PASS | - | - | PASS | PASS | FAIL | FAIL | FAIL | - | - | - | - | - | - | - | - | - | CAUGHT (linked) |
| V12 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | CAUGHT (linked) |
| V13 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | CAUGHT (linked) |

### 8.1 Linked tests used by the script

A variant counts as caught when **at least one of its linked tests fails**. The links come from the Phase 2 plan, corrected after the Wave 1 results.

| Variant | Linked tests | Variant | Linked tests |
|---|---|---|---|
| V01 | G01a, G01b | V08 | G08, G03a |
| V02 | G01a, G01b | V09 | G04, G05a, G05b-prop |
| V03 | G06c | V10 | G09, G04 |
| V04 | G02a, G02b, G01a, G01b | V11 | G05a, G05b-prop, G04 |
| V05 | G03a, G03b, G08 | V12 | G05b-prop |
| V06 | G07 | V13 | G04, G09, G10 |
| V07 | G07, G08 | | |

### 8.2 What each variant actually failed

| Variant | Failed scenario tests | Failed property tests |
|---|---|---|
| V01 | G02b, G06c | G01a, G01b |
| V02 | G02b, G06c | G01a, G01b |
| V03 | G06c | G01a, G01b |
| V04 | G02a, G02b, G06b, G06c | G01a, G01b |
| V05 | G07, G08 ("policy country not restricted") | G03a, G03b |
| V06 | G07 | G03a, G03b |
| V07 | G07, G08 ("module not bound") | G03a, G03b |
| V08 | G07, G08 ("policy country not restricted") | G03a, G03b |
| V09 | G05b-rec, G09, G10 | G04, G05a, G05b |
| V10 | G05b-rec, G09 | G04, G05a, G05b |
| V11 | not run (no scenario suite) | G04, G05a, G05b |
| V12 | none | G04, G05a, G05b |
| V13 | G09, G10 | G04 |

---

## 9. How the detection rate was calculated

### 9.1 Definition

> **Detection rate = (reproducible seeded variants that fail at least one linked gold test) ÷ (reproducible seeded variants).**

A variant is **reproducible** if it fails at least one gold test of any kind. A variant that fails nothing would be marked "not reproducible" with a written reason, and would be removed from the denominator (as the project brief says). **No variant needed to be removed.**

### 9.2 Calculation

| Quantity | Value |
|---|---|
| Seeded variants built | 13 (V01 to V13) |
| Reproducible (fail at least one test) | 13 |
| Caught by a linked test | 13 |
| Caught by any test | 13 |
| Not caught | 0 |
| **Detection rate** | 13 ÷ 13 = **100%** (target: at least 75%) |

### 9.3 Stricter views (for the report, not the official number)

| View | Caught | Rate | Note |
|---|---|---|---|
| Property tests only | 13 of 13 | 100% | In this run, with this fuzz seed |
| Scenario tests only | 11 of 13 | 85% | V11 has no scenario suite, and V12 passes every scenario |

The scenario-only rate is a lower bound to quote honestly: **V12 is invisible to every fixed scenario test.**

### 9.4 Why this is not circular

The tests judge against **ground truth kept by the harness** (section 5.4), not against the broken contract's own answers. This is why V13 (cap set to the maximum) and V09 (module removed) are caught by G04 even though the module's own numbers look self-consistent.

---

## 10. How the false-positive rate was calculated

### 10.1 Definition

> **False-positive rate = (clean configurations on which any gold test G01 to G10 or G13 fails) ÷ (clean configurations).**

Clean configurations are correct setups. A failing gold test there would be a false alarm. G11, G12 and G14 are **excluded**, because they target stock gaps that fail on every configuration by design. Including them would make every clean setup look broken.

### 10.2 Calculation

| Quantity | Value |
|---|---|
| Clean configurations | 8 (C01 to C08) |
| Configurations with a failing gold test | 0 |
| **False-positive rate** | 0 ÷ 8 = **0%** (target: at most 15%) |

Source: `results/clean.log` ended with `16 test suites: 79 tests passed, 0 failed` at the close of Phase 3. **Update after Phase 4:** the same command now gives **80 tests passed, 0 failed**, because `StockGapsVByte.t.sol` (S04) adds one test. Nothing else changed. The false-positive rate stays 0 of 8.

### 10.3 How the 79 tests break down

| Group | Suites | Tests |
|---|---|---|
| Smoke | 1 | 1 |
| StockGaps | 1 | 4 |
| C01 baseline | 1 | 11 |
| Gold scenarios on C01 | 1 | 11 |
| Gold invariants on C01 | 1 | 1 (counted as one entry; contains 7 invariants) |
| Clean scenario suites (C02, C05, C06, C08) | 4 | 44 |
| Clean invariant suites (C02 to C08) | 7 | 7 (one each) |
| **Total at the close of Phase 3** | **16** | **79** |
| S04 (`StockGapsVByte.t.sol`, added after Phase 4) | +1 | +1 |
| **Total now** | | **80** |

Foundry 1.8.7 counts an invariant suite as one test entry. Counting each invariant separately gives 126 tests; the two figures describe the same tests.

### 10.4 Resolution of this measure

With only 8 clean configurations, **one** false alarm would be 12.5% (still within the 15% limit) and **two** would be 25% (over it). The clean set is small, so the margin is thin. A larger clean set would make the number more convincing.

### 10.5 What the clean set already caught

- The G13 flaw on C08 (section 6), which was a test bug.
- The D3 and D1/J4 traps (C03, C04), which stop a naive test from flagging expected behaviour.

---

## 11. Observations to record

### 11.1 About the contracts (T-REX 4.1.6)

1. **Vacuous passes:** empty required-topics list makes KYC pass for any registered wallet; zero modules bound makes `canTransfer` true for everything.
2. **Fail-closed:** an unconfigured `MaxBalanceModule` has cap 0 and blocks every non-zero transfer.
3. **`forcedTransfer`** skips `canTransfer` but still calls `transferred`. `MaxBalanceModule` catches it on the write side; `CountryRestrictModule` does not (empty hooks). It is a known exception (G13).
4. **Only the receiver is KYC-checked** in `transfer` and `transferFrom`. A holder who lost KYC can still send (S02).
5. **No expiry check** exists in `ClaimIssuer.isClaimValid` (S01).
6. **Revocation is keyed by exact signature bytes,** so the twin-signature trick revives a revoked claim (S03).
7. **Module state survives `removeModule`** (restricted countries, balances, preset flag stay under the compliance address).
8. **`mint` has different revert messages** from `transfer` ("Identity is not verified." / "Compliance not followed" against "Transfer not possible").
9. **`isVerified`, `updateCountry`, `isClaimValid`, `forcedTransfer` and `_getIdentity` are not `virtual`,** so variants must be full copies.

### 11.2 About the gold tests

1. **V12 is caught only by fuzzed properties.** No scenario test sees it. A fixed scenario for "`forcedTransfer` keeps tracked balance equal to real balance" would close the gap, but was not added because it would change the measured result.
2. **Detection depends on the fuzz seed and 64 runs.** G04 on V10 passed in one earlier run and failed (1076, then 1245 above the cap) in later runs. G09 catches V10 every time because it is a scenario with fixed amounts.
3. **V03's G01a and G01b failures** depend on the fuzzer finding "revoke, then send to the revoked identity". G06c is the reliable catch.
4. **V13 is caught by G04 alone among the properties.** G05a and G05b pass because the module's counters stay correct; only the cap is wrong. G09 and G10 also catch it.
5. **V05, V07 and V08 fail the same four tests.** The tests cannot tell them apart, but the G08 message differs: "module not bound" for V07, "policy country not restricted" for V05 and V08.
6. **G13 passes on every variant,** which is correct: it is the known-exception test.
7. **G05b appears twice** (property and recovery scenario). The table lists both columns; counts must not double-count it.
8. **Same author for gold tests and variants.** A risk of bias: the variants are the bugs the author thought of. Phase 5's independent evaluator and Phase 4's AI-written tests reduce this.

### 11.3 About the process

1. Every fixture change was verified by re-running the clean set (79 passed).
2. Variants were run only with prepared "should fail" tables. Surprises were written down, not hidden.
3. Replayed failures: Foundry stores failing invariant sequences in `cache/invariant/failures` and may replay them ("runs: 0, calls: 0" in the log). Delete `cache/invariant` before any final benchmark run so numbers come from a fresh fuzz.

---

## 12. Problems met and fixes

| # | Problem | Cause | Fix |
|---|---|---|---|
| 1 | Fuzzer overwrote the harness ground truth | Handler setup functions were fuzzable | Restrict to the test contract and `excludeSelector` (section 5.5) |
| 2 | G13 failed on C08 | Test assumed Carol starts at 0 | Compare against the starting balance |
| 3 | First "should fail" tables were incomplete | Secondary failures not predicted (e.g. V04 G06b/G06c) | Corrected tables before running; then matched exactly |
| 4 | Compile error: `variants/IdentityRegistryV01.sol` not found | Files were saved in `test/variants/`, not root `variants/` | Moved them with `mv`; imports (`../../variants/...`) then resolved |
| 5 | Log said "compilation skipped" and showed no V02/V03 | The edits were not saved yet | Re-saved; re-ran; log then listed V01, V02, V03, V06 |
| 6 | Compile error in `MaxBalanceModuleV10.sol`: "Documented parameter `_compliance` not found" | Stock `@param _compliance` doc comment stayed above a function whose parameter name was commented out | Replaced the doc block with a plain `//` comment |
| 7 | V10 prediction wrong for G04 in one run | Fuzzer did not reach the cap in that run | Recorded as a fuzz limit; later runs failed G04 |
| 8 | V06 as written in Phase 2 not reproducible | Stock module reads the country live | Option B (registry ignores `updateCountry`) |
| 9 | Stale invariant failures replayed | `cache/invariant` kept old failures | `rm -rf cache/invariant` before final runs |
| 10 | CRLF warnings and "can be restricted to view/pure" compiler warnings | Windows line endings; test functions | Harmless, no action |

---

## 13. How to reproduce

From the `ComplyRWA` folder (Git Bash):

```
# 1. Clean set must show 79 passed, 0 failed
forge test --no-match-contract GoldSpecial --no-match-path "test/variants/*" > results/clean.log 2>&1

# 2. Special set: G11, G12, G14 must all fail (stock gaps)
forge test --match-contract GoldSpecial > results/special.log 2>&1

# 3. Variants (delete stale failures first so the fuzz starts fresh)
rm -rf cache/invariant
forge test --match-path "test/variants/*" > results/all_variants.log 2>&1

# 4. Build the table
python scripts/make_table.py results/all_variants.log results/clean.log
```

Outputs: `results/variant_table.csv` and `results/variant_table.md`.

Expected numbers: 80 passed (clean; it was 79 at the close of Phase 3, S04 added one); 3 failed (special); 145 tests in the variant run (109 passed, 36 failed); 13 variants caught by a linked test; 8 clean configurations with 0 false positives.

**Per-wave counts (for cross-checking):** Wave 1 = 73 tests (6 scenario suites of 11 plus 7 invariant suites), Wave 2 = 72 tests (6 scenario suites of 11 plus 6 invariant suites). 73 + 72 = 145.

---

## 14. Limits of this phase

1. **Hand-written, not AI-generated.** These results measure the human answer key. They do not yet measure the AI pipeline (Phase 4).
2. **Fuzz-dependent.** Property detection uses a fixed seed and 64 runs. Another seed or more runs could change which property tests fail, though scenario results are fixed.
3. **13 variants chosen by the author.** They cover all three categories but are not an exhaustive bug list.
4. **Small clean set.** 8 configurations give a coarse false-positive rate (section 10.4).
5. **One pinned implementation.** Everything is tied to T-REX 4.1.6 and the three policy categories.
6. **Script output.** The script's printed summary was captured (section 15.1) and matches the numbers in sections 9 and 10.
7. **ONCHAINID version.** The version number of the installed dependency was still to be recorded in `environment.md` when Phase 2 closed; confirm it is there.

---

## 15. Status checklist and hand-off to Phase 4

### 15.1 Phase 3 checklist

- [x] Shared fixture with override hooks
- [x] 18 gold tests covering 13 rules (G01 to G14)
- [x] Handler with ground truth, fixed fuzz settings, setup functions excluded from fuzzing
- [x] 8 clean configurations, all passing
- [x] 13 seeded variants, all caught by a linked test
- [x] Stock gaps S01 to S03 confirmed (G11, G12, G14 fail on stock); S04 added after Phase 4 (`test_S04` passes)
- [x] Results table and script
- [x] Detection rate: 100% (target at least 75%)
- [x] False-positive rate: 0% (target at most 15%)
- [x] Final commit done
- [x] `Phase2.md` updated (V06 wording, V10 and V12 results, "V12 caught only by properties", fixed fuzz seed and 64 runs)
- [x] Script output confirmed (below)

**Script output (`python scripts/make_table.py results/all_variants.log results/clean.log`):**

```
Seeded variants found: 13
  caught by a linked test: 13
  caught by any test:      13
  not caught:              0
  detection rate (linked): 100%
Clean configs found: 8
  with a failing gold test: 0  -> false-positive rate 0%
Wrote results/variant_table.csv and results/variant_table.md
```

### 15.2 Commits known so far

| Step | Commit |
|---|---|
| Step 2 (gold tests on C01) | `abe4ce9` |
| Step 3 (clean configurations C02 to C08) | `ab9d678` |
| Steps 4 and 5 (variants, table) | commit messages used: "Phase 3 step 4a: fixture helpers", "step 4b: Wave 1 variants", "step 4c: Wave 2 variants V01 and V06", "V02 and V03", "V10", "V12" (hashes not recorded here) |

### 15.3 What Phase 4 can reuse

| Phase 3 asset | Use in Phase 4 |
|---|---|
| Gold tests G01 to G10 | Answer key to score LLM-generated invariants (valid and non-vacuous) |
| Clean configs C01 to C08 | Validity filter: a generated test that fails on clean is rejected |
| Variants V01 to V13 | Executor target: run each surviving generated test on each variant |
| `make_table.py` and table format | Same table for the three-way benchmark (generated vs plain Foundry vs LLM-only review) |
| Handler ground-truth idea | Template for the "judge against the policy" rule the generator must follow |
| Fixture hooks | Generated tests can inherit `ComplyFixture` and run on any variant unchanged |

### 15.4 Decisions still needed for Phase 4

1. Which LLM and access (for example the Anthropic API) and how token cost is recorded.
2. CLI or web as the first interface (Phase 5 needs one of them).
3. Pipeline language (Python is the working assumption).
4. The current `foundry.toml`, so generated tests use the same remappings and fuzz settings.