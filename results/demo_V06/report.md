# ComplyRWA audit report: V06

Audit target: configuration `V06` (cause hidden from the auditor). Model: haiku. Mode: live.

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
In configuration V06, all three tests failed. After Bob's wallet was moved to the restricted country, mint, transfer and transferFrom to that wallet succeeded instead of reverting, so the restricted investor received tokens. The forge output shows only "did not revert", so it cannot be told whether a KYC or a compliance check would have caused the revert. What V06 changes is not known.

**Affected functions**
`token.mint`, `token.transfer`, `token.transferFrom`

**How to reproduce**
Clearest test: `test_transferToRestrictedCountryIsBlocked`.
1. Agent mints one tenth of the cap to Alice's first wallet (the cap value for V06 is not given).
2. Agent calls `ir.updateCountry` to set Bob's wallet to `RESTRICTED`.
3. Alice's first wallet calls `token.transfer` to Bob's wallet for the same amount.
4. Expected revert "Transfer not possible". Actual: the call succeeded.

The mint and transferFrom tests fail the same way.

**Suggested fix**
Check in V06 that the country restriction module is bound to `compliance` and that the restricted country setting is active. The cause is not visible in this output. Re-run the three tests; they must pass on all clean configurations.

Failing tests and reasons:
- `test_mintToRestrictedCountryIsBlocked`: next call did not revert as expected
- `test_transferFromToRestrictedCountryIsBlocked`: next call did not revert as expected
- `test_transferToRestrictedCountryIsBlocked`: next call did not revert as expected

Direct evidence: 3 of 3 failing tests.

Reproducible test (generated):

```solidity
function test_transferToRestrictedCountryIsBlocked() public {
        uint256 amt = CAP / 10;

        // Put Alice's wallet a1 in a position to send tokens.
        _mint(a1, amt);

        // Move the receiver into a restricted country.
        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);

        uint256 aBefore = token.balanceOf(a1);
        uint256 bBefore = token.balanceOf(b);

        vm.prank(a1);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(b, amt);

        // Policy outcome: no tokens moved to the restricted-country investor.
        assertEq(token.balanceOf(a1), aBefore, "sender balance changed on blocked transfer");
        assertEq(token.balanceOf(b), bBefore, "restricted-country investor received tokens");
    }
```

## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 1; cost paid $0.0011; cost when first made $0.0011; model seconds 7
- Demo wall time: 14 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
