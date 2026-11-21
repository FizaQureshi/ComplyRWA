# ComplyRWA Audit Report (SAMPLE)

**Audit:** audit-2026-11-12-001  |  **Target:** T-REX 4.1.6 (`a09cfd3`), config "V13 (sample)"  |  **Verdict: FAIL**

## Summary

5 rules checked, 10 properties generated, 9 valid, 1 rejected by the validity filter.
8 valid properties passed and 1 failed. 1 finding: **1 high**.

## Policy checked

| ID | Category | Rule |
|---|---|---|
| R1 | KYC | Only investors with a valid KYC claim from a trusted issuer may receive tokens. |
| R2 | KYC | At least one KYC claim topic must be required. |
| R3 | Jurisdiction | Investors registered in a restricted country (408) may not receive tokens. |
| R4 | Holding limit | No investor may hold more than 1000 tokens. |
| R5 | Holding limit | The holding-limit module's balance records must match the real token balances. |

## Findings

### F1 (HIGH): Holding limit can be exceeded: the cap is not enforced

**Rule violated (R4):** No investor may hold more than 1000 tokens.

**What happened:** The holding-limit module is bound, but its cap was set to the largest possible number, so it never blocks anything. Bob received 1200 tokens, which is above the 1000 limit in your policy.

**Affected functions:** `Token.mint`, `Token.transfer`, `MaxBalanceModule.moduleCheck`, `MaxBalanceModule.setMaxBalance`

**Steps to reproduce**

1. Agent calls `Token.mint(bob, 1200)`. Result: success.
2. `Token.balanceOf(bob)` returns 1200.
3. Check `balanceOf(bob) <= 1000`. Result: **FAILED** (1200 > 1000).

**Reproduce command:**
```
forge test --match-path out/generated/ComplyGenerated.t.sol --match-test invariant_capNotExceeded -vvv
```
Fuzz seed: `0x436f6d706c79`

**Suggested fix:** Set the cap to the intended number through `ModularCompliance.callModuleFunction` (`setMaxBalance(1000)`). Check the token's decimals when you write the number.

## Properties

| ID | Rule | Property | Status |
|---|---|---|---|
| P1 | R1 | invariant_receiverIsVerifiedAfterTransfer | passed |
| P2 | R1 | invariant_receiverIsVerifiedAfterMint | passed |
| P3 | R2 | test_claimTopicsNotEmpty | passed |
| P4 | R2 | test_unverifiedWalletCannotReceive | passed |
| P5 | R3 | invariant_noRestrictedCountryReceiverOnTransfer | passed |
| P6 | R3 | invariant_noRestrictedCountryReceiverOnMint | passed |
| P7 | R4 | invariant_capNotExceeded | **failed** |
| P8 | R5 | invariant_trackedEqualsRealAfterTransfer | passed |
| P9 | R5 | invariant_trackedEqualsRealAfterMintBurnForced | passed |
| P10 | R1 | test_everyoneCanReceive | rejected (contradicts the policy on the clean baseline) |

## Cost

236,000 input tokens, 28,400 output tokens, about $0.76, 210 seconds.
