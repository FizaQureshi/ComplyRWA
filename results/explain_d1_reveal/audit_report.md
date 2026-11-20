# ComplyRWA audit findings (reveal configuration text)

| configuration | rule | severity | failing tests | checks |
|---|---|---|---|---|
| V05 | J1 | HIGH | 3 | see note |
| V12 | H3 | HIGH | 1 | see note |

## Configuration V05

### Rule J1 (tests from batch d1: test_mintToRestrictedCountryIsBlocked, test_transferFromToRestrictedCountryIsBlocked, test_transferToRestrictedCountryIsBlocked)

HIGH

**Violated policy**
Rule J1: investors registered in a restricted country may not receive tokens.

**What went wrong**
Under configuration V05, the restricted country code is 410 instead of 408. In all three tests, the receiver `b` is set to `RESTRICTED` and the test expects the operation to revert. Forge reports that none of the calls reverted, so `b` could receive tokens. The most likely cause is the country code mismatch, but the input does not show the value of the `RESTRICTED` constant, so this cannot be confirmed.

The two transfer tests expect "Transfer not possible." That message is also used for KYC failures, and the output does not show which check ran, so the cause cannot be confirmed from the input.

**Affected functions**
- `mint`
- `transferFrom`
- `transfer`

**How to reproduce**
Test 1: `test_mintToRestrictedCountryIsBlocked`
1. Agent calls `ir.updateCountry(b, RESTRICTED)`.
2. Agent calls `token.mint(b, CAP / 10)`. Expected revert "Compliance not followed". No revert occurred.

Test 2: `test_transferFromToRestrictedCountryIsBlocked`
1. Mint `CAP / 10` to `a1`.
2. Agent calls `ir.updateCountry(b, RESTRICTED)`.
3. `a1` calls `token.approve(b, CAP / 10)`.
4. `b` calls `token.transferFrom(a1, b, CAP / 10)`. Expected revert "Transfer not possible". No revert occurred.

Test 3: `test_transferToRestrictedCountryIsBlocked`
1. Mint `CAP / 10` to `a1`.
2. Agent calls `ir.updateCountry(b, RESTRICTED)`.
3. `a1` calls `token.transfer(b, CAP / 10)`. Expected revert "Transfer not possible". No revert occurred.

The numeric value of `CAP` is not in the input.

**Suggested fix**
Confirm that the `RESTRICTED` constant and the country restriction in V05 use the same code. Set the restricted code to the value the policy intends, then rerun all three tests. If the tests still fail, check the transfer-path compliance logic and confirm which check produces "Transfer not possible."

> Automatic checks: 284 words (limit 250)


## Configuration V12

### Rule H3 (tests from batch d1: test_H3_trackedMatchesRealAfterBurnAndForcedTransfer)

**Severity: HIGH** (a rule is bypassed)

**Violated policy**
H3: The holding-limit module's balance records must match the real token balances.

**What went wrong**
The test passes the mint and the burn checks. It fails on the forced transfer. The failure shows the tracked balance for identity A is 75 while its real wallet balance is 50. The forced transfer moved tokens out of a1 but did not update the module's records, because `forcedTransfer` does not call `transferred`. The module therefore still counts 25 tokens that the holder no longer has. The receiver's record (identity B) is also not updated, so it likely shows less than its real balance, which could let B pass a holding limit it should fail. The test source does not print idB's values, so this second effect is inferred, not observed.

This is not the known INFO exception. That exception covers an agent's forcedTransfer to a restricted country, and nothing in this test or configuration shows a country check.

**Affected functions**
- `forcedTransfer`: does not call `transferred`.
- `burn`: the test passes its assertion, so it appears to update the records correctly.

**How to reproduce**
The CAP value is not given. The failure values (75 and 50) imply CAP/10 = 100 units, so the steps below assume amt = 100.
1. Mint 100 tokens to a1. Tracked and real balances both equal 100.
2. Agent calls `burn(a1, 25)`. Tracked and real both equal 75.
3. Agent calls `forcedTransfer(a1, b, 25)`. Real balance of a1 becomes 50; tracked stays at 75.
4. The assertion `idA tracked != real: 75 != 50` fails.

**Suggested fix**
Make `forcedTransfer` call `transferred` for the sender and receiver identities, as the normal `transfer` path does. Then add a check that runs H3 after each forced transfer, including one where the receiver is a different identity.

> Automatic checks: 303 words (limit 250)

