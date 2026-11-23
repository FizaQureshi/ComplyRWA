# ComplyRWA audit findings (blind configuration text)

| configuration | rule | severity | failing tests | checks |
|---|---|---|---|---|
| V09 | H1 | HIGH | 4 | ok |
| V09 | H3 | HIGH | 4 | ok |

## Configuration V09

### Rule H1 (tests from batch d2: test_mintPastCapIsRefused, test_mintWithinCapSucceeds, test_transferToSecondWalletCannotExceedIdentityCap, test_transferWithinIdentityCapSucceeds)

Severity: HIGH

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

