# ComplyRWA audit report: V12

Audit target: configuration `V12` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| H1 | 4 | 0 | PASS |
| H3 | 4 | 1 | FAIL |

## 3. Findings grouped by symptom

### Holding limit not enforced or tracked wrongly (H3)

#### Rule H3: severity HIGH

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

Failing tests and reasons:
- `test_H3_trackedMatchesRealAfterBurnAndForcedTransfer`: idA tracked != real: 75 != 50

Direct evidence: 1 of 1 failing tests.

Reproducible test (generated):

```solidity
function test_H3_trackedMatchesRealAfterBurnAndForcedTransfer() public {
        uint256 amt = CAP / 10;
        _mint(a1, amt);
        assertTrackedEqualsReal();

        vm.prank(agent);
        token.burn(a1, amt / 4);
        assertTrackedEqualsReal();

        vm.prank(agent);
        token.forcedTransfer(a1, b, amt / 4);
        assertTrackedEqualsReal();
    }
```

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 1; cost paid $0.0000; cost when first made $0.0014; model seconds 0
- Demo wall time: 0 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
