# ComplyRWA audit findings (blind configuration text)

| configuration | rule | severity | failing tests | checks |
|---|---|---|---|---|
| V05 | J1 | HIGH | 3 | see note |
| V12 | H3 | HIGH | 1 | see note |

## Configuration V05

### Rule J1 (tests from batch d1: test_mintToRestrictedCountryIsBlocked, test_transferFromToRestrictedCountryIsBlocked, test_transferToRestrictedCountryIsBlocked)

HIGH

**Violated policy**
Rule J1: Investors registered in a restricted country may not receive tokens.

**What went wrong**
In all three tests, the agent marked the receiver `b` as restricted, and then a mint or transfer to `b` did not revert. Each test expected a revert, so the token accepted the restricted-country receiver. The failure output does not show balances after the call, so the test's own balance checks were not reached. Configuration V05 is not described, so the cause is not known from the given information.

For the revert message: `transfer` and `transferFrom` expect "Transfer not possible", which the issuer's rules describe as the message for both KYC and compliance failures. The test does not show whether `b` passed KYC, so the check that should have fired cannot be identified. The mint test expects "Compliance not followed". Since no revert occurred, no message was observed.

**Affected functions**
- `mint` (receiver `b`)
- `transfer` (receiver `b`)
- `transferFrom` (receiver `b`, spender `b`)

**How to reproduce**
1. Agent calls `ir.updateCountry(b, RESTRICTED)`.
2. Agent calls `token.mint(b, CAP/10)`. Expected: revert "Compliance not followed". Actual: call did not revert. (CAP's value is not given.)

Transfer case:
1. Setup: `_mint(a1, CAP/10)`.
2. Agent calls `ir.updateCountry(b, RESTRICTED)`.
3. `a1` calls `token.transfer(b, CAP/10)`. Expected: revert "Transfer not possible". Actual: call did not revert.

TransferFrom case:
1. Setup: `_mint(a1, CAP/10)`.
2. Agent calls `ir.updateCountry(b, RESTRICTED)`.
3. `a1` calls `token.approve(b, CAP/10)`.
4. `b` calls `token.transferFrom(a1, b, CAP/10)`. Expected: revert "Transfer not possible". Actual: call did not revert.

**Suggested fix**
Make `mint`, `transfer` and `transferFrom` check the receiver's country against the restricted list before moving tokens, and revert when the receiver is restricted. Then rerun all three tests. Separately, provide the V05 configuration change so the cause can be confirmed.

> Automatic checks: 290 words (limit 250)


## Configuration V12

### Rule H3 (tests from batch d1: test_H3_trackedMatchesRealAfterBurnAndForcedTransfer)

**Severity: HIGH**

**Violated policy**
H3: the holding-limit module's tracked balance for each identity must equal the real token balance of that identity's wallets.

**What went wrong**
For identity idA, the tracked balance is 75 and the real balance (a1 + a2) is 50. The test does not show the tracked value before the failure. The first two checks in the test (after the mint and after the burn) did not fail, so the mismatch appeared after the forced transfer. The 25-unit gap matches the forced transfer amount (amt/4) that left a1. This suggests `forcedTransfer` moved the real tokens but did not update idA's tracked balance. The failure stopped at idA, so idB, idC and idM were not checked. Whether the tracker for the recipient (b) is also wrong is not known. If it is understated, the holding limit could be exceeded. The failure output does not show the value of CAP, so the amounts are not known beyond the 75 and 50 shown.

**Affected functions**
- `forcedTransfer` (apparent cause, inferred from the test order and values)
- `burn` (passed its check in this run)
- MaxBalanceModule tracker (named in the test comment; its update logic is not visible)

**How to reproduce**
1. Mint amt = CAP/10 to a1 (exact value not shown in output).
2. Agent calls `burn(a1, amt/4)`. Tracked and real balances agree after this step.
3. Agent calls `forcedTransfer(a1, b, amt/4)`.
4. Check H3: idA tracked = 75, idA real = 50. Fails.

**Suggested fix**
Make `forcedTransfer` update the holding-limit tracker for both the sender's and the recipient's identities, the same way a normal transfer does. Add a check for idB and the other identities, so the test reports every mismatch. The configuration V12 changes are not known, so the cause cannot be confirmed from this output alone.

> Automatic checks: 300 words (limit 250)

