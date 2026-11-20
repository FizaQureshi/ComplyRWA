# ComplyRWA audit findings (blind configuration text)

| configuration | rule | severity | failing tests | checks |
|---|---|---|---|---|
| V04 | H3 | HIGH | 1 | ok |
| V04 | K1 | HIGH | 3 | ok |
| V04 | K3 | HIGH | 3 | ok |

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

