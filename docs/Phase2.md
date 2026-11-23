# ComplyRWA: Phase 2 Policy Catalogue (Scope)

**Goal of Phase 2:** fix exactly what ComplyRWA will check, so Phases 3 and 4 have a stable target.

**Scope:** 3 policy categories, 3-5 rules per category (13 rules total).

| Category | Pinned component | Rules |
|---|---|---|
| KYC | IdentityRegistry (and the registries behind it) | K1 to K5 |
| Jurisdiction | CountryRestrictModule | J1 to J4 |
| Holding limit | MaxBalanceModule | H1 to H4 |

Pinned system: T-REX tag `4.1.6`, Solidity 0.8.17.
Commit hash: `a09cfd38aa257d56db7ff9c90f30e65f125a141b` (`a09cfd3`, "Compliance modules fixes & improvements (#228)").

> **How to read the examples.** Every example is a *planned* case, written from the Phase 1 notes. None of them has been run yet. They become real in Phase 3, when each one is turned into a seeded vulnerable variant and a Foundry test. Where an example depends on something not yet confirmed in the pinned version, it is marked **(verify)**.

---

## 1. Common test setup (used by all examples)

So every example is short, they all use the same cast and settings.

| Item | Value |
|---|---|
| Token | Unpaused (a fresh T-REX token starts paused, so the fixture must call `unpause()`) |
| Required claim topic | Topic `1` (KYC claim) |
| Trusted issuer | `IssuerX` (trusted for topic 1) |
| Alice | Wallet `A1`, identity `ID_A`, country `356` (India), holds valid KYC claim from IssuerX |
| Alice's second wallet | `A2`, also under `ID_A` |
| Bob | Wallet `B`, identity `ID_B`, country `356`, holds valid KYC claim from IssuerX |
| Carol | Wallet `C`, identity `ID_C`, country `408` (restricted), holds valid KYC claim from IssuerX |
| Mallory | Wallet `M`, registered in the registry but **no** valid claim |
| Compliance modules (clean config) | `CountryRestrictModule` (restricted: `408`) and `MaxBalanceModule` (max `1000`) |
| Revert message | `transfer`, `transferFrom` and `forcedTransfer` revert with `"Transfer not possible"` for both KYC and compliance failures. `mint` is different: it reverts with `"Identity is not verified."` (KYC) or `"Compliance not followed"` (rules) (confirmed on pinned `Token.sol`) |

**Reading the "Result" lines:**
- **Policy expects** = what the issuer's rule says should happen.
- **Broken config gives** = what actually happens in the vulnerable variant.
- A **finding** is raised when these two differ.

---

## 2. Decisions that change how rules are judged

Four decisions from Phase 1 still need your sign-off. The proposals are my suggestion, not final.

| # | Decision | Proposal | Affects |
|---|---|---|---|
| D1 | Is `forcedTransfer` always exempt, or judged per module? | **Per module and per policy.** Skips `canTransfer` (read side) but still hits `transferred` (write side). MaxBalance catches it; CountryRestrict does not | J1, J4, H1 |
| D2 | Are sender-side checks in scope (K5, sender country)? | **K5 in scope as "intentionally violated by stock config".** Sender-country listed as an issuer policy choice, not a default | K5 |
| D3 | Same-identity move (600 held, cap 1000, move 500 between `A1` and `A2`): "rejected" or "should pass"? | **Expected = rejected** (matches stock `moduleCheck`). The auditor does not report it as a bug. Recorded as a known false-positive trap | H2 |
| D4 | Is K4 (expired KYC) a real finding? | **Yes, in scope**, flagged as a known gap of stock T-REX rather than a code bug | K4 |

---

## 3. Rule cards

Each card has the same fields:
ID, Plain-English rule, Paths covered, Contracts involved, Testable form, Known exceptions, How it could break, **Example**, plus a Status line (does the stock config satisfy the rule?).

**Status legend**
- **Holds on stock:** a correctly configured stock T-REX satisfies the rule. Findings come from bad configuration.
- **Violated by stock:** stock T-REX does not enforce it. A finding is expected unless the issuer adds extra logic.

---

### KYC rules

#### K1: Only fully verified investors can receive

| Field | Value |
|---|---|
| **ID** | K1 |
| **Plain-English rule** | A wallet may receive tokens only if it holds a valid claim for **every** required topic, signed by a **trusted** issuer. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint`, and `forcedTransfer` (it still calls `isVerified(_to)`) |
| **Contracts involved** | Token, IdentityRegistry, IdentityRegistryStorage, ClaimTopicsRegistry, TrustedIssuersRegistry, Identity (ONCHAINID), ClaimIssuer |
| **Testable form** | After any covered call succeeds, `identityRegistry.isVerified(receiver) == true`. Equivalent: if `isVerified(receiver) == false`, the call reverts and balances are unchanged. |
| **Known exceptions** | None for receivers. Senders are not checked (see K5). |
| **How it could break** | `isVerified` logic changed to OR across topics instead of AND. A claim from an untrusted issuer is accepted. Mock ClaimIssuer whose `isClaimValid` always returns true. A forged identity contract that returns an attacker-chosen issuer (agent-gated registration, so a trust assumption; worth a test). |
| **Status** | Holds on stock |

**Example: OR instead of AND across topics**

| Step | Detail |
|---|---|
| Setup | Required topics are `1` (KYC) and `2` (accreditation). Bob holds a valid claim for topic 1 only. Variant registry loops over topics and returns true as soon as **one** topic is satisfied. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert `"Transfer not possible"` (Bob has no accreditation claim) |
| Broken config gives | Transfer **succeeds**. `balanceOf(B)` goes from 0 to 100 |
| Finding | K1 violated: a receiver missing a required claim got tokens |

---

#### K2: Revocation must block receiving

| Field | Value |
|---|---|
| **ID** | K2 |
| **Plain-English rule** | If an investor's KYC is revoked, the wallet can no longer **receive** tokens. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint`, `forcedTransfer` (receiver side) |
| **Contracts involved** | Token, IdentityRegistry, IdentityRegistryStorage, TrustedIssuersRegistry, ClaimIssuer |
| **Testable form** | For each revocation route below, after revocation `isVerified(receiver) == false` and a transfer to that receiver reverts. Routes: (a) `deleteIdentity`, (b) trusted issuer removed (and no other trusted issuer holds a claim for the investor), (c) claim revoked at the ClaimIssuer. |
| **Known exceptions** | Revocation does **not** stop the wallet from sending tokens it already holds (see K5). Removing a required topic is **not** a revocation route; see the note under K3. |
| **How it could break** | Variant `isVerified` caches a previous "true" result. Variant ClaimIssuer ignores `revokedClaims`. Variant registry keeps the old identity after `deleteIdentity`. |
| **Status** | Holds on stock for the three routes. **Two bypasses found by test: S03** (investor re-adds a revoked claim with a twin signature) **and S04** (same, with a different `v` byte) |

**Example: revoked claim still accepted**

| Step | Detail |
|---|---|
| Setup | Bob's claim is revoked at IssuerX (`revokeClaim`). Variant ClaimIssuer's `isClaimValid` skips the `revokedClaims` check. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds** |
| Finding | K2 violated: revocation had no effect on receiving |

---

> **K2 bypass S04 (added after Phase 4 step 4.8).** Same idea as S03, but the signature is changed in the `v` byte instead of `s`: `v` as 0/1 instead of 27/28. `revokedClaims` is keyed by the exact signature bytes, so the changed signature is not found there and `isClaimValid` accepts it again. Reproduced on the project owner's machine (`test/StockGapsVByte.t.sol`, `test_S04` passes). Like S03, it is a gap of the ONCHAINID dependency (2.1.0), not of T-REX code. It is not part of the 13 variants or the detection rate.

> **K2 bypass reproduced in a test (S03).** An investor can undo a revocation by re-adding the claim with a twin signature. See section 5a (note after item 12). Reproduced in a sandbox run; re-run on your machine to confirm (`test/StockGaps.t.sol`).

#### K3: Required claim topics list must not be empty

| Field | Value |
|---|---|
| **ID** | K3 |
| **Plain-English rule** | The issuer must require at least one claim topic, so that "verified" actually means something. |
| **Paths covered** | All receiving paths (`transfer`, `transferFrom`, `batchTransfer`, `mint`, `forcedTransfer`) |
| **Contracts involved** | IdentityRegistry, ClaimTopicsRegistry |
| **Testable form** | `claimTopicsRegistry.getClaimTopics().length > 0`. Companion test: with the list empty, Mallory (registered, no claim) can receive, which proves K1 would be vacuous. |
| **Known exceptions** | None. An empty list is allowed by the code, but it makes K1 pass for every registered wallet. |
| **How it could break** | Deployment script forgets `addClaimTopic`. A topic is removed later. |
| **Status** | Holds on stock **only if** the issuer adds a topic (configuration check) |

**Example: empty topic list**

| Step | Detail |
|---|---|
| Setup | `ClaimTopicsRegistry` has no topics. Mallory is registered but has no claim. |
| Action | Alice calls `transfer(M, 100)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds**. `isVerified(M)` returns `true` because the topic list is empty |
| Finding | K3 violated, and K1 is vacuously "true" |

> **Note on topic removal (Phase 1 conflict, resolved).** Your Phase 1 notes listed "remove the topic" as a route that should make `isVerified` return false. That looks backwards: removing a required topic means the receiver needs **fewer** claims, so verification gets **easier**, and removing the last topic makes the list empty. Topic removal is therefore handled here under K3, not K2. **Decision: confirmed by project owner.**

---

#### K4 (optional): Expired KYC must not be accepted

| Field | Value |
|---|---|
| **ID** | K4 |
| **Plain-English rule** | A KYC claim past its expiry date must not let a wallet receive tokens. |
| **Paths covered** | All receiving paths |
| **Contracts involved** | IdentityRegistry, Identity (ONCHAINID), ClaimIssuer |
| **Testable form** | Issue a claim whose `data` encodes an expiry date in the past. After that date, a transfer to the holder must revert. |
| **Known exceptions** | Stock `ClaimIssuer.isClaimValid` checks only the signer key (purpose 3) and `revokedClaims`. Expiry would have to be inside the opaque `data` and enforced off-chain. |
| **How it could break** | Stock behaviour itself: nothing on-chain reads an expiry. |
| **Status** | **Violated by stock. Confirmed** on the `ClaimIssuer.sol` from the installed dependency (version number still to be recorded) |

**Example: expired claim still accepted**

| Step | Detail |
|---|---|
| Setup | Bob's claim `data` says "valid until 2025-01-01". Current block time is 2026. Claim is not revoked. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert `"Transfer not possible"` (KYC expired) |
| Stock config gives | Transfer **succeeds** |
| Finding | K4 violated. Report as a gap of stock T-REX, with a suggestion to add expiry handling in a custom ClaimIssuer or module |

---

#### K5 (optional): A sender who lost KYC cannot send

| Field | Value |
|---|---|
| **ID** | K5 |
| **Plain-English rule** | A wallet whose KYC was revoked must not be able to move its tokens out. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer` (sender side) |
| **Contracts involved** | Token, IdentityRegistry |
| **Testable form** | After the sender's KYC is revoked, `transfer` from that sender reverts. |
| **Known exceptions** | `forcedTransfer` and `burn` by an agent. Also, with MaxBalanceModule bound, a **deleted** identity cannot send (`_getIdentity` reverts), but a **revoked claim** alone can. |
| **How it could break** | Stock behaviour: `Token.transfer` calls `isVerified(_to)` only, never on `msg.sender`. |
| **Status** | **Violated by stock** (an issuer policy choice, see D2). **Confirmed on pinned `Token.sol`:** `transfer` and `transferFrom` call `isVerified(_to)` only |

**Example: revoked holder still sends**

| Step | Detail |
|---|---|
| Setup | Alice holds 500 tokens. Her claim is revoked at IssuerX. Her identity is **not** deleted. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert (sender no longer verified) |
| Stock config gives | Transfer **succeeds**. `balanceOf(B)` goes to 100 |
| Finding | K5 violated. Report as a policy gap and suggest a sender check or an agent freeze |

---

### Jurisdiction rules

#### J1: No receiving in a restricted country

| Field | Value |
|---|---|
| **ID** | J1 |
| **Plain-English rule** | Wallets registered in a restricted country must not receive tokens. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint` (all call `canTransfer`) |
| **Contracts involved** | Token, ModularCompliance, CountryRestrictModule, IdentityRegistry, IdentityRegistryStorage |
| **Testable form** | After any covered call succeeds, `investorCountry(receiver)` is not in the restricted list. |
| **Known exceptions** | `forcedTransfer` (see J4). Senders' countries are not checked. |
| **How it could break** | Module removed from `getModules()`. Wrong country code stored (e.g. `410` instead of `408`). Restriction added to a different compliance contract. Batch call that reverted, leaving the list empty. |
| **Status** | Holds on stock when configured correctly |

**Example: wrong country code**

| Step | Detail |
|---|---|
| Setup | Policy: "no investors from country 408". Admin restricted `410` by mistake. Carol's wallet `C` is registered with country `408`. |
| Action | Alice calls `transfer(C, 100)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds** |
| Finding | J1 violated: configuration does not match the written policy |

---

#### J2: A country change to a restricted one blocks future receiving

| Field | Value |
|---|---|
| **ID** | J2 |
| **Plain-English rule** | If a wallet's country is updated to a restricted country, it can no longer receive tokens. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint` |
| **Contracts involved** | IdentityRegistry (`updateCountry`), IdentityRegistryStorage, CountryRestrictModule |
| **Testable form** | After `updateCountry(wallet, 408)`, a transfer to that wallet reverts. |
| **Known exceptions** | Existing balances are **not** moved. Only future receipts are blocked. A wallet that moved to a restricted country can still **send**. |
| **How it could break** | Variant module reads a country cached at registration time. Variant registry ignores `updateCountry`. |
| **Status** | Holds on stock (the module reads `investorCountry` live) |

**Example: stale country**

| Step | Detail |
|---|---|
| Setup | Bob registered with country `356`. Agent calls `updateCountry(B, 408)`. Variant module still uses the country from registration. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds** |
| Finding | J2 violated: country change not respected |

---

#### J3: The country module must be bound and configured

| Field | Value |
|---|---|
| **ID** | J3 |
| **Plain-English rule** | A country restriction policy is only real if the module is actually bound to the compliance contract **and** has the right countries set. |
| **Paths covered** | All paths that call `canTransfer` |
| **Contracts involved** | ModularCompliance (`getModules`), CountryRestrictModule |
| **Testable form** | (a) `getModules()` contains the CountryRestrictModule and `isModuleBound(module)` returns true. (b) The module's restricted list matches the issuer's policy. Use `getModules()` as the source of truth, not the module's own `complianceBound` flag, because any contract can mark itself bound in a module. |
| **Known exceptions** | None |
| **How it could break** | Module never added. Module removed with `removeModule` (rule silently disappears). Module added but no country ever restricted (empty list restricts nobody). Zero modules bound, so `canTransfer` returns true for everything. |
| **Status** | Holds on stock when set up correctly |

**Example: module removed**

| Step | Detail |
|---|---|
| Setup | Clean config had CountryRestrictModule with `408` restricted. Owner calls `removeModule`. |
| Action | Alice calls `transfer(C, 100)` (Carol is in country 408) |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds**. Token still deploys and works normally |
| Finding | J3 violated: the rule exists only on paper |

---

#### J4: `forcedTransfer` to a restricted country must be classified, not blindly reported

| Field | Value |
|---|---|
| **ID** | J4 |
| **Plain-English rule** | An agent's `forcedTransfer` to a restricted country is a known exception. The auditor must label it clearly instead of reporting it as an ordinary bypass. |
| **Paths covered** | `forcedTransfer` |
| **Contracts involved** | Token, ModularCompliance, CountryRestrictModule |
| **Testable form** | Call `forcedTransfer(A1, C, amount)` as an agent. Expect success, and expect the report to mark it **"Known exception: agent-only path"**, not "vulnerability". |
| **Known exceptions** | This rule **is** the exception rule (see D1). |
| **How it could break** | Stock behaviour: `forcedTransfer` skips `canTransfer`, and CountryRestrictModule's write hooks are empty, so nothing stops it. The *auditor* breaks if it reports this as a plain J1 failure (a false positive). |
| **Status** | Violated by stock (by design). **Confirmed** on pinned `Token.sol` and `CountryRestrictModule.sol` |

**Example: forced transfer to a restricted country**

| Step | Detail |
|---|---|
| Setup | Clean config. Alice holds 500 tokens. |
| Action | Agent calls `forcedTransfer(A1, C, 100)` (Carol in country 408) |
| Policy expects | Allowed as an agent exception (court order or recovery) |
| Stock config gives | Transfer **succeeds**, `balanceOf(C)` is 100 |
| Correct audit output | `INFO: J1 bypassed via forcedTransfer (agent-only). Classified as known exception.` |
| Wrong audit output | `HIGH: jurisdiction bypass` (counts as a false positive) |

---

### Holding-limit rules

#### H1: No identity may exceed the maximum

| Field | Value |
|---|---|
| **ID** | H1 |
| **Plain-English rule** | No investor identity may hold more than the configured maximum after a transfer or mint. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint`, and `forcedTransfer` (caught by the write-side check in `moduleTransferAction`) |
| **Contracts involved** | Token, ModularCompliance, MaxBalanceModule |
| **Testable form** | After any covered call, `getIDBalance(compliance, id) <= maxBalance` for every identity. |
| **Known exceptions** | `burn` only reduces balances, so it cannot break the limit. |
| **How it could break** | MaxBalanceModule removed from the module list. `moduleCheck` comparison changed (`>` to `>=` or the reverse). `moduleTransferAction` limit re-check removed. Limit set to `type(uint256).max` (see H4). |
| **Status** | Holds on stock when configured correctly |

**Example: module removed, cap ignored**

| Step | Detail |
|---|---|
| Setup | Cap is 1000. Bob holds 900. MaxBalanceModule has been removed from the compliance contract. |
| Action | Alice calls `transfer(B, 200)` |
| Policy expects | Revert `"Transfer not possible"` (Bob would hold 1100) |
| Broken config gives | Transfer **succeeds**. `balanceOf(B)` is 1100 |
| Finding | H1 violated |

---

#### H2: The cap is per identity, not per wallet

| Field | Value |
|---|---|
| **ID** | H2 |
| **Plain-English rule** | Two wallets under the same identity share one cap. |
| **Paths covered** | `transfer`, `transferFrom`, `batchTransfer`, `mint` |
| **Contracts involved** | MaxBalanceModule, Token, IdentityRegistry (`identity(wallet)`) |
| **Testable form** | With `A1` and `A2` under `ID_A`: `balanceOf(A1) + balanceOf(A2) <= maxBalance` after any covered call. |
| **Known exceptions** | A second wallet registered under a **different** identity doubles the cap. This is an issuer-process matter, **out of scope**. Same-identity moves are decided by D3. |
| **How it could break** | Variant module keyed by wallet instead of identity. Variant `_getIdentity` returns the wallet address. |
| **Status** | Holds on stock |

**Example: cap checked per wallet**

| Step | Detail |
|---|---|
| Setup | Cap 1000. `A1` holds 600 and `A2` holds 0, both under `ID_A`. Variant module keys balances by wallet. |
| Action | Bob calls `transfer(A2, 600)` |
| Policy expects | Revert (Alice's identity would hold 1200) |
| Broken config gives | Transfer **succeeds**. Combined balance for `ID_A` is 1200 |
| Finding | H2 violated |

**Known false-positive trap (D3):** `A1` holds 600 and moves 500 to `A2`. Stock `moduleCheck` computes 600 + 500 > 1000 and **rejects** it, although the net change is zero. A naive invariant "any transfer that stays under the limit must succeed" would wrongly flag this. The auditor must treat the rejection as expected.

---

#### H3: Tracked balance must equal the real balance (counter drift)

| Field | Value |
|---|---|
| **ID** | H3 |
| **Plain-English rule** | The module's own balance record for an identity must match the real token balances of that identity's wallets. |
| **Paths covered** | All paths that change balances: `transfer`, `transferFrom`, `mint`, `burn`, `forcedTransfer`, `recoveryAddress` |
| **Contracts involved** | MaxBalanceModule (`getIDBalance`, `preSetModuleState`), Token, ModularCompliance |
| **Testable form** | For every identity: `getIDBalance(compliance, id) == sum of balanceOf(w)` over the wallets `w` of that identity. |
| **Known exceptions** | Nothing in the code verifies preset values, so a wrong preset is a configuration finding, not a code bug. |
| **How it could break** | Preset value too low (via `batchPreSetModuleState`). `presetCompleted()` called with nothing preset: it sets the preset flag with no check that any balances were loaded, so the module can be bound to a token that already has holders. Module removed and re-added, leaving stale state under the compliance key. A balance-changing path that skips `transferred`, `created` or `destroyed` (the stock `Token` has none, so this needs a variant `Token`). |
| **Status** | Holds on stock unless the preset or module history is wrong |

**Example: preset too low**

| Step | Detail |
|---|---|
| Setup | Bob already holds 800 tokens. Owner calls `batchPreSetModuleState(compliance, [ID_B], [0])` (this also sets the preset flag), then `addModule`. Cap is 1000. |
| Action | Alice calls `transfer(B, 500)` |
| Policy expects | Revert (Bob would hold 1300) |
| Broken config gives | Transfer **succeeds**. Tracked balance is 500, real balance is 1300 |
| Finding | H3 violated, and it makes the cap in H1 bypassable |

---

#### H4: The maximum must be configured sensibly

| Field | Value |
|---|---|
| **ID** | H4 |
| **Plain-English rule** | The cap must match the issuer's intended number. It must not be 0 (blocks everything) or `type(uint256).max` (no limit). |
| **Paths covered** | All paths that call `canTransfer` |
| **Contracts involved** | MaxBalanceModule (`setMaxBalance`), ModularCompliance (`callModuleFunction`) |
| **Testable form** | `0 < maxBalance < type(uint256).max`, and `maxBalance` equals the number in the issuer's policy text. |
| **Known exceptions** | None |
| **How it could break** | `setMaxBalance` never called (max is 0, every non-zero transfer is blocked, fail-closed). `setMaxBalance(type(uint256).max)` (limit effectively off). Wrong number or wrong units (decimals). |
| **Status** | Holds on stock when configured correctly |

**Example: limit disabled**

| Step | Detail |
|---|---|
| Setup | Policy: "no investor may hold more than 1000 tokens". Owner calls `callModuleFunction` to run `setMaxBalance(type(uint256).max)`. |
| Action | Alice calls `transfer(B, 5000)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds** |
| Finding | H4 violated |

**Fail-closed variant:** `setMaxBalance` never called. A transfer of 1 token reverts. This is an availability problem rather than a bypass, so the report should mark it **"Medium: token unusable"**, not "bypass".

---

## 4. Summary table

| ID | Category | Rule (short) | Status on stock | Main break type |
|---|---|---|---|---|
| K1 | KYC | Only fully verified receivers | Holds | Wrong verification logic |
| K2 | KYC | Revocation blocks receiving | Holds (bypasses S03, S04) | Revocation ignored, twin signature, v-byte variant |
| K3 | KYC | Topics list not empty | Config check | Empty list |
| K4 | KYC | Expired KYC rejected | **Violated** | No on-chain expiry |
| K5 | KYC | Revoked sender cannot send | **Violated** | Sender never checked |
| J1 | Jurisdiction | No restricted-country receivers | Holds | Wrong country code, removed module |
| J2 | Jurisdiction | Country change respected | Holds | Stale country |
| J3 | Jurisdiction | Module bound and configured | Config check | Module missing or empty |
| J4 | Jurisdiction | `forcedTransfer` classified | By design | Auditor false positive |
| H1 | Holding limit | Cap not exceeded | Holds | Module removed, bad comparison |
| H2 | Holding limit | Cap per identity | Holds | Keyed by wallet |
| H3 | Holding limit | Counters match balances | Holds | Bad preset, drift |
| H4 | Holding limit | Cap set sensibly | Config check | 0 or max value |

**Count check against clearance criteria:** 13 rules give enough room for **at least 8** executable invariants and **12-15** seeded variants (one per example above, plus extras).

---

## 5. Verification plan against the pinned commit

Phase 1 checked some files against GitHub `main`, not against the pinned commit `a09cfd3`. That commit's message ("Compliance modules fixes & improvements") also suggests the compliance modules may differ from `main`. So the claims below must be re-checked on the exact pinned files.

| # | What to confirm | Rule / decision it affects | File to read (pinned) |
|---|---|---|---|
| 1 | `transfer` and `transferFrom` call `isVerified` on the receiver only | K5, D2 | `T-REX/contracts/token/Token.sol` |
| 2 | `forcedTransfer` skips `canTransfer` but still calls `transferred` | D1, J4, H1 | `T-REX/contracts/token/Token.sol` |
| 3 | `moduleCheck` logic and the write-side limit check | D1, D3, H1 to H4 | `.../compliance/modular/modules/MaxBalanceModule.sol` |
| 4 | Empty write hooks, receiver-only country check | D1, J1, J4 | `.../compliance/modular/modules/CountryRestrictModule.sol` |
| 5 | `isVerified` logic (AND across topics, OR across issuers, empty topic list) | K1, K2, K3 | `T-REX/contracts/registry/implementation/IdentityRegistry.sol` |
| 6 | Whether `isClaimValid` checks any expiry | K4, D4 | `T-REX/node_modules/@onchain-id/solidity/contracts/ClaimIssuer.sol` |
| 7 | What `onlyComplianceCall` and `bindCompliance` really check | J3 (use `getModules()` as source of truth) | `AbstractModuleUpgradeable.sol` (and `AbstractModule.sol` if present) |

Commands to find and read the files (Git Bash, from the `ComplyRWA` folder):

```
# K4: which ONCHAINID version is installed, and any expiry logic
grep -n "@onchain-id" T-REX/package.json
grep '"version"' T-REX/node_modules/@onchain-id/solidity/package.json
grep -rniE "expir|validTo|validUntil|block.timestamp" T-REX/node_modules/@onchain-id/solidity/contracts T-REX/contracts/registry

# onlyComplianceCall: find the abstract module files and the key lines
find T-REX/contracts/compliance -name "AbstractModule*"
grep -rn "onlyComplianceCall\|complianceBound\|function bindCompliance" T-REX/contracts/compliance/modular
```

Reading the source is step one. In Phase 3, each confirmed claim also becomes a small Foundry test, so the result is proven by running code and not only by reading it.

---

## 5a. Findings from the pinned files (7 of 7 checked)

Checked against the pinned commit `a09cfd3`: `Token.sol`, `IdentityRegistry.sol`, `ModularCompliance.sol`, `MaxBalanceModule.sol`, `CountryRestrictModule.sol`, `AbstractModuleUpgradeable.sol`, and `ClaimIssuer.sol` (from the installed ONCHAINID dependency; its version number is not recorded yet).

| # | Claim | Result | Evidence in the pinned code |
|---|---|---|---|
| 1 | `transfer` and `transferFrom` check KYC on the receiver only | **Confirmed** | Both call `isVerified(_to)`. Nothing calls it on the sender |
| 2 | `forcedTransfer` skips `canTransfer` but still calls `transferred` | **Confirmed** | It requires only `isVerified(_to)`, then `_transfer` and `transferred` |
| 3 | MaxBalance `moduleCheck` and write-side guard | **Confirmed** | `moduleCheck` uses `>` and ignores `_from`. `moduleTransferAction` and `moduleMintAction` revert with `MaxBalanceExceeded` if the receiver ends above the cap. Unconfigured max is 0, so every non-zero transfer is blocked |
| 5 | `isVerified` logic | **Confirmed** | AND across topics, OR across issuers. Empty topic list returns true. No trusted issuer for a topic returns false. The `issuer` used comes from `getClaim`, not from the trusted list |
| 4 | CountryRestrictModule hooks | **Confirmed** | `moduleTransferAction`, `moduleMintAction` and `moduleBurnAction` have empty bodies (only `onlyComplianceCall`). `moduleCheck` looks only at the receiver's country and ignores `_from` and the amount. Country is read live from the registry on every check. `canComplianceBind` and `isPlugAndPlay` both return true |
| 6 | `ClaimIssuer` expiry | **Confirmed** | `isClaimValid` only checks that the recovered signer's key has purpose 3 and that the signature is not in `revokedClaims`. No timestamp or expiry logic anywhere in the path (registry or issuer) |
| 7 | `onlyComplianceCall` / `bindCompliance` | **Confirmed** | `onlyComplianceCall` checks `complianceBound[msg.sender]` in the module's own storage. `bindCompliance(_compliance)` only requires `msg.sender == _compliance`, so any contract can mark itself bound. State is keyed by `msg.sender`, so this is harmless to other compliance contracts, but "bound in the module" does not prove "listed in a real ModularCompliance". Use `getModules()` and `isModuleBound` as the source of truth |

**Corrections to earlier notes (from the pinned code)**

1. **`mint` uses different revert messages** from `transfer`. KYC failure gives `"Identity is not verified."` and a rule failure gives `"Compliance not followed"`. The "same message for both" observation holds only for `transfer`, `transferFrom` and `forcedTransfer`. The Counterexample Explainer can read the reason string for mint.
2. **Preset functions behave differently.** `preSetModuleState` (single) does not set the preset flag. `batchPreSetModuleState` and `presetCompleted` do. `presetCompleted` has **no** "module not yet bound" check, and it does not check that any balances were preset. This gives an easy H3 variant.
3. **`canComplianceBind`** (MaxBalance) returns true if the preset flag is set, otherwise it reads the bound token's `totalSupply`. If no token is bound yet and no preset is set, that call should revert (inferred from the code; test it in Phase 3). Fixture rule: bind the token to the compliance before adding MaxBalanceModule.
4. **`bindToken`** lets the token bind itself only while no token is bound. The owner can always bind.
5. **`forcedTransfer`, `mint` and `burn` are not `whenNotPaused`.** A paused token still allows these agent paths. Not one of the 13 rules, but worth a line in the audit report.
6. **`ModularCompliance.isModuleBound(module)` exists.** Use it with `getModules()` for the J3 test.
7. **Same-identity moves (D3):** `moduleCheck` rejects `A1` to `A2` (600 held, move 500, cap 1000) because it adds 600 + 500. But an agent `forcedTransfer` of the same amount succeeds, because `moduleTransferAction` adds then subtracts for the same identity (net zero).
8. **`forcedTransfer` to a restricted country (D1, J4) is confirmed.** `Token.forcedTransfer` skips `canTransfer`, and the three `CountryRestrictModule` write hooks are empty, so nothing stops it. `MaxBalanceModule` is different: its write hook reverts.
9. **Module state survives `removeModule`.** `unbindCompliance` only flips the `complianceBound` flag. Restricted countries, `_IDBalance` and the preset flag stay stored under the compliance address. A module removed and re-added picks up the old state. Useful for H3 and J3 tests.
10. **Modules are UUPS upgradeable and need `initialize()`.** `AbstractModuleUpgradeable` is `UUPSUpgradeable` with `_authorizeUpgrade` restricted to the module owner. Fixture rule: deploy each module behind a proxy and call `initialize()`. Check how T-REX's own Hardhat test fixtures do this before copying the pattern. An un-initialized module would let the first caller become its owner. That is a deployment-trust matter, out of scope as a finding.
11. **`ClaimIssuer` revocation is keyed by the raw signature bytes** (`revokedClaims[sig]`). Two consequences for the tests:
    - A revoked claim cannot simply be "re-issued" with identical data. A deterministic signer produces the same signature, which is still revoked. **C06 must re-issue with different `data`.**
    - In Foundry, sign the exact `prefixedHash` that `isClaimValid` builds (`"\x19Ethereum Signed Message:\n32"` plus the data hash) with `vm.sign`. Do not add a second prefix.
12. **`ClaimIssuer` is deployed directly.** Its constructor passes `isLibrary = false` to `Identity`, so a normal `new ClaimIssuer(managementKey)` works. The signer key needs purpose 3 (added with `addKey`).

**Candidate finding, now reproduced in a test (S03).** Because `getRecoveredAddress` does not enforce a low-`s` signature, and `revokedClaims` is keyed by exact signature bytes, an investor who controls their own ONCHAINID might re-add the same claim with the "twin" signature (same signer, different bytes). That twin would not be in `revokedClaims`, so a revoked claim could pass `isClaimValid` again. This depends on how `Identity.addClaim` behaves, and I have not seen that file. Treat it as a hypothesis for a Phase 3 Foundry test (possible extra stock-gap case under K2), not as a finding. Reading `Identity.addClaim` (ONCHAINID 2.1.0) supports it: it only requires `isClaimValid` to return true for the new signature, and it overwrites the stored claim. A Foundry test (`test_S03_revokedClaimRevivedByTwinSignature`) revoked Bob's claim, confirmed receiving was blocked, then had Bob re-add the claim with the twin signature, and Bob could receive again. This was run in a sandbox with Foundry 1.2.3 and the pinned T-REX; it still needs to be re-run on your machine. Treat it as a stock gap of the ONCHAINID dependency, not of T-REX code.

---

## 6. Default audit input (demo set)

The tool accepts 3-5 rules per audit. The default demo uses **5 rules that cover all 3 categories**:

| Rule | Category | Why it is in the demo |
|---|---|---|
| **K1** | KYC | The clearest rule, and the issue text's own example ("only KYC-verified investors") |
| **K3** | KYC | Vivid bug: nothing looks wrong, yet an empty topic list makes K1 pass for everyone |
| **J1** | Jurisdiction | The second half of the issue text's example ("approved jurisdictions"). Also catches a removed module or a wrong country code |
| **H1** | Holding limit | The clearest holding-limit rule |
| **H3** | Holding limit | Stateful counter drift. Hard for a plain checklist or an LLM-only review, so it shows what generated properties plus execution add |

**Demo policy text (plain English, as the issuer would type it):**
1. Only investors with a valid KYC claim from a trusted issuer may receive tokens.
2. At least one KYC claim topic must be required.
3. Investors registered in a restricted country (408) may not receive tokens.
4. No investor may hold more than 1000 tokens.
5. The holding-limit module's balance records must match the real token balances.

**Why the others are not in the default set**
- **K4 and K5** are violated by stock T-REX. In a default audit they would raise findings on a clean config and confuse the false-positive measure. They run in an "extended" audit.
- **K2, J2, J3, H2, H4** are real rules, kept for the extended audits so the benchmark still covers all 13 rules.
- **J4** is not an audit rule. It is a known-exception trap, used in the clean set (C04).

---

## 7. Seeded vulnerable variants (starter list for Phase 3)

Type codes: **C** = code change in a copy of a contract, **G** = configuration only, **S** = stock gap (stock behaviour, no change needed).
All variant code lives in a separate `ComplyRWA/variants/` folder. The `T-REX/` folder stays unmodified, as in Phase 0.

| ID | Rule | Type | What is changed | Expected finding |
|---|---|---|---|---|
| V01 | K1 | C | `isVerified` returns true when **any** one required topic is satisfied (OR instead of AND) | Receiver with only topic 1 gets tokens |
| V02 | K1 | C | `isClaimValid` always returns true | Wallet with a fake claim gets tokens |
| V03 | K2 | C | ClaimIssuer ignores `revokedClaims` | Revoked investor still receives |
| V04 | K3 | G | `ClaimTopicsRegistry` has no topics | Registered wallet with no claim (Mallory) receives |
| V05 | J1 | G | Wrong country code restricted (`410` instead of `408`) | Transfer to Carol (408) succeeds |
| V06 | J2 | C | Registry copy whose updateCountry does not write the new country | After updateCountry(B, 408) Bob still receives |
| V07 | J3 | G | CountryRestrictModule removed with `removeModule` | Transfer to Carol succeeds |
| V08 | J3 | G | Module bound, but no country ever restricted | Transfer to Carol succeeds |
| V09 | H1 | G | MaxBalanceModule removed | Bob ends with 1100 against a cap of 1000 |
| V10 | H2 | C | Module keys balances by wallet, not identity | `ID_A` ends with 1200 across two wallets |
| V11 | H3 | G | Module bound with `batchPreSetModuleState(compliance, [ID_B], [0])` while Bob holds 800 (alternative build: `presetCompleted()` with nothing preset) | Bob reaches 1300, tracked 500 |
| V12 | H3 | C | Variant copy of `Token.sol` whose `forcedTransfer` skips `transferred` (stock `Token` has no such path, so this needs a copied Token) | Tracked balance differs from real balance |
| V13 | H4 | G | `setMaxBalance(type(uint256).max)` | Transfer of 5000 succeeds against policy cap 1000 |
| S01 | K4 | S | Stock config, claim with an expiry date in the past | Expired claim accepted (stock gap) |
| S02 | K5 | S | Stock config, sender's claim revoked | Revoked sender can still send (stock gap) |
| S03 | K2 | S | Stock config, claim revoked, then re-added by the investor with the twin signature (`s' = n - s`, flipped `v`) | Revoked investor receives again (stock gap, reproduced in test) |
| S04 | K2 | S | Stock config, claim revoked, then re-added by the investor with the same `r` and `s` but a different `v` byte (0/1 instead of 27/28) (`test/StockGapsVByte.t.sol`, `test_S04`) | Revoked investor receives again (stock gap, found in step 4.8, reproduced in test) |

**Count:** 13 seeded variants (V01 to V13) plus 4 stock-gap cases (S01, S02, S03, S04). Even if you drop the S cases, 13 stays inside the 12-15 target.

**Which run detects what**
- **Default audit (K1, K3, J1, H1, H3):** V01, V02, V04, V05, V07, V09, V11, V12, V13 (V13 is caught by the H1 test because a 5000 transfer exceeds the policy cap).
- **Extended audits (K2, J2, J3, H2, K4, K5):** V03, V06, V08, V10, S01, S02, S03, S04.

**Checks to do when building them:** some variants may turn out not to be reproducible (for example V06 depends on how the module reads the country). Reproducibility is judged in Phase 3. Only reproducible variants count in the 75% detection target.

---

## 8. Clean configurations (separate non-vulnerable set)

These must **not** produce findings. They measure the false-positive rate (target: 15% or less).

| ID | Scenario | Related rule | What a correct auditor does |
|---|---|---|---|
| C01 | Baseline: topic 1, issuer `IssuerX`, restricted `408`, cap 1000, all modules bound | all | No findings |
| C02 | Two required topics and two trusted issuers per topic. Receiver holds a valid claim for each topic from one issuer | K1 | No findings (AND across topics, OR across issuers is correct) |
| C03 | Alice holds 600 across `A1` and `A2` (same identity). She moves 500 from `A1` to `A2` and `moduleCheck` rejects it | H2, D3 | Reports nothing (expected rejection, known trap) |
| C04 | Agent calls `forcedTransfer` to Carol (country 408) | J1, J4, D1 | `INFO: known exception`, **not** a vulnerability |
| C05 | Different but valid settings: cap 500, countries `408` and `643` restricted | J1, H1 | No findings (checks the auditor reads values from the config) |
| C06 | Bob's claim was revoked, then re-issued **with different `data`** (identical data gives the same signature, which stays revoked). A transfer to Bob succeeds | K2 | No findings (receiving works again after re-issue) |
| C07 | Bob holds 900 and receives exactly 100, ending at exactly 1000 | H1 | No findings (hitting the cap exactly is allowed, since the check uses `>`) |
| C08 | MaxBalanceModule bound to a token that already has holders, with a **correct** preset (`batchPreSetModuleState` with the real balances, then `addModule`) | H3 | No findings |

C07 relies on the check being `>` rather than `>=`. **Confirmed** in the pinned `MaxBalanceModule.sol`: both `moduleCheck` and `moduleTransferAction` use `>`.

---

## 8a. How the clean configurations are built (Phase 3 step 3)

All of them live in `test/clean/CleanConfigs.t.sol`. Each configuration is a small contract that overrides one fixture hook. It is combined with the **property suite** (G01a to G05b, run as random action sequences) and, where the starting state allows, the **scenario suite** (G02, G05b recovery, G06 to G10, G13). The scenario tests assume an empty start, so configurations that start with balances run only the property suite.

| ID | What is different | Property suite | Scenario suite |
|---|---|---|---|
| C01 | Baseline | yes | yes |
| C02 | Topics 1 and 2 both required. Issuers X and Y both trusted for both topics. Everyone holds topic 1 from X. Topic 2 comes from Y (Alice, Carol) or X (Bob) | yes | yes |
| C03 | Start state: Alice holds 600 and her 500-token move between her own wallets was rejected | yes | no (same deployment as C01) |
| C04 | Start state: an agent `forcedTransfer` put 100 tokens in Carol's wallet (country 408) | yes | no (same deployment as C01) |
| C05 | Cap 500; countries 408 and 643 restricted. Gold tests read these numbers from the policy, not from constants | yes | yes |
| C06 | Bob's claim revoked, then re-issued with different data | yes | yes |
| C07 | Start state: Bob holds exactly 1000 (the cap), reached by receiving exactly 100 | yes | no (same deployment as C01) |
| C08 | Carol holds 300 and Alice's second wallet holds 100 before `MaxBalanceModule` exists. Correct preset via `batchPreSetModuleState`, then `addModule` | yes | yes |

The scenario assertions for C03, C04 and C07 are also covered by `test/C01_Baseline.t.sol` (`test_C03_...`, `test_C04_...`, `test_C07_...`).

**C08 start state (note).** The start state mints 300 tokens to Carol (country 408) **before** the country module is bound. At that moment no rule can block it, so this is a legal setup step, not a bypass. The balance exists first, then `MaxBalanceModule` is bound with a correct preset. Any review (human or LLM) that flags this mint as a jurisdiction bypass is raising a false alarm. This was found in step 4.8, where Sonnet's one clean-configuration false positive was C08. C08 is documented, not changed.

**A defect in a gold test, found by the clean set.** On C08 the test G13 failed because it assumed Carol starts with 0 tokens. This was a flaw in the test, not a finding about the contracts. G13 now compares against Carol's starting balance. This is the kind of false positive the clean set exists to catch.

---

## 9. Status: Phase 2 CLOSED

**Decisions (all signed off by the project owner)**

| Item | Outcome |
|---|---|
| K2 / K3 topic removal | Closed. Handled under K3 |
| D1 `forcedTransfer` judged per module and policy | **Accepted.** Confirmed by code |
| D2 K5 in scope as "violated by stock" | **Accepted.** Confirmed by code |
| D3 same-identity move expected as rejected | **Accepted.** Confirmed by code |
| D4 K4 in scope | **Accepted.** Confirmed by code |

**Checklist**
- [x] Commit hash recorded and tag `4.1.6` confirmed.
- [x] `environment.md` updated (commit hash, ONCHAINID version).
- [x] 13 rules written with the full template and an example each.
- [x] Default audit input chosen (section 6).
- [x] Variant list and clean set written (sections 7 and 8).
- [x] All 7 pinned-code checks done (section 5a).
- [x] D1 to D4 accepted.
- [x] Hardhat version recorded: 2.14.0 (run `npx hardhat --version` inside `T-REX/`).
- [x] **Addendum after closure:** the signature-malleability hypothesis was reproduced in a test and added as S03 (K2) and G14. No decision changed.

---

## 10. Phase 3 selection: gold invariants and seeds

### 10.1 Gold-standard tests (hand-written Foundry tests)

18 tests covering all 13 rules. **P** = property (must hold after any sequence of calls, checked with fuzzing or invariant tests). **S** = scenario or configuration check (fixed steps).

**Default audit set: 9 tests, for rules K1, K3, J1, H1, H3** (this gives the 8 or more executable invariants the project needs)

| ID | Rule | What it asserts | Type |
|---|---|---|---|
| G01a | K1 | After any successful `transfer`, `transferFrom` or `batchTransfer`, `isVerified(receiver)` is true | P |
| G01b | K1 | After any successful `mint` or `forcedTransfer`, `isVerified(receiver)` is true | P |
| G02a | K3 | `getClaimTopics().length > 0` | S |
| G02b | K3 | A registered wallet with no claim (Mallory) cannot receive | S |
| G03a | J1 | After any successful `transfer` or `transferFrom`, the receiver's country is not restricted | P |
| G03b | J1 | After any successful `mint`, the receiver's country is not restricted | P |
| G04 | H1 | After any action, every identity's **real** balance (summed over its wallets) is at most the **policy** cap (1000) | P |
| G05a | H3 | After `transfer` or `transferFrom`, tracked balance equals the sum of real balances for each identity | P |
| G05b | H3 | After `mint`, `burn`, `forcedTransfer` or `recoveryAddress`, tracked balance equals the sum of real balances | P |

**Extended set: 5 tests, for rules K2, J2, J3, H2, H4**

| ID | Rule | What it asserts | Type |
|---|---|---|---|
| G06 | K2 | After each revocation route (delete identity, remove trusted issuer, revoke claim), a transfer to that receiver reverts | S |
| G07 | J2 | After `updateCountry(wallet, 408)`, a transfer to that wallet reverts | S |
| G08 | J3 | The country module is in `getModules()` with `isModuleBound` true, and its restricted list matches the policy | S |
| G09 | H2 | Two wallets under one identity share one cap: Bob sending 600 to Alice's second wallet (`A1` holds 600) must revert | S |
| G10 | H4 | The cap equals the policy number. The module has no getter, so the test probes `canTransfer`: exactly 1000 is allowed, 1001 is blocked | S |

**Special set: 4 tests, for K4, K5, J4 and K2**

| ID | Rule | What it asserts | Expected on stock |
|---|---|---|---|
| G11 | K4 | An expired claim must be rejected | **Fails** (stock gap, S01) |
| G12 | K5 | A sender whose claim was revoked cannot send | **Fails** (stock gap, S02) |
| G13 | J4 | `forcedTransfer` to a restricted country succeeds and is labelled "known exception" | Passes, with INFO label |
| G14 | K2 | A revoked claim cannot be revived by the investor re-adding it with a different signature | **Fails** (stock gap, S03) |

G01 to G10 must **pass** on every clean configuration. G11, G12 and G14 are kept out of the default run, so they never disturb the false-positive measure.

**Refinements made while writing the tests (no rule changed)**
- **Tests judge against the policy, not the config.** G01 to G04 use ground truth kept by the test harness (who is KYC-verified, who is in country 408, the policy cap 1000). If a test asked the registry or the module, a broken registry or module would simply agree with itself, and variants such as V01 or V13 would go unnoticed.
- **G04 uses real balances** and the policy cap. Checking the module's own tracked balance against the module's own cap would miss V09 (module removed) and V13 (cap set to the maximum).
- **G09 is now a scenario** and G04 is the general property. They would otherwise check the same thing.
- **G10 probes behaviour** because `MaxBalanceModule` has no public getter for its cap.
- **G05b** is covered by two tests: the random-action property (mint, burn, `forcedTransfer`) and a scenario for `recoveryAddress`.

### 10.4 Phase 3 progress

**Step 1 (fixture and clean baseline C01): done.** `test/ComplyFixture.sol`, `test/C01_Baseline.t.sol`, `test/StockGaps.t.sol`. Confirmed on the project owner's machine: 16 tests passed (including the smoke test).

**Step 2 (gold tests on C01): done and confirmed on the owner's machine** (28 tests passed; the invariant call table lists only the 7 action functions; committed as `abe4ce9`). Files in `test/gold/`:
- `GoldHandler.sol` (random-action driver with ground truth), `GoldInvariants.t.sol` (7 property tests: G01a, G01b, G03a, G03b, G04, G05a, G05b), `GoldScenarios.t.sol` (11 tests: G02a, G02b, G05b recovery, G06a/b/c, G07, G08, G09, G10, G13), `GoldSpecial.t.sol` (G11, G12, G14).
- On C01: all 18 default tests pass. The 3 special tests fail, as expected, because stock T-REX and ONCHAINID violate K4, K5 and the K2 twin-signature case.
- **Handler fix (found from the owner's run).** The owner's call table showed the fuzzer calling the handler's setup functions `addIdentity` and `addWallet` (about 20% of calls). That could overwrite the harness's ground truth with random values and cause false findings. Fixed two ways: the setup functions now accept only the test contract, and `GoldInvariants.t.sol` excludes them from fuzzing with `excludeSelector`. After the fix the table should list only the 7 action functions. Mutation check repeated after the fix: same results.
- **Test counting.** Foundry 1.8.7 counts the 7 invariants as one suite entry, so a full run reports 28 tests, not 34. The tests are the same.
- Reproducibility: `foundry.toml` now fixes the fuzz seed (`0x436f6d706c79`), runs = 64, depth = 40. Repeated runs gave identical results.
- **Mutation check (sandbox only):** five quick variants were run to see whether the gold tests have teeth. V04 (empty topics) is caught by G01a and G01b. V05 (wrong country code) is caught by G03a and G03b. V09 (no `MaxBalanceModule`) is caught by G04, G05a and G05b. V13 (cap = max) is caught by G04, G09 and G10. V07 (country module removed) is caught by G07 and G08. These are not the final variants; step 4 builds them properly.

**Step 3 (clean configurations C02 to C08): done in sandbox, to be confirmed on the owner's machine.** `test/clean/CleanConfigs.t.sol` (section 8a). To support it, `ComplyFixture.sol` gained hooks (`_configure`, `_afterSetUp`, `_deployModules`, `_addModules`, `_configureModules`), policy numbers became variables, and claims can be issued from a second issuer. In the sandbox all clean-configuration tests pass (126 tests counting each invariant separately, which is 79 in the owner's Foundry counting, where each invariant suite counts once). The three special tests still fail on stock, as intended, and the five quick mutants are still caught.

**Next:** steps 4 and 5: build the 13 seeded variants (V01 to V13) and run every gold test against every variant to produce the variant-by-test table.

### 10.2 Seeds to build, in two waves

**Wave 1: configuration only (7 variants, fast).** V04, V05, V07, V08, V09, V11, V13.
**Wave 2: code changes in copies of contracts (6 variants, slower).** V01, V02, V03, V06, V10, V12.
**Stock gaps (no build, 4 cases).** S01, S02, S03, S04 (S04 added after Phase 4).
**Clean set (8 configurations).** C01 to C08.

All variant code goes in `ComplyRWA/variants/`, and `T-REX/` stays untouched. V06 and V12 are the riskiest (V06 needs a copied module, V12 a copied `Token.sol`). If both turn out not reproducible, 11 seeded variants plus S01, S02 and S03 still make 14, inside the 12 to 15 target.

### 10.3 Phase 3 order of work

1. Build the shared fixture and the clean baseline C01 (unpause the token, bind the token before `MaxBalanceModule`, modules behind proxies with `initialize()`, claim signing with `vm.sign`).
2. Write G01 to G10 and G13 and make them pass on C01.
3. Build C02 to C08. All of G01 to G10 must still pass.
4. Build the Wave 1 variants, then Wave 2.
5. Run every gold test against every variant and record a variant-by-test table.

**Done when:** each reproducible variant fails at least its linked gold test, every clean configuration passes G01 to G10, and any variant that fails nothing is marked "not reproducible" with a reason.