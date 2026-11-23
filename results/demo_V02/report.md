# ComplyRWA audit report: V02

Audit target: configuration `V02` (cause hidden from the auditor). Model: haiku. Mode: live.

## 1. Policy input

| Rule | Policy |
|---|---|
| K1 | Only investors with a valid KYC claim from a trusted issuer may receive tokens. |
| K3 | At least one KYC claim topic must be required. |
| J1 | Investors registered in a restricted country may not receive tokens. |
| H1 | No investor may hold more than the maximum allowed tokens. |
| H3 | The holding-limit module's balance records must match the real token balances. |

## 2. Generated properties and execution results

| Rule | Generated tests run | Failed | Status |
|---|---|---|---|
| K1 | 4 | 3 | FAIL |
| K3 | 4 | 2 | FAIL |
| J1 | 4 | 0 | PASS |
| H1 | 4 | 0 | PASS |
| H3 | 4 | 1 | FAIL |

## 3. Findings grouped by symptom

### KYC requirement missing or bypassed (K1, K3)

#### Rule K1: severity HIGH

**Violated policy**
Only investors with a valid KYC claim from a trusted issuer may receive tokens (rule K1).

**What went wrong**
In V02, the token accepted tokens for wallets without a valid KYC claim. Three tests expected a refusal and got none: a mint to Mallory, a transfer to Mallory, and a transfer to Bob after his claim was revoked. The configuration change is not provided, so the cause is not known. Because nothing reverted, it cannot be told whether "Transfer not possible" would have come from a KYC or a rule failure.

**Affected functions**
`token.mint` and `token.transfer`. The other two tests are not shown to affect any other function.

**How to reproduce**
1. Call `vm.prank(agent)` and `vm.expectRevert("Identity is not verified.")`.
2. Call `token.mint(m, 1)` (1 token to Mallory's wallet).
3. The call does not revert, so the test fails with "next call did not revert as expected."

The transfer tests fail the same way: `token.transfer(m, 1)` after Alice mints 10, and `token.transfer(b, 1)` after `_revokeClaim(idB)`.

**Suggested fix**
Compare V02 with the clean configuration C01 and find the setting that lets wallets without a valid KYC claim pass. The output does not show which setting does this.

Failing tests and reasons:
- `test_mintToUnverifiedWalletReverts`: next call did not revert as expected
- `test_transferToUnverifiedWalletReverts`: next call did not revert as expected
- `test_transferToWalletWithRevokedClaimReverts`: next call did not revert as expected

Direct evidence: 3 of 3 failing tests.

Reproducible test (generated):

```solidity
function test_mintToUnverifiedWalletReverts() public {
        uint256 before = token.balanceOf(m);

        vm.prank(agent);
        vm.expectRevert(bytes("Identity is not verified."));
        token.mint(m, 1);

        assertEq(token.balanceOf(m), before, "unverified wallet was minted tokens");
    }
```

#### Rule K3: severity HIGH

**Violated policy**
K3: at least one KYC claim topic must be required. Wallets without a KYC claim must be rejected.

**What went wrong**
Both tests expected a rejection and neither got one. Mallory, who is registered but holds no KYC claim, received tokens by mint and by transfer. The output does not show the cause. The V02 change is not provided, so the cause is not known.

**Affected functions**
`token.mint` and `token.transfer`, both of which rely on the identity KYC check.

**How to reproduce**
Transfer test, the clearest case:
1. Agent calls `token.mint(Alice's first wallet, CAP / 10)`. The holding cap value for V02 is not given.
2. Alice's first wallet calls `token.transfer(Mallory, CAP / 10)`.
3. Expected: revert "Transfer not possible". Actual: no revert. The test comment says the expected failure is the KYC check, so the intended revert was KYC-related.

The mint test (`test_K3_mintToUnclaimedWalletRejected`) fails the same way: `token.mint(Mallory, CAP / 10)` did not revert with "Identity is not verified."

**Suggested fix**
Make V02 require at least one KYC claim topic (`KYC_TOPIC`). Check whether V02 removes or empties the required claim topics. The output does not confirm this, so verify it before changing anything.

Failing tests and reasons:
- `test_K3_mintToUnclaimedWalletRejected`: next call did not revert as expected
- `test_K3_transferToUnclaimedWalletRejected`: next call did not revert as expected

Direct evidence: 2 of 2 failing tests.

Reproducible test (generated):

```solidity
function test_K3_mintToUnclaimedWalletRejected() public {
        // Mallory is registered but holds no KYC claim, so the policy forbids minting to her.
        uint256 amt = CAP / 10;
        assertTrue(amt > 0);

        uint256 before = token.balanceOf(m);

        vm.prank(agent);
        vm.expectRevert(bytes("Identity is not verified."));
        token.mint(m, amt);

        assertEq(token.balanceOf(m), before);
    }
```

### Holding limit not enforced or tracked wrongly (H3)

#### Rule H3: severity HIGH

Violated policy
H3: the holding-limit module's tracked balances must match the real token balances.

What went wrong
The test expected Bob's transfer to Alice's first wallet to be refused after Alice's KYC claim was revoked. The transfer was not refused. The test stopped at this check, so the H3 balance assertions did not run and any drift is not known. The output does not show whether the refusal was a KYC or a rule failure. The cause in V02 is not known, because the configuration change was not provided.

Affected functions
`token.transfer` (sender Bob). Revocation uses `_revokeClaim`.

How to reproduce
1. The agent mints CAP/10 tokens to Bob (CAP for V02 is not given).
2. Check that tracked and real balances match for all four identities.
3. Revoke Alice's KYC claim (`idA`).
4. Bob calls `token.transfer` to Alice's first wallet for half the amount.
5. The expected "Transfer not possible" revert did not happen.

Suggested fix
Not known from this output. Find out why V02 accepted a transfer to a recipient whose KYC claim was revoked, then rerun the test.

Failing tests and reasons:
- `test_H3_rejectedTransferDoesNotDrift`: next call did not revert as expected (side effect: a KYC failure let a transfer through)

Direct evidence: 0 of 1 failing tests.

All failing H3 tests are side effects of the KYC failure above. No separate holding-limit problem is shown.

Reproducible test (generated):

```solidity
function test_H3_rejectedTransferDoesNotDrift() public {
        uint256 amt = CAP / 10;
        _mint(b, amt);
        assertTrackedEqualsReal();

        // Recipient's KYC is revoked, so the transfer to a1 must be refused.
        _revokeClaim(idA);

        uint256 bBefore = token.balanceOf(b);
        vm.prank(b);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(a1, amt / 2);

        assertEq(token.balanceOf(b), bBefore, "rejected transfer moved tokens");
        assertTrackedEqualsReal();
    }
```

Note: a finding can be a side effect of another group's problem. Grouping is by rule category, not by proven root cause.

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 3; cost paid $0.0034; cost when first made $0.0034; model seconds 24
- Demo wall time: 32 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
