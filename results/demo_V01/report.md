# ComplyRWA audit report: V01

Audit target: configuration `V01` (cause hidden from the auditor). Model: haiku. Mode: live.

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
Rule K1: only investors with a valid KYC claim from a trusted issuer may receive tokens.

**What went wrong**
In V01, three transfers that should have been refused went through. The agent minted 1 unit to Mallory, who holds no KYC claim. Alice's first wallet sent 1 unit to Mallory, and Alice's first wallet sent 1 unit to Bob after his claim was revoked. The change V01 makes is not provided, so the cause is not known. Both transfer failures show only "Transfer not possible", which is used for KYC and rule failures alike, so which check failed cannot be told.

**Affected functions**
`token.mint`, `token.transfer`

**How to reproduce**
Clearest test: `test_mintToUnverifiedWalletReverts`
1. Record Mallory's balance.
2. Agent calls `vm.prank(agent)`.
3. Expect a revert with "Identity is not verified."
4. Agent calls `token.mint(m, 1)`. The call succeeds, so the test fails.

Also failing: `test_transferToUnverifiedWalletReverts` and `test_transferToWalletWithRevokedClaimReverts`.

**Suggested fix**
Compare V01 with the baseline C01 to find what changed. Restore the KYC check on the receiving side for `mint` and `transfer`, then rerun all three tests on every clean configuration.

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

Violated policy
K3: at least one KYC claim topic must be required.

What went wrong
Both tests expected a transfer to Mallory to be blocked, because she is registered but holds no KYC claim. In this configuration both calls succeeded, so the KYC check was not enforced. The configuration change is not provided, and the output does not show the cause. "Transfer not possible" covers both KYC and rule failures, and the output does not show which check would have fired.

Affected functions
`token.mint` (to Mallory's wallet) and `token.transfer` (from Alice's first wallet to Mallory's wallet).

How to reproduce
Clearest test: `test_K3_mintToUnclaimedWalletRejected`.
1. The agent calls `token.mint` for Mallory's wallet with one tenth of the holding cap. Expected: "Identity is not verified." Observed: no revert.

`test_K3_transferToUnclaimedWalletRejected` fails the same way: Alice's first wallet transfers to Mallory's wallet and no revert occurs.

Suggested fix
Confirm that the claim topics registry has at least one required topic (the KYC topic) in V01. The output does not show the cause, so check the V01 claim topic setup first.

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

**Violated policy**
H3: the MaxBalanceModule's tracked balance for each identity must equal the real token balance of that identity's wallets.

**What went wrong**
The test revoked Alice's KYC claim, then expected Bob's transfer of CAP/10 divided by 2 to Alice's first wallet (a1) to be refused with "Transfer not possible". The transfer was not refused. The test stopped at that point, so its H3 balance checks never ran. The failure does not show a balance mismatch, so H3 drift is not confirmed. The bypass shown is that a recipient with revoked KYC still received tokens. The test comment indicates a KYC failure, so that is the expected reason, but the output does not confirm which check was involved. The configuration change for V01 is not provided, so the cause is not known.

**Affected functions**
`token.transfer` (the rejected call that succeeded), and the KYC check on the recipient. Not known: whether the MaxBalanceModule's tracked balances were updated.

**How to reproduce**
1. Agent mints CAP/10 tokens to Bob (`_mint(b, amt)`).
2. Check tracked equals real balances for all identities.
3. Revoke Alice's KYC claim (`_revokeClaim(idA)`).
4. Bob calls `token.transfer(a1, amt / 2)`, expecting "Transfer not possible". This did not revert.

The other failing tests were not provided.

**Suggested fix**
Confirm that the revoked-KYC transfer is blocked in V01. Check what V01 changes to the identity or claim checks. Then re-run the test and check the H3 balances.

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

- Explainer LLM calls this run: 3; cost paid $0.0033; cost when first made $0.0033; model seconds 32
- Demo wall time: 43 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
