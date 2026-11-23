# ComplyRWA audit report: V13

Audit target: configuration `V13` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| H1 | 4 | 2 | FAIL |
| H3 | 4 | 0 | PASS |

## 3. Findings grouped by symptom

### Holding limit not enforced or tracked wrongly (H1)

#### Rule H1: severity HIGH

Violated policy
H1: No investor may hold more than the maximum allowed number of tokens.

What went wrong
The changes in V13 are not known. The output does not say which assertion failed. The likely reading is that an over-cap call succeeded, so the cap was not enforced. This is not a known exception, because both calls raise holdings above the cap through an ordinary mint or transfer.

Affected functions
token.mint and token.transfer. The cap check in MaxBalanceModule is not shown in the output.

How to reproduce
Clearest test: test_mintPastCapIsRefused.
1. The agent mints Bob "room + 1" tokens, where room is the cap minus Bob's identity balance. The cap value for V13 is not given.
2. The test expects the call to fail and Bob's balances to stay unchanged.

Also failing: test_transferToSecondWalletCannotExceedIdentityCap. It moves tokens from Bob to Alice's second wallet, which pushes Alice's shared identity one token over the cap.

Suggested fix
Confirm which assertion failed and whether the cap module is bound to compliance under V13. Check that both the mint path and the transfer path test the identity's total balance against the cap.

Failing tests and reasons:
- `test_mintPastCapIsRefused`: assertion failed
- `test_transferToSecondWalletCannotExceedIdentityCap`: assertion failed

Direct evidence: 2 of 2 failing tests.

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

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 1; cost paid $0.0014; cost when first made $0.0014; model seconds 11
- Demo wall time: 18 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
