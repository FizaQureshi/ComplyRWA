# ComplyRWA audit report: V05

Audit target: configuration `V05` (cause hidden from the auditor). Model: haiku. Mode: live.

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
In configuration V05, three ways of sending tokens to a restricted-country investor succeeded when they should have been blocked. Each test expected a revert, and none happened. The tests target the rule failure, not KYC, since Bob holds a KYC claim. The cause in V05 is not known, because the audit tool did not describe the configuration change.

Affected functions
token.mint, token.transfer, token.transferFrom

How to reproduce
Steps from test_mintToRestrictedCountryIsBlocked:
1. Agent calls ir.updateCountry(b, RESTRICTED), so Bob is in the restricted country.
2. The test records total supply and Bob's balance.
3. Agent calls token.mint(b, CAP / 10). In C01 that is 100 tokens. V05's cap is not given.
4. The test expects the revert "Compliance not followed". The call did not revert.
5. Bob received new tokens and supply grew, so the balance checks fail.

The other two tests, test_transferFromToRestrictedCountryIsBlocked and test_transferToRestrictedCountryIsBlocked, failed the same way: the expected "Transfer not possible" revert did not occur.

Suggested fix
In V05, check that the country restriction module is bound to compliance and that the restricted-country variable is set as intended. The output does not confirm the cause.

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

- Explainer LLM calls this run: 1; cost paid $0.0000; cost when first made $0.0012; model seconds 0
- Demo wall time: 0 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
