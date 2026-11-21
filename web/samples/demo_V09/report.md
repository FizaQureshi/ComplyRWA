# ComplyRWA audit report: V09

Audit target: configuration `V09` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| H1 | 4 | 4 | FAIL |
| H3 | 4 | 4 | FAIL |

## 3. Findings grouped by symptom

### Holding limit not enforced or tracked wrongly (H1, H3)

#### Rule H1: severity HIGH

Violated policy
Rule H1: No investor may hold more than the maximum allowed number of tokens.

What went wrong
In V09, the holding cap appears not to be enforced. `test_mintPastCapIsRefused` expects a mint that takes Bob above the cap to be refused. The failure shows the call was not refused. `test_transferToSecondWalletCannotExceedIdentityCap` shows the same gap across Alice's two wallets. The two "0 != 500" failures do not show which line failed, so their cause cannot be told from the output.

Affected functions
Token.mint and Token.transfer, through the MaxBalanceModule cap check. The cause in V09 is not known, because the audit tool did not describe what the configuration changes.

How to reproduce (test_mintPastCapIsRefused)
1. Read Bob's identity balance (idB) and compute room = CAP minus that balance.
2. The agent mints room + 1 tokens to Bob.
3. Expected: the call is refused. Observed: the call succeeds, so the assertFalse(ok) check fails.

The transfer test fails the same way on Alice's second wallet.

Suggested fix
Check that MaxBalanceModule is bound to compliance in V09 and that its cap check runs on both mint and transfer. Confirm the cap value for V09, which is not given in the inputs. Rerun all four tests.

Failing tests and reasons:
- `test_mintPastCapIsRefused`: assertion failed
- `test_mintWithinCapSucceeds`: assertion failed: 0 != 500 (side effect: the module's counter did not move)
- `test_transferToSecondWalletCannotExceedIdentityCap`: assertion failed
- `test_transferWithinIdentityCapSucceeds`: assertion failed: 0 != 500 (side effect: the module's counter did not move)

Direct evidence: 2 of 4 failing tests.

Reproducible test (generated):

```solidity
function test_mintPastCapIsRefused() public {
        uint256 bal = _idBalance(idB);
        assertTrue(bal <= CAP);
        uint256 room = CAP - bal;
        uint256 pre = token.balanceOf(b);

        vm.prank(agent);
        (bool ok, ) = address(token).call(abi.encodeWithSelector(Token.mint.selector, b, room + 1));

        assertFalse(ok);
        assertEq(token.balanceOf(b), pre);
        assertEq(_idBalance(idB), bal);
    }
```

#### Rule H3: severity HIGH

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

Failing tests and reasons:
- `test_H3_rejectedTransferDoesNotDrift`: idB tracked != real: 0 != 100
- `test_H3_sameIdentityTransferKeepsTrackedTotal`: idA tracked != real: 0 != 100
- `test_H3_trackedMatchesRealAfterBurnAndForcedTransfer`: idA tracked != real: 0 != 100
- `test_H3_trackedMatchesRealAfterMintAndTransfers`: idA tracked != real: 0 != 100

Direct evidence: 4 of 4 failing tests.

Symptom hint: the module's tracked balance stayed at 0 after real mints, so the module is not being notified. Check that `compliance.getModules()` lists MaxBalanceModule.

Reproducible test (generated):

```solidity
function test_H3_trackedMatchesRealAfterMintAndTransfers() public {
        uint256 amt = CAP / 10;
        _mint(a1, amt);
        _mint(b, amt);
        assertTrackedEqualsReal();

        uint256 bBefore = token.balanceOf(b);
        _transfer(a1, b, amt / 2);
        assertEq(token.balanceOf(b), bBefore + amt / 2, "b did not receive tokens");
        assertTrackedEqualsReal();

        _transfer(a1, a2, amt / 4);
        assertTrackedEqualsReal();
    }
```

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 2; cost paid $0.0000; cost when first made $0.0030; model seconds 0
- Demo wall time: 1 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
