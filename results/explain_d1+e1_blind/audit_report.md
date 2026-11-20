# ComplyRWA audit findings (blind configuration text)

| configuration | rule | severity | failing tests | checks |
|---|---|---|---|---|
| V04 | H3 | HIGH | 1 | ok |
| V04 | K1 | HIGH | 3 | ok |
| V04 | K2 | HIGH | 3 | ok |
| V04 | K3 | HIGH | 3 | ok |
| V05 | J1 | HIGH | 3 | ok |
| V05 | J2 | HIGH | 3 | ok |
| V05 | J3 | HIGH | 3 | ok |
| V09 | H2 | HIGH | 4 | ok |
| V09 | H3 | HIGH | 4 | ok |
| V12 | H3 | HIGH | 1 | ok |
| V13 | H2 | HIGH | 2 | ok |
| V13 | H4 | HIGH | 2 | ok |

## Configuration V04

### Rule H3 (tests from batch d1: test_H3_rejectedTransferDoesNotDrift)

Severity: HIGH

Violated policy
H3: the holding-limit module's balance records must match the real token balances. The test also expects a transfer to a recipient with revoked KYC to be refused.

What went wrong
Bob's transfer to Alice's first wallet succeeded after Alice's KYC claim was revoked. The test expected "Transfer not possible". Because the call did not revert, the test stopped before the balance check, so it is not known whether the tracked balances also drifted. The test intends a KYC failure, but since nothing reverted, the output cannot show which check applies. The configuration change for V04 is not provided, so its cause is not known.

Affected functions
- `token.transfer` (recipient KYC check)
- `_revokeClaim` (revokes the claim that should block the transfer)

How to reproduce
1. The agent mints CAP / 10 tokens to Bob's wallet. The CAP value for V04 is not given.
2. Revoke the KYC claim for Alice's identity with `_revokeClaim(idA)`.
3. Bob calls `token.transfer` to Alice's first wallet for half that amount.
4. Expected: revert "Transfer not possible". Actual: the call did not revert.

No other failing tests are listed.

Suggested fix
Compare V04 with the clean configuration C01 to find the setting that lets a transfer to a revoked recipient succeed. Check the recipient KYC check, the required claim topic and the trusted issuer. Re-run the test on V04 after the fix.

### Rule K1 (tests from batch d1: test_mintToUnverifiedWalletReverts, test_transferToUnverifiedWalletReverts, test_transferToWalletWithRevokedClaimReverts)

Severity: HIGH

Violated policy
K1: Only investors with a valid KYC claim from a trusted issuer may receive tokens.

What went wrong
Under V04, the agent could mint to Mallory, and Alice and Bob could transfer to Mallory and to Bob after his claim was revoked. Mallory holds no KYC claim, and Bob's claim was revoked, so these transfers should have been refused. The change V04 makes is not provided, so the cause is not known.

Affected functions
- token.mint
- token.transfer

How to reproduce
Clearest test: test_mintToUnverifiedWalletReverts
1. Record Mallory's token balance.
2. As agent, call token.mint(Mallory's wallet, 1), expecting revert "Identity is not verified."
3. The call succeeded instead of reverting, so the test failed.

Also failing: test_transferToUnverifiedWalletReverts and test_transferToWalletWithRevokedClaimReverts.

The expected "Transfer not possible" revert never happened in the transfer tests, so it cannot be told whether a KYC or compliance check was meant to fail.

Suggested fix
Compare V04 with C01 for the KYC claim topic, the trusted issuer and the identity checks. The output does not show which setting is responsible.

### Rule K2 (tests from batch e1: test_revokedKycCannotReceiveMint, test_revokedKycCannotReceiveTransfer, test_revokedKycCannotReceiveTransferFrom)

Severity: HIGH

Violated policy
Rule K2: if an investor's KYC is revoked, the wallet can no longer receive tokens.

What went wrong
After Bob's KYC claim was revoked, all three ways of sending him tokens still succeeded. Each test expected a revert and forge reported that none occurred. The cause in V04 is not known, because the audit tool did not say what this configuration changes. For transfer and transferFrom, the expected message "Transfer not possible" covers both KYC and rule failures, so the output cannot show which check was skipped.

Affected functions
token.mint, token.transfer, token.transferFrom

How to reproduce
1. The agent mints one tenth of the holding cap to Alice's first wallet.
2. Alice's first wallet transfers half of that amount to Bob's wallet. This succeeds (control).
3. Revoke Bob's KYC claim.
4. Alice's first wallet transfers a quarter of the mint amount to Bob's wallet.
5. Expected: revert with "Transfer not possible". Actual: no revert.

The mint test (expects "Identity is not verified.") and the transferFrom test fail the same way.

Suggested fix
Make the receive-side KYC check apply to mint, transfer and transferFrom for revoked identities. Then rerun the three tests on V04 and review the configuration's change list to find what disables the check.

### Rule K3 (tests from batch d1: test_K3_mintToUnclaimedWalletRejected, test_K3_requiredTopicsNonEmptyAndIncludeKyc, test_K3_transferToUnclaimedWalletRejected)

Severity: HIGH

**Violated policy**
K3: At least one KYC claim topic must be required.

**What went wrong**
Mint and transfer to Mallory's wallet succeeded. Mallory is registered but holds no KYC claim, so both calls should have reverted. The required-topics test also failed, which suggests KYC_TOPIC is not required in V04. The failure output does not show the topic list. The configuration change is not provided, so the cause is not known. The transfer test expected "Transfer not possible", but the call did not revert, so it cannot be told whether a KYC or a rule check applies.

**Affected functions**
token.mint, token.transfer, ctr.getClaimTopics

**How to reproduce** (from test_K3_mintToUnclaimedWalletRejected and test_K3_transferToUnclaimedWalletRejected)
1. Agent calls token.mint(Mallory's wallet, CAP / 10). Expected revert: "Identity is not verified." Observed: no revert.
2. Agent calls token.mint(Alice's first wallet, CAP / 10).
3. Alice's first wallet calls token.transfer(Mallory's wallet, CAP / 10). Expected revert: "Transfer not possible." Observed: no revert.

The topics test (test_K3_requiredTopicsNonEmptyAndIncludeKyc) also failed. It only reads ctr.getClaimTopics().

**Suggested fix**
Make KYC_TOPIC a required claim topic in V04, for example with ctr.addClaimTopic(KYC_TOPIC). Then re-run the three tests.


## Configuration V05

### Rule J1 (tests from batch d1: test_mintToRestrictedCountryIsBlocked, test_transferFromToRestrictedCountryIsBlocked, test_transferToRestrictedCountryIsBlocked)

Severity: HIGH

Violated policy
Rule J1: investors registered in a restricted country may not receive tokens.

What went wrong
In configuration V05, three ways of sending tokens to a restricted-country investor succeeded when they should have been blocked. Each test expected a revert, and none happened. The tests target the rule failure, not KYC, since Bob holds a KYC claim. The cause in V05 is not known, because the audit tool did not describe the configuration change.

Affected functions
token.mint, token.transfer, token.transferFrom

How to reproduce
Steps from test_mintToRestrictedCountryIsBlocked:
1. Agent calls ir.updateCountry(b, RESTRICTED), so Bob is in the restricted country.
2. The test records total supply and Bob's balance.
3. Agent calls token.mint(b, CAP / 10). In C01 that is 100 tokens. V05's cap is not given.
4. The test expects the revert "Compliance not followed". The call did not revert.
5. Bob received new tokens and supply grew, so the balance checks fail.

The other two tests, test_transferFromToRestrictedCountryIsBlocked and test_transferToRestrictedCountryIsBlocked, failed the same way: the expected "Transfer not possible" revert did not occur.

Suggested fix
In V05, check that the country restriction module is bound to compliance and that the restricted-country variable is set as intended. The output does not confirm the cause.

### Rule J2 (tests from batch e1: test_J2_restoringAllowedCountryReenablesReceiving, test_J2_restrictedCountryUpdateBlocksMint, test_J2_restrictedCountryUpdateBlocksTransfer)

Severity: HIGH

**Violated policy**
J2: If a wallet's country is updated to a restricted country, it can no longer receive tokens.

**What went wrong**
In `test_J2_restoringAllowedCountryReenablesReceiving`, Bob's country was changed to the restricted country, but Alice's first wallet could still transfer one tenth of the cap to Bob. The test expected "Transfer not possible" and no revert occurred. The configuration change for V05 is not given, so the cause is not known. The other two tests fail with an assertion error and the output gives no line number. They likely fail at the first check that the country is restricted, before any transfer, but this cannot be confirmed from the output.

**Affected functions**
- `ir.updateCountry`
- `token.transfer`
- `countryModule.isCountryRestricted` (likely, from the other two failures)

**How to reproduce**
1. The agent mints one quarter of the cap to Alice's first wallet.
2. The agent calls `ir.updateCountry` to set Bob's wallet to `RESTRICTED`.
3. Alice's first wallet calls `token.transfer` to Bob's wallet for one tenth of the cap.
4. The test expects a revert. No revert occurs, so the transfer succeeds.

The tests `test_J2_restrictedCountryUpdateBlocksMint` and `test_J2_restrictedCountryUpdateBlocksTransfer` also fail, both on an assertion.

**Suggested fix**
Check V05's restricted-country setting and confirm that the country module is bound to `compliance` and applies to transfers. Then rerun the three tests.

### Rule J3 (tests from batch e1: test_J3_restrictedCountriesAreConfiguredInModule, test_J3_restrictedCountryMintBlockedWhileModuleBound, test_J3_transferIntoRestrictedCountryBlocked)

Severity: HIGH

**Violated policy**
J3: a country restriction is only real if the country module is bound to compliance and has the right countries set.

**What went wrong**
The module does not mark the restricted country (RESTRICTED) as restricted. The bound check passed, so the module is connected but its country settings are wrong. As a result, a transfer and a mint into Carol's wallet were not blocked. The V05 configuration change is not provided, so the cause is not known.

**Affected functions**
countryModule.isCountryRestricted (settings check), token.transfer and token.mint (the restriction that should block them).

**How to reproduce**
Test 3 is written out in full. Tests 1 and 2 fail for the same reason.
1. Agent mints one tenth of the cap to Alice's first wallet (a1).
2. Alice's first wallet transfers that same amount to Carol's wallet (c).
3. Expected: the transfer reverts. Actual: it did not revert.

Test 1 fails because RESTRICTED is not set as restricted. Test 2 fails because minting to Carol did not revert.

The revert reason cannot be told, because the test uses an expected revert with no message and the call did not revert.

**Suggested fix**
Set RESTRICTED (and RESTRICTED2 if it is not 0) as restricted in the country module, using the `_restrictCountry` helper through `compliance.callModuleFunction`. Then rerun the three J3 tests.


## Configuration V09

### Rule H2 (tests from batch e1: test_H2_fullIdentityDoesNotBlockOtherIdentity, test_H2_mintToSecondWalletCountsAgainstIdentityCap, test_H2_transferIntoSecondWalletCountsAgainstIdentityCap, test_H2_walletsOfSameIdentityCanFillSharedCapExactly)

**Severity: HIGH**

**Violated policy**
H2: Two wallets under the same identity share one cap.

**What went wrong**
Alice's identity balance (idA) reads 0 after her wallets receive tokens, so the shared cap is not enforced. In the clearest test, the agent minted to Alice's second wallet past the cap and the mint succeeded. Three other tests fail on the same 0 reading. The output does not show which line or module causes it. The configuration change for V09 was not provided.

**Affected functions**
- `token.mint`: confirmed by the mint test.
- `token.transfer`: not confirmed. The transfer test stops before its transfer step. The output does not show whether the revert was a KYC or a compliance failure.
- `_idBalance` / MaxBalanceModule tracking: reads 0.

**How to reproduce**
Test: `test_H2_mintToSecondWalletCountsAgainstIdentityCap`
1. Starting from an empty identity, the room under the cap is 1000 tokens.
2. The agent mints 500 tokens to Alice's first wallet (a1).
3. The agent mints 501 tokens to Alice's second wallet (a2), with a revert expected.
4. The mint does not revert. The test fails with "next call did not revert as expected."

The tests `test_H2_fullIdentityDoesNotBlockOtherIdentity`, `test_H2_transferIntoSecondWalletCountsAgainstIdentityCap` and `test_H2_walletsOfSameIdentityCanFillSharedCapExactly` fail on the identity balance reading 0.

**Suggested fix**
Check how the identity balance is updated on mint and transfer. Make sure the cap check reads the same combined total for both wallets of one identity. Re-run the four H2 tests on V09 to confirm.

### Rule H3 (tests from batch d1: test_H3_rejectedTransferDoesNotDrift, test_H3_sameIdentityTransferKeepsTrackedTotal, test_H3_trackedMatchesRealAfterBurnAndForcedTransfer, test_H3_trackedMatchesRealAfterMintAndTransfers)

Severity: HIGH

**Violated policy**
H3: the holding-limit module's tracked balance for each identity must equal the real token balance of that identity's wallets.

**What went wrong**
After a 100-token mint to Alice's first wallet, the tracked balance for Alice's identity stays 0 while her real balance is 100. Because the tracked figure is too low, the holding cap check sees less than the real holding, so the cap can be bypassed. The test output does not show why. What V09 changes was not provided, so the cause is not known.

**Affected functions**
The failing tests use mint, transfer, burn and forced transfer. The output does not show which function skips the tracker update.

**How to reproduce**
Taken from `test_H3_trackedMatchesRealAfterMintAndTransfers`:
1. The agent mints 100 tokens to Alice's first wallet (`a1`).
2. The H3 check runs: Alice's identity shows tracked 0, real 100. The test fails here.

The other three failing tests show the same gap, including Bob's identity (tracked 0, real 100) in the rejected-transfer test.

**Suggested fix**
Make the MaxBalanceModule update the tracked balance on every mint, transfer, burn and forced transfer. Review what V09 changes, since that is the likely cause, but that is not known from this output.


## Configuration V12

### Rule H3 (tests from batch d1: test_H3_trackedMatchesRealAfterBurnAndForcedTransfer)

Severity: HIGH

Violated policy
H3: the MaxBalanceModule's tracked balance for each identity must equal the real token balance of its wallets.

What went wrong
After the forced transfer, Alice's tracked balance is 75 but her real balance across both wallets is 50. The tracker did not drop when the tokens left her wallet. The check after the burn passed, so the burn appears correct. The output reports only idA, so the other identities were not shown to fail.

Affected functions
token.forcedTransfer: the tracker for the sender identity appears not to be updated. token.burn appears correct.

How to reproduce
1. Agent mints one tenth of the cap (CAP/10) to Alice's first wallet a1. The cap value in V12 is not given. With the C01 cap of 1000, this is 100 tokens.
2. Agent burns a quarter of that amount from a1.
3. Agent forces a transfer of a quarter of that amount from a1 to Bob's wallet b.
4. The check fails: Alice's tracked balance is 75, real balance is 50.

Suggested fix
Check how forcedTransfer updates the MaxBalanceModule's tracked balance for the sender's identity, and make it match the real balance change. Then rerun this test.

Configuration V12 changes: not provided. The cause within V12 is not known.


## Configuration V13

### Rule H2 (tests from batch e1: test_H2_mintToSecondWalletCountsAgainstIdentityCap, test_H2_transferIntoSecondWalletCountsAgainstIdentityCap)

**Severity: HIGH**

**Violated policy**
Two wallets under the same identity share one cap (H2).

**What went wrong**
In configuration V13, both tests expect a transfer that would push Alice's identity past the cap to be rejected. Both calls succeeded instead, so the shared cap was not enforced. The configuration change was not provided, so the cause is not known. The test expects a bare revert, so the revert message is not shown. It cannot be told whether a KYC or compliance rule applies, and in these tests no revert happened at all.

**Affected functions**
`token.mint` (agent minting to Alice's second wallet) and `token.transfer` (Bob to Alice's second wallet). The identity balance is tracked by the MaxBalanceModule.

**How to reproduce**
Mint test, the clearest one:
1. Read Alice's identity balance and work out the remaining room under the cap.
2. Agent mints half of that room to Alice's first wallet.
3. Agent calls `token.mint` for Alice's second wallet with an amount that exceeds the remaining room.
4. Expected: revert.
5. Actual: the call succeeds.

The transfer test (Bob sends into Alice's second wallet) fails the same way.

**Suggested fix**
Check the V13 settings against the policy: the cap value, and whether the MaxBalanceModule is bound to `compliance`. Then check that the identity-level cap is enforced on both mint and transfer. The cause cannot be confirmed from the output given.

### Rule H4 (tests from batch e1: test_H4_capIsNotMaxUint256, test_H4_capMatchesPolicyNumber)

Severity: HIGH

Violated policy
Rule H4: the holding cap must match the issuer's number and must not be 0 or the maximum uint256.

What went wrong
The MaxBalanceModule accepted more than the cap. It allowed a holding one unit above the cap, and it allowed a holding of the maximum uint256. The output does not show why. The cause is not known.

Affected functions
MaxBalanceModule.moduleCheck. Cap changes go through compliance.callModuleFunction. Whether V13 changed this path is not known.

How to reproduce
Failing test: test_H4_capMatchesPolicyNumber. test_H4_capIsNotMaxUint256 fails the same way.
1. Read Mallory's tracked balance (idM). The test requires it to be below CAP.
2. Compute room = CAP - held.
3. Call moduleCheck for Mallory's wallet (m) with room. Expected true; this passed.
4. Call moduleCheck for m with room + 1. Expected false; observed true.
The value of CAP for V13 is not given.

Suggested fix
Check the cap stored in MaxBalanceModule for V13 against the issuer's number. Confirm moduleCheck refuses any amount that would take a holding above that cap. Re-run both tests.

