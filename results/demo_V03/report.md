# ComplyRWA audit report: V03

Audit target: configuration `V03` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| K1 | 4 | 1 | FAIL |
| K3 | 4 | 0 | PASS |
| J1 | 4 | 0 | PASS |
| H1 | 4 | 0 | PASS |
| H3 | 4 | 1 | FAIL |

## 3. Findings grouped by symptom

### KYC requirement missing or bypassed (K1)

#### Rule K1: severity HIGH

**Violated policy**
Rule K1: only investors with a valid KYC claim from a trusted issuer may receive tokens.

**What went wrong**
Bob's KYC claim was revoked, and the test expected a transfer of 1 token from Alice's first wallet to Bob's wallet to revert. The transfer succeeded instead, so a wallet without a valid claim received tokens. The failure output does not show why. The changes made by configuration V03 are not provided, so the cause is not known. Because the transfer did not revert, the revert message "Transfer not possible" was not seen, and it cannot be told whether the check that failed was KYC or a compliance rule.

**Affected functions**
`token.transfer`, as called in this test. It is not known whether `transferFrom` is affected.

**How to reproduce**
1. The agent mints 10 tokens to Alice's first wallet.
2. Revoke Bob's KYC claim at `claimIssuer` (`_revokeClaim(idB)`).
3. Alice's first wallet calls `token.transfer(b, 1)`, expecting a revert with "Transfer not possible".
4. Result: no revert. The test stops at the failed expectation, so the balance checks are not reached.

**Suggested fix**
Make `transfer` check that the receiving identity holds a valid KYC claim from a trusted issuer at the time of transfer, and revert with "Transfer not possible" when it does not. Once the V03 changes are known, confirm which check was removed or altered.

Failing tests and reasons:
- `test_transferToWalletWithRevokedClaimReverts`: next call did not revert as expected

Direct evidence: 1 of 1 failing tests.

Reproducible test (generated):

```solidity
function test_transferToWalletWithRevokedClaimReverts() public {
        _mint(a1, 10);
        _revokeClaim(idB);

        uint256 senderBefore = token.balanceOf(a1);
        uint256 recipientBefore = token.balanceOf(b);

        vm.prank(a1);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(b, 1);

        assertEq(token.balanceOf(a1), senderBefore, "sender balance changed on refused transfer");
        assertEq(token.balanceOf(b), recipientBefore, "investor with revoked KYC received tokens");
    }
```

### Holding limit not enforced or tracked wrongly (H3)

#### Rule H3: severity HIGH

Violated policy
Rule H3: the holding-limit module's tracked balances must match the real token balances.

What went wrong
The test expected Alice's wallets to refuse a transfer after her KYC claim was revoked. The transfer was accepted instead, so the test failed before the balance check ran. Whether tracked and real balances drifted is not known. The revert message cannot be checked either, because no revert happened. The V03 change is not provided, so the cause is not known.

Affected functions
token.transfer, _revokeClaim, _idBalance (used by the H3 check, which was not reached).

How to reproduce
1. The agent mints one tenth of the holding cap to Bob's wallet (`_mint(b, amt)`).
2. Check that tracked balances equal real balances.
3. Revoke Alice's identity KYC claim (`_revokeClaim(idA)`).
4. Bob transfers half of his amount to Alice's first wallet, expecting revert "Transfer not possible".
5. The transfer succeeds, and Forge reports "next call did not revert as expected".

Suggested fix
Compare the V03 settings with clean configuration C01. Confirm the recipient KYC check is active for this configuration, then rerun the test. Do not weaken the test to remove the revert expectation.

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

- Explainer LLM calls this run: 2; cost paid $0.0023; cost when first made $0.0023; model seconds 17
- Demo wall time: 24 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
