# ComplyRWA audit report: V08

Audit target: configuration `V08` (cause hidden from the auditor). Model: haiku. Mode: live.

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
| J1 | 4 | 3 | FAIL |
| H1 | 4 | 0 | PASS |
| H3 | 4 | 0 | PASS |

## 3. Findings grouped by symptom

### Jurisdiction restriction not enforced (J1)

#### Rule J1: severity HIGH

**Violated policy**
Rule J1: investors registered in a restricted country may not receive tokens.

**What went wrong**
In all three tests, the call that should have been rejected succeeded. Bob's wallet `b` was moved to the restricted country, but minting to it and transferring tokens to it both went through. The output shows only "next call did not revert as expected," so the cause in V08 is not known. The configuration change was not provided.

**Affected functions**
- `token.mint` (receiver country check)
- `token.transfer` (receiver country check)
- `token.transferFrom` (receiver country check)

**How to reproduce**
Clearest test: `test_mintToRestrictedCountryIsBlocked`.
1. The agent calls `ir.updateCountry` to set Bob's wallet `b` to the restricted country (`RESTRICTED`).
2. The agent calls `token.mint(b, CAP / 10)`. The test expects "Compliance not followed". No revert occurred.

The other two tests (`test_transferToRestrictedCountryIsBlocked`, `test_transferFromToRestrictedCountryIsBlocked`) fail the same way. For a `transfer` or `transferFrom` revert, the message "Transfer not possible" is shared with KYC failures, so the output cannot show which check should have fired.

**Suggested fix**
Check that the country module is bound to `compliance` in V08 and that the restricted country is set. The cause cannot be confirmed from this output.

Failing tests and reasons:
- `test_mintToRestrictedCountryIsBlocked`: next call did not revert as expected
- `test_transferFromToRestrictedCountryIsBlocked`: next call did not revert as expected
- `test_transferToRestrictedCountryIsBlocked`: next call did not revert as expected

Direct evidence: 3 of 3 failing tests.

Reproducible test (generated):

```solidity
function test_mintToRestrictedCountryIsBlocked() public {
        uint256 amt = CAP / 10;

        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);

        uint256 supplyBefore = token.totalSupply();
        uint256 bBefore = token.balanceOf(b);

        vm.prank(agent);
        vm.expectRevert(bytes("Compliance not followed"));
        token.mint(b, amt);

        // Policy outcome: no new tokens were created for the restricted-country investor.
        assertEq(token.balanceOf(b), bBefore, "restricted-country investor was minted tokens");
        assertEq(token.totalSupply(), supplyBefore, "supply grew for a restricted-country receiver");
    }
```

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 1; cost paid $0.0010; cost when first made $0.0010; model seconds 7
- Demo wall time: 14 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
