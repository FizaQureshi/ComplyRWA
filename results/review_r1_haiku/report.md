# LLM-only review: review_r1_haiku

| measure | value |
|---|---|
| variants detected (official) | 13 of 13 = 100% |
| variants detected (strict, names the changed code) | 13 of 13 = 100% |
| variants detected (official, adjusted: ignoring stock-gap findings) | 13 of 13 = 100% |
| variants detected (strict, adjusted) | 13 of 13 = 100% |
| variants with any HIGH/MEDIUM finding | 13 of 13 |
| clean targets with a false positive | 7 of 8 = 88% |
| clean targets with a false positive (adjusted: ignoring stock-gap findings) | 2 of 8 = 25% |
| targets with a stock-gap finding (twin signature, S03) | 5 (C01 C02 C03 C06 C07) |
| false-positive findings on a rule outside the 10 listed | 0 |
| targets with no valid answer | 0 (none) |
| LLM calls (cut off) | 21 (0) |
| input / output tokens | 335,658 / 85,812 |
| cost USD | $0.0765 |
| model time (seconds) | 797 |

## Variants

| target | status | official | strict | rules flagged (HIGH/MEDIUM) | matched finding |
|---|---|---|---|---|---|
| V01 | ok | yes | yes | K1 K2 | K1 HIGH: IdentityRegistry.isVerified / Deployment._registerInvestors |
| V02 | ok | yes | yes | K1 | K1 HIGH: Deployment._registerInvestors (override) with ClaimIssuer.is |
| V03 | ok | yes | yes | K2 | K2 HIGH: ClaimIssuer.isClaimValid (ClaimIssuer.sol), called by Identi |
| V04 | ok | yes | yes | K1 K2 K3 | K3 HIGH: Deployment._deployClaimIssuer (override)  |
| V05 | ok | yes | yes | J1 J3 | J1 HIGH: Deployment._configureModules (overrides BaseSetup._configure |
| V06 | ok | yes | yes | J2 | J2 HIGH: IdentityRegistry.updateCountry |
| V07 | ok | yes | yes | J1 J2 J3 | J2 HIGH: Deployment._configureModules (override) -> ModularCompliance |
| V08 | ok | yes | yes | J1 J3 | J1 HIGH: Deployment._configureModules (overrides BaseSetup._configure |
| V09 | ok | yes | yes | H1 H2 | H1 HIGH: Deployment._configureModules |
| V10 | ok | yes | yes | H1 H2 | H2 HIGH: MaxBalanceModule._getIdentity / moduleMintAction / moduleTra |
| V11 | ok | yes | yes | H1 H3 | H1 HIGH: Deployment._addModules (setup override) with MaxBalanceModul |
| V12 | ok | yes | yes | H1 H3 | H3 HIGH: Token.forcedTransfer (also reached through Token.recoveryAdd |
| V13 | ok | yes | yes | H1 H4 | H4 HIGH: Deployment._configureModules (setup override) |

## Clean targets

| target | status | false positive | rules flagged (HIGH/MEDIUM) | first serious finding |
|---|---|---|---|---|
| C01 | ok | YES | K2 | K2 HIGH: ClaimIssuer.getRecoveredAddress / ClaimIssuer.isClaimValid / |
| C02 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / ClaimIs |
| C03 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / ClaimIs |
| C04 | ok | YES | J3 | J3 MEDIUM: Deployment setup (BaseSetup._deployComplianceAndToken, _addM |
| C05 | ok | no | - |  |
| C06 | ok | YES | K2 | K2 MEDIUM: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / ClaimIs |
| C07 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / Identit |
| C08 | ok | YES | J1 | J1 HIGH: Deployment._addModules (override, runs before super._addModu |

## How to read this

- The reviewer reads the code and setup of each target and lists rule breaks without running anything.
- Official detection needs a HIGH or MEDIUM finding on a linked rule. Strict detection also needs a word that names the changed code.
- A clean target with any HIGH or MEDIUM finding counts as a false positive.
- An empty, cut-off or invalid answer is never counted as 'no findings'.
- Stock-gap findings describe the twin-signature gap (S03 in Phase 3), a real gap of the ONCHAINID dependency that is not a seeded variant. Phase 3 kept it out of the detection and false-positive measures, so the adjusted rows ignore these findings. The rule was fixed after the first real answer and before the other answers existed. A finding that mixes S03 with a real bug would be dropped from the adjusted rows, which is the cautious direction.
