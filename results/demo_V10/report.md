# ComplyRWA audit report: V10

Audit target: configuration `V10` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| K1 | 4 | 0 | PASS |
| K3 | 4 | 0 | PASS |
| J1 | 4 | 0 | PASS |
| H1 | 4 | 3 | FAIL |
| H3 | 4 | 4 | FAIL |

## 3. Findings grouped by symptom

### Holding limit not enforced or tracked wrongly (H1, H3)

#### Rule H1: severity HIGH

Violated policy
H1: No investor may hold more than the maximum allowed number of tokens.

What went wrong
Under V10, Bob's tracked identity balance stays at 0 after an agent mints him 500 tokens, so the cap check does not count the holding. The output shows "0 != 500" in two tests. In the cross-wallet test, over-cap mints to Alice's wallets raised no error and the transfer to a2 was not blocked. The failing line and the V10 cause are not known, because the configuration change was not provided.

Affected functions
token.mint, token.transfer, and MaxBalanceModule balance tracking (_idBalance).

How to reproduce
Steps from test_mintWithinCapSucceeds:
1. Read _idBalance(idB). The fixture start state is 0.
2. Room = CAP minus 0. The output's 500 implies CAP 1000 (V10's CAP is not given).
3. Agent calls token.mint(Bob, 500). No revert is shown.
4. Check balanceOf(Bob) and _idBalance(idB) equal 500. Output: 0 != 500.

Also failing: test_transferWithinIdentityCapSucceeds (0 != 500) and test_transferToSecondWalletCannotExceedIdentityCap (assertFalse with no values shown).

Suggested fix
Make MaxBalanceModule update identity balances on mint and transfer under V10, and revert over-cap mints with MaxBalanceExceeded. Rerun the three tests.

Failing tests and reasons:
- `test_mintWithinCapSucceeds`: assertion failed: 0 != 500 (side effect: the module's counter did not move)
- `test_transferToSecondWalletCannotExceedIdentityCap`: assertion failed
- `test_transferWithinIdentityCapSucceeds`: assertion failed: 0 != 500 (side effect: the module's counter did not move)

Direct evidence: 1 of 3 failing tests.

Reproducible test (generated):

```solidity
function test_mintWithinCapSucceeds() public {
        uint256 bal = _idBalance(idB);
        assertTrue(bal <= CAP);
        uint256 room = CAP - bal;
        assertGt(room, 1);
        uint256 amt = room / 2;

        uint256 pre = token.balanceOf(b);
        vm.prank(agent);
        token.mint(b, amt);

        assertEq(token.balanceOf(b), pre + amt);
        assertEq(_idBalance(idB), bal + amt);
        assertTrue(_idBalance(idB) <= CAP);
    }
```

#### Rule H3: severity HIGH

**Violated policy**
Rule H3: the holding-limit module's balance records must match the real token balances.

**What went wrong**
After 100 tokens were minted to Bob, the module's record for Bob's identity showed 0 while his real balance was 100. The same mismatch appeared for Alice's identity after minting to her wallet. The tests fail at this first check, so they do not reach the transfer, burn or forced-transfer steps. The cause in V10 is not known, because the audit tool did not say what V10 changes.

**Affected functions**
- `mint`: the tracked balance is not updated.
- `_idBalance`: returns the stale value.
- `transfer`, `burn` and `forcedTransfer`: not confirmed, since the tests stop before them.

**How to reproduce**
1. Agent mints 100 tokens to Bob (`_mint(b, amt)`, where amt = CAP/10).
2. Run `assertTrackedEqualsReal()`. It fails with "idB tracked != real: 0 != 100".

The other three failing tests show the same mismatch for Alice's identity after minting to a1.

**Suggested fix**
Check how V10 changes the MaxBalanceModule's update on mint, and make the tracked balance increase by the minted amount. Re-run the four H3 tests on V10 and on C01.

Failing tests and reasons:
- `test_H3_rejectedTransferDoesNotDrift`: idB tracked != real: 0 != 100
- `test_H3_sameIdentityTransferKeepsTrackedTotal`: idA tracked != real: 0 != 100
- `test_H3_trackedMatchesRealAfterBurnAndForcedTransfer`: idA tracked != real: 0 != 100
- `test_H3_trackedMatchesRealAfterMintAndTransfers`: idA tracked != real: 0 != 100

Direct evidence: 4 of 4 failing tests.

Symptom hint: the module's tracked balance stayed at 0 after real mints, so the module is not being notified. Check that `compliance.getModules()` lists MaxBalanceModule.

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

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 2; cost paid $0.0036; cost when first made $0.0036; model seconds 27
- Demo wall time: 34 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
