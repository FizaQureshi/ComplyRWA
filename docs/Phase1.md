# ComplyRWA: Phase 1 Study Notes

**Goal of Phase 1:** trace the transfer path through `Token`, `IdentityRegistry` and `ModularCompliance`, and draw the dependency map.

**Files studied, in order:**

1. `T-REX/contracts/token/Token.sol`
2. `T-REX/contracts/registry/implementation/IdentityRegistry.sol`
3. `T-REX/contracts/compliance/modular/ModularCompliance.sol`
4. `T-REX/contracts/compliance/modular/modules/MaxBalanceModule.sol`

Pinned version notes: Solidity `0.8.17`, T-REX (Tokeny) GPL-3.0. MaxBalanceModule is also under CC-BY-NC-4.0, which matters if ComplyRWA is ever commercialised.

---

## 0. The big picture

### Dependency map (text version)

```
Token.transfer()
 ├─ whenNotPaused                                       (Token storage)
 ├─ frozen checks, free-balance check                   (Token storage)
 ├─ IdentityRegistry.isVerified(_to)                    [KYC path]
 │    ├─ IdentityRegistryStorage.storedIdentity(_to)    wallet registered?
 │    ├─ ClaimTopicsRegistry.getClaimTopics()           which claims are required?
 │    ├─ TrustedIssuersRegistry.getTrustedIssuersForClaimTopic()   who may sign?
 │    ├─ Identity (ONCHAINID).getClaim(claimId)         does investor hold one?
 │    └─ ClaimIssuer.isClaimValid(...)                  is the signature still good?
 ├─ ModularCompliance.canTransfer(from, to, amt)        [rule path, read]
 │    └─ for each module: IModule.moduleCheck(from, to, amt, compliance)
 │         └─ MaxBalanceModule.moduleCheck
 │              ├─ reads _maxBalance[compliance]
 │              ├─ reads _IDBalance[compliance][identity(to)]
 │              └─ Token.identityRegistry().identity(to)      (module -> token -> registry)
 ├─ _transfer()                                         balances move
 └─ ModularCompliance.transferred(from, to, amt)        [rule path, write, onlyToken]
      └─ for each module: IModule.moduleTransferAction(from, to, amt)
           └─ MaxBalanceModule.moduleTransferAction
                ├─ writes _IDBalance for identity(from) and identity(to)
                └─ reverts if identity(to) balance > max
```

Mint follows the same pattern with `canTransfer(address(0), ...)` plus `created`. Burn calls only `destroyed`.

### The spine: check, move, notify

1. **Check** (read-only): freeze checks, `isVerified(_to)`, `canTransfer(...)`.
2. **Move**: `_transfer(...)` updates `_balances`.
3. **Notify**: `transferred(...)` lets modules update their own counters.

### Two enforcement paths

| Path | Question it answers | Where it lives | Contracts |
|---|---|---|---|
| KYC path | Is the receiver an eligible investor? | IdentityRegistry and the four registries behind it | 5 contracts |
| Rule path | Does this transfer respect the rules? | ModularCompliance and its modules | 1 dispatcher plus N modules |

Jurisdiction (country) is **not** in the KYC path. The country is stored in IdentityRegistryStorage but only compliance modules read it, through `investorCountry()`. The KYC and jurisdiction policy categories are therefore enforced in different places.

---

## 1. Token.sol

### Purpose

The ERC-20-like security token. It holds balances, freezes and pause state, and acts as the **entry point** for every balance change. It contains no compliance logic itself. It calls the IdentityRegistry (KYC) and ModularCompliance (rules) at the right moments.

### Key state (from TokenStorage)

`_balances`, `_allowances`, `_totalSupply`, `_frozen` (wallet-level freeze), `_frozenTokens` (partial freeze), `_tokenPaused`, `_tokenIdentityRegistry`, `_tokenCompliance`.

### `init(...)`

Sets name, symbol, decimals, registry and compliance addresses. **Sets `_tokenPaused = true`**, so a fresh token cannot transfer until an agent calls `unpause()`. The test fixture must unpause. `setCompliance` also calls `bindToken(address(this))` on the compliance contract.

### `transfer(address _to, uint256 _amount)`: the main function

```solidity
function transfer(address _to, uint256 _amount) public override whenNotPaused returns (bool) {
    require(!_frozen[_to] && !_frozen[msg.sender], "wallet is frozen");
    require(_amount <= balanceOf(msg.sender) - (_frozenTokens[msg.sender]), "Insufficient Balance");
    if (_tokenIdentityRegistry.isVerified(_to) && _tokenCompliance.canTransfer(msg.sender, _to, _amount)) {
        _transfer(msg.sender, _to, _amount);
        _tokenCompliance.transferred(msg.sender, _to, _amount);
        return true;
    }
    revert("Transfer not possible");
}
```

Line by line:

1. **`whenNotPaused`**: reverts if the token is paused.
2. **Freeze check**: neither sender nor receiver may be in `_frozen`.
3. **Free-balance check**: `_amount <= balance - frozenTokens`, which enforces partial freezes.
4. **Two compliance gates** joined with `&&`:
   - `isVerified(_to)`: KYC/identity, **receiver only**.
   - `canTransfer(msg.sender, _to, _amount)`: rule check across all modules.
5. **`_transfer`**: rejects zero addresses, calls the empty `_beforeTokenTransfer` hook, updates `_balances`, emits `Transfer`.
6. **`transferred`**: notifies compliance after the move so modules update counters.
7. **`revert("Transfer not possible")`**: the same message for both gate failures. A failing test does not say whether KYC or compliance blocked it, so the Counterexample Explainer has to work that out itself.

### Other token paths

| Function | Access | Checks | Notes |
|---|---|---|---|
| `transferFrom` | anyone with allowance | same as `transfer`, with `_from` as sender, plus `_approve` allowance deduction | Invariants must hold on both paths |
| `batchTransfer` | anyone | loops over `transfer` | Inherits the same checks |
| `forcedTransfer` | `onlyAgent` | **only `isVerified(_to)`**; skips `canTransfer`; still calls `transferred` | Intentional (court orders, recovery). Also unfreezes tokens if needed |
| `mint` | `onlyAgent` | `isVerified(_to)` **and** `canTransfer(address(0), _to, _amount)`; then calls `created` | Rules apply to issuance |
| `burn` | `onlyAgent` | no compliance checks; calls `destroyed` | Only reduces balances, so it cannot break a limit |
| `recoveryAddress` | `onlyAgent` | registers the new wallet in the registry, then `forcedTransfer`, copies freezes, deletes old identity | Touches both the registry and the token |
| `pause` / `unpause` | `onlyAgent` | n/a | Global switch |
| `setAddressFrozen`, `freezePartialTokens`, `unfreezePartialTokens` | `onlyAgent` | n/a | Freeze management |
| `setIdentityRegistry`, `setCompliance` | `onlyOwner` | n/a | Swapping either changes the whole rule set |

### Observations that matter for ComplyRWA

- **Only the receiver is KYC-checked.** `isVerified` is never called on `msg.sender`, so a holder who lost KYC can still send. This may be intended, but it is a policy question to write down.
- **`forcedTransfer` skips the read-side compliance check.** The auditor must treat it as a known exception, or it will produce false positives. Whether it can break a policy depends on the module (see section 4).
- **State drift.** Any path that moves balances without calling `transferred`, `created` or `destroyed` leaves module counters out of sync with real balances. This is a good seeded vulnerability.
- **`_beforeTokenTransfer` is empty** in this version, so there is nothing to trace there.

### Self-check answers

1. **Which two external contracts does `transfer` call before moving tokens?** The IdentityRegistry (`isVerified(_to)`) and ModularCompliance (`canTransfer`). Both are read-only.
2. **Why does `transferred` come after `_transfer`?** It is a notification that the move happened. Modules record the real post-transfer state. If it ran first, modules could record a transfer that later reverts, leaving state out of sync.
3. **Which function moves tokens without `canTransfer`?** `forcedTransfer`. (`burn` also skips it but cannot push anyone over a limit.)

---

## 2. IdentityRegistry.sol

### Purpose

The **KYC gate**. It answers one question: "does this wallet belong to an investor who holds all required claims from trusted issuers?" It stores nothing itself. It coordinates four other contracts: IdentityRegistryStorage, ClaimTopicsRegistry, TrustedIssuersRegistry, and the investor's ONCHAINID (plus the ClaimIssuer that signed each claim).

### `isVerified(address _userAddress)`: the key function

Logic in pseudocode:

```
if receiver has no registered identity        -> false
if no claim topics are required               -> true
for each required topic:
    get trusted issuers for that topic
    if there are none                         -> false
    does the receiver hold a VALID claim from at least ONE of them?
        no                                    -> false
return true
```

**AND across topics, OR across issuers.** Every required topic must be satisfied, and any one trusted issuer per topic is enough.

Walkthrough:

1. **Registration check**: `identity(_userAddress) == address(0)` returns false. `identity()` reads from **IdentityRegistryStorage**.
2. **Required topics**: `_tokenTopicsRegistry.getClaimTopics()`. If the list is empty, return `true`.
3. **Trusted issuers per topic**: from TrustedIssuersRegistry. Zero issuers for a required topic returns false (fail-closed).
4. **Claim IDs**: `keccak256(abi.encode(issuer, topic))`, computed from the **trusted issuers list**. A claim from a removed issuer is never looked up, so it stops counting.
5. **Fetch and validate**: `identity.getClaim(claimId)`, then `IClaimIssuer(issuer).isClaimValid(...)` inside `try/catch`. Outcomes per issuer:
   - Found and valid: exit the inner loop (`j = claimIds.length`), go to the next topic.
   - Found but invalid, or issuer call reverts: try the next issuer; if it was the last, return false.
   - No claim of that topic: same, next issuer or false.
6. All topics pass: return `true`.

The `try/catch` means a broken or malicious issuer contract cannot brick verification. It is simply treated as "not valid".

### Other functions in this file

| Function | Access | Purpose |
|---|---|---|
| `registerIdentity`, `batchRegisterIdentity` | agent | Add wallet, identity, country to storage |
| `updateIdentity` | agent | Change the ONCHAINID of a wallet |
| `updateCountry` | agent | Change the stored country (used in jurisdiction-change tests) |
| `deleteIdentity` | agent | Remove a wallet from storage |
| `setIdentityRegistryStorage`, `setClaimTopicsRegistry`, `setTrustedIssuersRegistry` | owner | Swap the underlying registries. Changes verification rules, so a misconfiguration here is a plausible vulnerable variant |
| `identity`, `investorCountry`, `contains`, getters | view | Read helpers |

### Observations that matter for ComplyRWA

- **Empty `requiredClaimTopics` makes KYC vacuous.** Any registered wallet passes. Strong seeded vulnerability. It is also a case where the invariant "only KYC-verified investors may receive tokens" is vacuously true.
- **Country is not checked here.** Jurisdiction lives in modules (see Rule path).
- **Claim expiry**: this code only asks the issuer whether the claim is valid. In the standard ClaimIssuer that is signature and revocation, as far as I know, not an expiry date. **Verify in the pinned version.** If it holds, an "expired KYC" test shows a bypass.
- **Trust assumption on the identity contract.** The `issuer` that gets called comes from what `getClaim` returns. The code never checks it equals `trustedIssuers[j]`. A forged identity contract registered for a wallet could return an attacker-controlled issuer. Registration is agent-gated, so this is a trust assumption, but worth a test.
- **Multiple revocation routes**: delete the identity, remove the trusted issuer, revoke the claim at the issuer, or remove the topic. Each should make `isVerified` return false. Each is a candidate "revocation actually blocks transfers" test.
- **Point-in-time check.** It runs only when a transfer happens. A wallet that already holds tokens and loses KYC keeps its balance and can still send.
- **Five-contract dependency**, which is exactly the cross-contract problem the Cross-Contract Compliance Analyzer must handle.

### Self-check answers

1. **Empty `requiredClaimTopics`, registered wallet?** `isVerified` returns `true`.
2. **Does `isVerified` enforce country?** No. Country is stored in IdentityRegistryStorage and enforced by compliance modules via `investorCountry()`.
3. **Investor's only KYC issuer removed from TrustedIssuersRegistry?** If no other trusted issuer exists for that topic, `getTrustedIssuersForClaimTopic` returns an empty list, `isVerified` returns false, and the next incoming transfer reverts with "Transfer not possible". The investor's claim is never looked up because claim IDs are computed from the trusted list only. (If another trusted issuer exists and the investor holds a valid claim from it, they still pass.)

---

## 3. ModularCompliance.sol

### Purpose

A **dispatcher**. It holds no rules of its own. It keeps a list of bound modules, asks each one whether a transfer is allowed, and tells each one when a transfer, mint or burn has happened. It also controls who may configure the modules.

### `canTransfer(_from, _to, _value)`: "may this happen?"

```solidity
function canTransfer(address _from, address _to, uint256 _value) external view override returns (bool) {
    uint256 length = _modules.length;
    for (uint256 i = 0; i < length; i++) {
        if (!IModule(_modules[i]).moduleCheck(_from, _to, _value, address(this))) {
            return false;
        }
    }
    return true;
}
```

- `view`, changes nothing.
- **AND across modules**: the first `false` blocks the transfer.
- `address(this)` is passed so one module contract can serve many compliance contracts. Modules keep separate state per compliance address.
- **Zero modules returns `true` for everything.** Another vacuous pass, like the empty claim topics list.
- No access control, so anyone can call it. Useful as a dry run in the test harness.

### `transferred(_from, _to, _value)`: "it happened, update your records"

```solidity
function transferred(address _from, address _to, uint256 _value) external onlyToken override {
    require(_from != address(0) && _to != address(0), "invalid argument - zero address");
    require(_value > 0, "invalid argument - no value transfer");
    uint256 length = _modules.length;
    for (uint256 i = 0; i < length; i++) {
        IModule(_modules[i]).moduleTransferAction(_from, _to, _value);
    }
}
```

- **`onlyToken`**: only the single bound token (`_tokenBound`) can call it, which stops outsiders corrupting module counters.
- **Zero-address check** is why mint and burn have their own functions: `created(_to, _value)` calls `moduleMintAction`, `destroyed(_from, _value)` calls `moduleBurnAction`.
- **`_value > 0`**: a zero-value `transfer` reverts here, after the balance move, so the whole call reverts. Edge case for fixtures.
- **No `try/catch`**: one reverting module reverts the whole token transfer. Fail-closed, but one broken module can freeze the token.

### Admin functions (these change which rules apply)

| Function | Who | Why it matters |
|---|---|---|
| `addModule` | owner | Binds a module (max 25). Calls `canComplianceBind` unless plug-and-play, then `bindCompliance` |
| `removeModule` | owner | **Silently removes a rule.** Blocked transfers become allowed |
| `callModuleFunction` | owner | The only way to configure modules (limits, country lists), since module setters accept only the compliance contract as caller. Raw `call` via assembly |
| `bindToken` / `unbindToken` | owner or token | The owner can bind any address as "the token". Whoever is bound can call `transferred`, `created`, `destroyed` and write module state |

### Observations that matter for ComplyRWA

- **Rules live in modules, so the slicer must find them.** The first step of any audit is `getModules()`. A policy such as "max 1000 tokens per holder" is only enforced if a MaxBalance-type module is bound **and configured**.
- **Module list = rule set.** Empty list, missing module, removed module: all easy seeded vulnerabilities, because the token still deploys and transfers still work.
- **State drift on late binding.** A module added after tokens exist starts with zero counters while real balances are non-zero. Check the pinned module's preset mechanism.
- **Configuration bugs, not code bugs.** `callModuleFunction` forwards arbitrary calldata. A wrong parameter (a limit of 0 or `type(uint256).max`, a wrong country code) is exactly the class ComplyRWA targets.
- **Trust assumption on `bindToken`.** Treat as a trust-model question, not a vulnerability.

### Self-check answers

1. **`canTransfer` with no modules bound?** It returns `true`. Dangerous because every rule-based invariant is satisfied vacuously and every transfer passes.
2. **Why can't `transferred` be used for minting?** It requires `_from != address(0)`, and a mint has `address(0)` as the source. That is why `created` exists.
3. **Why does `moduleCheck` receive `address(this)`?** So a single deployed module can serve many compliance contracts and look up the right per-compliance state (limits, counters).

---

## 4. MaxBalanceModule.sol

### Purpose

A **real rule**: a cap on how many tokens one investor may hold. This is where "holding limit" policies are enforced. It has two halves:

| Half | Function | Called by | Role |
|---|---|---|---|
| Read | `moduleCheck` | `canTransfer` (before the move) | "Would this break the limit?" |
| Write | `moduleTransferAction`, `moduleMintAction`, `moduleBurnAction` | `transferred`, `created`, `destroyed` (after the move) | Update counters |

### Key design fact: the limit is per identity, not per wallet

```solidity
mapping(address => mapping(address => uint256)) private _IDBalance; // compliance -> ONCHAINID -> balance
mapping(address => uint256) private _maxBalance;                    // compliance -> limit
```

Both are keyed by compliance address. The inner key is the investor's **ONCHAINID**. `_getIdentity` resolves a wallet through `token.identityRegistry().identity(wallet)` and reverts with "identity not found" if there is none. Two wallets under the same identity share one cap. This adds a **module -> token -> registry** dependency.

### `moduleCheck(_from, _to, _value, _compliance)`

```solidity
if (_value > _maxBalance[_compliance]) return false;
address _id = _getIdentity(_compliance, _to);
if ((_IDBalance[_compliance][_id] + _value) > _maxBalance[_compliance]) return false;
return true;
```

- Ignores `_from`. Only the receiver's resulting balance matters.
- Rejects a single transfer larger than the cap, then rejects if tracked balance plus amount exceeds the cap.
- **If `setMaxBalance` was never called, `_maxBalance` is 0**, so any non-zero transfer fails. An unconfigured module is fail-closed, unlike the empty-list passes elsewhere.

### `moduleTransferAction(_from, _to, _value)`

```solidity
_IDBalance[msg.sender][_idTo]   += _value;
_IDBalance[msg.sender][_idFrom] -= _value;
if (_IDBalance[msg.sender][_idTo] > _maxBalance[msg.sender]) revert MaxBalanceExceeded(msg.sender, _value);
```

1. Re-checks the limit **after** updating and reverts, a second line of defence.
2. The subtraction can underflow (Solidity 0.8 reverts). If the module thinks the sender holds less than they really do, the transfer reverts.
3. `msg.sender` is the compliance contract; `onlyComplianceCall` restricts the caller.

`moduleMintAction` does the same for the receiver only. `moduleBurnAction` only subtracts, with no limit check.

### Correction made during study: `forcedTransfer` and this module

`forcedTransfer` skips `canTransfer` (so `moduleCheck` never runs), but it still calls `transferred`, and `moduleTransferAction` reverts if the receiver ends up over the cap.

Correct statement:

- `forcedTransfer` bypasses only the **read-side** checks (`moduleCheck`).
- It still hits any **write-side** checks.
- Whether it can break a policy depends on the module. MaxBalance has a write-side guard. A pure country-restriction module typically has no check in its write functions, so forced transfers could reach a non-allowed country there. **Verify with the CountryRestrict module.**
- So the "forcedTransfer exemption" in the auditor must be decided **per module and per policy**.

### Setup and configuration functions

| Function | Access | Notes |
|---|---|---|
| `setMaxBalance(_max)` | `onlyComplianceCall` | Owner must go through `callModuleFunction`. `type(uint256).max` effectively disables the limit |
| `preSetModuleState`, `batchPreSetModuleState`, `presetCompleted` | owner of compliance | Seed counters for a token that already has holders. Revert if the module is already bound |
| `canComplianceBind` | view | True if preset completed or total supply is 0. Otherwise `addModule` refuses (guard against late-binding drift) |
| `getIDBalance` | view | Read tracked balance per identity |

**Nothing verifies that preset values match real balances.** A preset that is too low makes the module under-count, so holders can exceed the real limit.

### Observations that matter for ComplyRWA

- **Holding-limit invariant**: for every identity, `getIDBalance(compliance, id) <= maxBalance`. A good property test also asserts that tracked balance equals the sum of real `balanceOf` over the wallets of that identity.
- **Counter drift is the key bug class.** Seeded variants: bad preset values, module added after minting without a preset, module removed and re-added (state sits under the compliance key and may be stale).
- **Check-versus-action inconsistency (false-positive risk).** An investor with 600 tokens and a cap of 1000 moves 500 between two of their own wallets under one identity. `moduleCheck` computes 600 + 500 > 1000 and rejects, though the net change is zero. A naive "transfers that stay under the limit must succeed" invariant would flag this. It directly affects the 15% false-positive target.
- **Wallet splitting** is stopped only if all wallets share an identity. If an agent registers a second wallet under a different identity, the cap doubles. That is an issuer-process issue, so treat as out of scope.
- **Deleted identity vs revoked claim**: with this module bound, a wallet whose identity was deleted cannot send (`_getIdentity` reverts). A wallet that only had a claim revoked can still send. This refines the "revoked KYC can still send" observation from Token.sol.
- **Misleading NatSpec.** Several comments are copy-pasted: `moduleCheck` says it checks countries, and the action functions say "no action required". LLM-based generators will read these. The slicer should prefer code over comments.
- **Not yet seen:** `AbstractModuleUpgradeable`. As I recall, `onlyComplianceCall` checks the caller is a bound compliance. **Confirm in the pinned version.**

### Self-check answers

1. **`setMaxBalance` never called, transfer of 1 token?** `_maxBalance` is 0, so `_value (1) > 0` and `moduleCheck` returns `false`. The transfer is blocked.
2. **Why can't `forcedTransfer` push someone over the max?** Because it still calls `transferred`, and `moduleTransferAction` reverts with `MaxBalanceExceeded` if the receiver's tracked balance exceeds the cap.
3. **What stops binding to a token that already has holders with mismatched counters?** `canComplianceBind` (checked by `addModule`) returns true only if a preset was completed or total supply is zero. Otherwise binding is refused. Caveat: the preset values themselves are not verified.

---

## 5. Cross-file summary

### Vacuous-pass and fail-closed cases (seeded-vulnerability candidates)

| Situation | Result | Where |
|---|---|---|
| `requiredClaimTopics` empty | KYC passes for any registered wallet | IdentityRegistry |
| No trusted issuer for a required topic | KYC fails for everyone | IdentityRegistry |
| No modules bound | `canTransfer` returns true for everything | ModularCompliance |
| Module removed with `removeModule` | Rule silently disappears | ModularCompliance |
| `setMaxBalance` never called | Everything blocked (fail-closed) | MaxBalanceModule |
| `setMaxBalance(type(uint256).max)` | Limit effectively disabled | MaxBalanceModule |
| Preset too low or missing on late binding | Counters under-count, limit bypassable | MaxBalanceModule |

### Paths that skip or weaken checks

| Path | Skips | Still runs |
|---|---|---|
| `forcedTransfer` | `canTransfer` (read-side modules), KYC on sender, frozen checks | `isVerified(_to)`, `transferred` (write-side modules) |
| `burn` | all checks | `destroyed` |
| `transfer` / `transferFrom` | KYC on the sender | everything else |
| Revoked claim (identity not deleted) | n/a | Holder can still send; receiving is blocked |

### Known exceptions to encode in the auditor

- `forcedTransfer` is an intentional exemption from read-side rules. Decide per module and per policy.
- `onlyToken` / `onlyComplianceCall` trust assumptions are by design.
- `bindToken` by the owner is a trust-model matter, not a finding.

### Verification results (checked against source on GitHub)

Source checked: `onchain-id/solidity` main (ClaimIssuer) and `TokenySolutions/T-REX` main (modules). Re-check against your exact pinned commit.

- [x] **`ClaimIssuer.isClaimValid` and expiry.** It does not enforce expiry. It checks that the recovered signer's key has purpose 3 (claim signer key) and that the signature is not in `revokedClaims`. Any expiry would have to be encoded in the opaque claim `data` and enforced off-chain. An "expired KYC" test therefore shows a bypass.
- [x] **`onlyComplianceCall`.** It requires `complianceBound[msg.sender]` in the module's own storage. That flag is set by `bindCompliance(_compliance)`, which only requires `msg.sender == _compliance`. Any contract can therefore mark itself as "bound" in a module. This is harmless for MaxBalance because state is keyed by `msg.sender`, but "bound in the module" does not mean "listed in a real ModularCompliance". The auditor must use `ModularCompliance.getModules()` as the source of truth.
- [x] **`CountryRestrictModule` write hooks.** `moduleTransferAction`, `moduleMintAction` and `moduleBurnAction` are empty (only `onlyComplianceCall`). `moduleCheck` looks only at the receiver's country and ignores `_from` and the amount. `CountryAllowModule` has the same structure. Consequence: `forcedTransfer` can deliver tokens to a restricted country, because it skips `canTransfer` and nothing runs in the write hooks.
- [x] **Copy-pasted NatSpec.** Confirmed in `MaxBalanceModule`: the `moduleCheck` comment is the `CountryAllowModule` text word for word, and all three action functions say "no ... action required" although they update balances. In `CountryAllow`, `CountryRestrict`, `SupplyLimit` and `TransferRestrict` the "no action required" comments match the empty bodies. `ExchangeMonthlyLimits`, `TimeExchangeLimits`, `TimeTransfersLimits` and `TransferFees` were not reviewed in detail.

---

## 7. Addendum: CountryRestrictModule.sol

**Purpose:** a jurisdiction blacklist. It blocks transfers whose **receiver** is registered in a restricted country, per compliance contract.

**State:** `_restrictedCountries[compliance][countryCode]` (ISO 3166-1 numeric).

**Functions**

| Function | Access | Notes |
|---|---|---|
| `addCountryRestriction`, `removeCountryRestriction` | `onlyComplianceCall` | The compliance owner reaches them through `callModuleFunction`. Reverts if the status would not change |
| `batchRestrictCountries`, `batchUnrestrictCountries` | `onlyComplianceCall` | Fewer than 195 entries per batch; one bad entry reverts the whole batch |
| `moduleCheck` | view | Returns false if `identityRegistry().investorCountry(_to)` is restricted. Ignores `_from` and the amount |
| `moduleTransferAction`, `moduleMintAction`, `moduleBurnAction` | `onlyComplianceCall` | **Empty bodies.** No write-side guard |
| `canComplianceBind` / `isPlugAndPlay` | view | Both return true, so binding has no preconditions |

**Dependency:** `_getCountry` calls `compliance.getTokenBound()`, then `Token.identityRegistry()`, then `investorCountry(wallet)`, which IdentityRegistry forwards to IdentityRegistryStorage. MaxBalanceModule resolves identities the same way.

**What it means for ComplyRWA**

- **Jurisdiction invariant:** no wallet whose country is restricted should receive tokens through `transfer`, `transferFrom` or `mint`. These are the paths that call `canTransfer`.
- **`forcedTransfer` bypass is real here.** It skips `canTransfer`, and the write hooks are empty, so a forced transfer to a restricted country succeeds. Intentional for agents, but the auditor must classify it, not report it blindly.
- **Sender country is never checked.** A holder who moves into a restricted country (`updateCountry`) can still send tokens out.
- **Country change does not move balances.** After `updateCountry`, existing holdings stay. Only future receipts are blocked.
- **Blacklist semantics:** an unregistered or unset country code (0) is not restricted unless someone adds it. `CountryAllowModule` is the allow-list counterpart.
- **NatSpec is accurate in this file**, unlike MaxBalanceModule. One small mismatch: setters say "Only the owner of the Compliance smart contract can call this function", but the code requires the compliance contract itself as caller (the owner goes through `callModuleFunction`).
- **Verified against GitHub:** the `moduleCheck` and the three empty hooks match the version fetched from `TokenySolutions/T-REX` main. I did not diff the whole file line by line.