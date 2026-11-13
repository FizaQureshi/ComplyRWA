# ComplyRWA fixture facts (for anyone writing a test)

These facts describe the state right after `setUp()` in the baseline configuration C01.
They are taken from `test/ComplyFixture.sol`. A test that inherits `ComplyFixture` gets all
of this for free. Use the member names exactly as they appear in the fixture summary.

## Who is who

| Person | Wallet(s) | Identity | Country | KYC claim (topic `KYC_TOPIC` = 1) |
|---|---|---|---|---|
| Alice | `a1`, `a2` | `idA` (one identity for both wallets) | `INDIA` (356) | yes |
| Bob | `b` | `idB` | `INDIA` | yes |
| Carol | `c` | `idC` | `RESTRICTED` (408 in C01) | yes |
| Mallory | `m` | `idM` | `INDIA` | **no** (registered in the registry, but holds no claim) |

- Every wallet above is registered in `ir` (the IdentityRegistry).
- After `setUp()` the token is unpaused, no tokens exist, and every balance is 0.

## Rules that are configured

- The required claim topic is `KYC_TOPIC`; the trusted issuer for it is `claimIssuer`.
- `countryModule` (CountryRestrictModule) and `maxBalanceModule` (MaxBalanceModule) are bound to `compliance`.
- Restricted country: `RESTRICTED`, and also `RESTRICTED2` when it is not 0. Holding cap: `CAP` (1000 in C01).
- **`RESTRICTED`, `RESTRICTED2` and `CAP` are variables.** Other clean configurations change them (for example cap 500). Read the variables; never write 408 or 1000 into a test.

## Who may call what

- `agent` is an agent of both `token` and `ir`. Agent-only calls need `vm.prank(agent)`: `token.mint`, `token.burn`, `token.forcedTransfer`, `token.recoveryAddress`, `ir.registerIdentity`, `ir.updateCountry`, `ir.deleteIdentity`.
- The test contract itself is the owner of the registries, `compliance` and the topic and issuer registries. Owner-only calls need no prank: for example `compliance.addModule`, `compliance.removeModule`, `compliance.callModuleFunction`, `ctr.addClaimTopic`, `tir.addTrustedIssuer`.
- Module settings can only be changed through `compliance.callModuleFunction(callData, module)`. The helpers `_restrictCountry(country)` and `_setCap(cap)` do this.

## Helpers you can use

- `_mint(to, amount)`: the agent mints. `_transfer(from, to, amount)`: `from` calls `token.transfer`.
- `_idBalance(identity)`: the MaxBalanceModule's tracked balance for an identity.
- `_revokeClaim(identity)`: revokes that identity's KYC claim at `claimIssuer`.
- `_issueClaim(identity, wallet)` and `_issueClaim(identity, wallet, topic, data)`: add a signed claim.

## Revert messages

- `transfer`, `transferFrom` and `forcedTransfer` revert with `"Transfer not possible"` for both a KYC failure and a rule failure.
- `mint` reverts with `"Identity is not verified."` (KYC) or `"Compliance not followed"` (rules).
- The MaxBalanceModule's own check on the write side reverts with `MaxBalanceExceeded`.

## What differs in other configurations

- Scenario tests (fixed steps) run only where the start state is empty: C01, C02, C05, C06, C08 and the variants except V11.
- C02 requires two claim topics and trusts two issuers. C05 changes the cap and restricted countries. C06 has a claim that was revoked and re-issued. C08 starts with some balances.
- A correct test must pass on all clean configurations, so it must not assume anything that these differences change.