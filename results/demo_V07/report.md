# ComplyRWA audit report: V07

Audit target: configuration `V07` (cause hidden from the auditor). Model: haiku. Mode: live.

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

Violated policy
Rule J1: investors registered in a restricted country may not receive tokens.

What went wrong
In configuration V07, all three tests failed. Each expects a revert when Bob's wallet is moved into the restricted country, but no revert happened. So tokens could reach a restricted-country investor through mint, transfer and transferFrom. The configuration change is not provided, so the cause is not known. The output does not show whether the expected "Transfer not possible" would have been a KYC or a rule failure, so this cannot be told.

Affected functions
token.mint, token.transfer, token.transferFrom. token.forcedTransfer is not tested here.

How to reproduce
Clearest test: test_mintToRestrictedCountryIsBlocked.
1. Agent calls ir.updateCountry for Bob's wallet, setting the restricted country.
2. Agent calls token.mint to Bob's wallet for one tenth of the cap.
3. Expected: revert "Compliance not followed". Observed: no revert, so the test failed.

The transfer and transferFrom tests fail the same way.

Suggested fix
Not known from the input. Check what V07 changes in the country rule settings and confirm the country module is still bound to compliance in V07.

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

- Explainer LLM calls this run: 1; cost paid $0.0012; cost when first made $0.0012; model seconds 9
- Demo wall time: 16 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
