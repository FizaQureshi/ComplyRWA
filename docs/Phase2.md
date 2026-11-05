# ComplyRWA: Phase 2

**Goal of Phase 2:** fix exactly what ComplyRWA will check, so Phases 3 and 4 have a stable target.

**Scope:** 3 policy categories, 3-5 rules per category (13 rules total).

| Category | Pinned component | Rules |
|---|---|---|
| KYC | IdentityRegistry (and the registries behind it) | K1 to K5 |
| Jurisdiction | CountryRestrictModule | J1 to J4 |
| Holding limit | MaxBalanceModule | H1 to H4 |

Pinned system: T-REX tag `4.1.6`, Solidity 0.8.17.
Commit hash: `a09cfd38aa257d56db7ff9c90f30e65f125a141b` (`a09cfd3`, "Compliance modules fixes & improvements (#228)").

> **How to read the examples.** Every example is a *planned* case, written from the Phase 1 notes. None of them has been run yet. They become real in Phase 3, when each one is turned into a seeded vulnerable variant and a Foundry test.

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
| **Status** | Holds on stock |

**Example: revoked claim still accepted**

| Step | Detail |
|---|---|
| Setup | Bob's claim is revoked at IssuerX (`revokeClaim`). Variant ClaimIssuer's `isClaimValid` skips the `revokedClaims` check. |
| Action | Alice calls `transfer(B, 100)` |
| Policy expects | Revert `"Transfer not possible"` |
| Broken config gives | Transfer **succeeds** |
| Finding | K2 violated: revocation had no effect on receiving |

---

> **K2 candidate (untested).** A possible revocation bypass through signature malleability is described in section 5a (note after item 12). It needs a Foundry test before it counts as a finding.

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
| K2 | KYC | Revocation blocks receiving | Holds | Revocation ignored |
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
| V06 | J2 | C | Module uses the country stored at registration, not the current one | After `updateCountry(B, 408)` Bob still receives |
| V07 | J3 | G | CountryRestrictModule removed with `removeModule` | Transfer to Carol succeeds |
| V08 | J3 | G | Module bound, but no country ever restricted | Transfer to Carol succeeds |
| V09 | H1 | G | MaxBalanceModule removed | Bob ends with 1100 against a cap of 1000 |
| V10 | H2 | C | Module keys balances by wallet, not identity | `ID_A` ends with 1200 across two wallets |
| V11 | H3 | G | Module bound with `batchPreSetModuleState(compliance, [ID_B], [0])` while Bob holds 800 (alternative build: `presetCompleted()` with nothing preset) | Bob reaches 1300, tracked 500 |
| V12 | H3 | C | Variant copy of `Token.sol` whose `forcedTransfer` skips `transferred` (stock `Token` has no such path, so this needs a copied Token) | Tracked balance differs from real balance |
| V13 | H4 | G | `setMaxBalance(type(uint256).max)` | Transfer of 5000 succeeds against policy cap 1000 |
| S01 | K4 | S | Stock config, claim with an expiry date in the past | Expired claim accepted (stock gap) |
| S02 | K5 | S | Stock config, sender's claim revoked | Revoked sender can still send (stock gap) |



**Which run detects what**
- **Default audit (K1, K3, J1, H1, H3):** V01, V02, V04, V05, V07, V09, V11, V12, V13 (V13 is caught by the H1 test because a 5000 transfer exceeds the policy cap).
- **Extended audits (K2, J2, J3, H2, K4, K5):** V03, V06, V08, V10, S01, S02.

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
 
## 9. Phase 3 selection: gold invariants and seeds
 
### 9.1 Gold-standard tests (hand-written Foundry tests)
 
17 tests covering all 13 rules. **P** = property (must hold after any sequence of calls, checked with fuzzing or invariant tests). **S** = scenario or configuration check (fixed steps).
 
**Default audit set: 9 tests, for rules K1, K3, J1, H1, H3** (this gives the 8 or more executable invariants the project needs)
 
| ID | Rule | What it asserts | Type |
|---|---|---|---|
| G01a | K1 | After any successful `transfer`, `transferFrom` or `batchTransfer`, `isVerified(receiver)` is true | P |
| G01b | K1 | After any successful `mint` or `forcedTransfer`, `isVerified(receiver)` is true | P |
| G02a | K3 | `getClaimTopics().length > 0` | S |
| G02b | K3 | A registered wallet with no claim (Mallory) cannot receive | S |
| G03a | J1 | After any successful `transfer` or `transferFrom`, the receiver's country is not restricted | P |
| G03b | J1 | After any successful `mint`, the receiver's country is not restricted | P |
| G04 | H1 | After `transfer`, `transferFrom`, `mint` or `forcedTransfer`, every identity's tracked balance is at most the cap | P |
| G05a | H3 | After `transfer` or `transferFrom`, tracked balance equals the sum of real balances for each identity | P |
| G05b | H3 | After `mint`, `burn`, `forcedTransfer` or `recoveryAddress`, tracked balance equals the sum of real balances | P |
 
**Extended set: 5 tests, for rules K2, J2, J3, H2, H4**
 
| ID | Rule | What it asserts | Type |
|---|---|---|---|
| G06 | K2 | After each revocation route (delete identity, remove trusted issuer, revoke claim), a transfer to that receiver reverts | S |
| G07 | J2 | After `updateCountry(wallet, 408)`, a transfer to that wallet reverts | S |
| G08 | J3 | The country module is in `getModules()` with `isModuleBound` true, and its restricted list matches the policy | S |
| G09 | H2 | For wallets under one identity, the sum of real balances is at most the cap | P |
| G10 | H4 | `0 < maxBalance < type(uint256).max` and equals the policy number | S |
 
**Special set: 3 tests, for K4, K5 and J4**
 
| ID | Rule | What it asserts | Expected on stock |
|---|---|---|---|
| G11 | K4 | An expired claim must be rejected | **Fails** (stock gap, S01) |
| G12 | K5 | A sender whose claim was revoked cannot send | **Fails** (stock gap, S02) |
| G13 | J4 | `forcedTransfer` to a restricted country succeeds and is labelled "known exception" | Passes, with INFO label |
 
G01 to G10 must **pass** on every clean configuration. G11 and G12 are kept out of the default run, so they never disturb the false-positive measure.
 
### 9.2 Seeds to build, in two waves
 
**Wave 1: configuration only (7 variants, fast).** V04, V05, V07, V08, V09, V11, V13.
**Wave 2: code changes in copies of contracts (6 variants, slower).** V01, V02, V03, V06, V10, V12.
**Stock gaps (no build, 2 cases).** S01, S02.
**Clean set (8 configurations).** C01 to C08.
 
All variant code goes in `ComplyRWA/variants/`, and `T-REX/` stays untouched. V06 and V12 are the riskiest (V06 needs a copied module, V12 a copied `Token.sol`). If both turn out not reproducible, 11 seeded variants plus S01 and S02 still make 13, inside the 12 to 15 target.
 
### 9.3 Phase 3 order of work
 
1. Build the shared fixture and the clean baseline C01 (unpause the token, bind the token before `MaxBalanceModule`, modules behind proxies with `initialize()`, claim signing with `vm.sign`).
2. Write G01 to G10 and G13 and make them pass on C01.
3. Build C02 to C08. All of G01 to G10 must still pass.
4. Build the Wave 1 variants, then Wave 2.
5. Run every gold test against every variant and record a variant-by-test table.


**Done when:** each reproducible variant fails at least its linked gold test, every clean configuration passes G01 to G10, and any variant that fails nothing is marked "not reproducible" with a reason.