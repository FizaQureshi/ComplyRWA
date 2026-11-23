# LLM-only review: review_r1b_haiku

| measure | value |
|---|---|
| variants detected (official) | 13 of 13 = 100% |
| variants detected (strict, names the changed code) | 13 of 13 = 100% |
| variants detected (official, adjusted: ignoring stock-gap findings) | 13 of 13 = 100% |
| variants detected (strict, adjusted) | 13 of 13 = 100% |
| variants with any HIGH/MEDIUM finding | 13 of 13 |
| clean targets with a false positive | 5 of 8 = 62% |
| clean targets with a false positive (adjusted: ignoring stock-gap findings) | 1 of 8 = 12% |
| targets with a stock-gap finding (twin signature, S03) | 5 (C01 C03 C05 C07 V06) |
| false-positive findings on a rule outside the 10 listed | 0 |
| targets with no valid answer | 0 (none) |
| LLM calls (cut off) | 21 (0) |
| input / output tokens | 335,658 / 86,024 |
| cost USD | $0.0766 |
| model time (seconds) | 401 |

## Variants

| target | status | official | strict | rules flagged (HIGH/MEDIUM) | matched finding |
|---|---|---|---|---|---|
| V01 | ok | yes | yes | K1 K2 | K1 HIGH: IdentityRegistry.isVerified (with Deployment._registerInvest |
| V02 | ok | yes | yes | K1 K2 | K1 HIGH: ClaimIssuer.isClaimValid (used by IdentityRegistry.isVerifie |
| V03 | ok | yes | yes | K2 | K2 HIGH: ClaimIssuer.isClaimValid (node_modules/@onchain-id ClaimIssu |
| V04 | ok | yes | yes | K1 K2 K3 | K1 HIGH: Deployment._deployClaimIssuer (setup override), IdentityRegi |
| V05 | ok | yes | yes | J1 J2 J3 | J1 HIGH: Deployment._configureModules (overrides BaseSetup._configure |
| V06 | ok | yes | yes | J2 K2 | J2 HIGH: IdentityRegistry.updateCountry |
| V07 | ok | yes | yes | J1 J2 J3 | J2 HIGH: IdentityRegistry.updateCountry / ModularCompliance.canTransf |
| V08 | ok | yes | yes | J1 J2 J3 | J1 HIGH: Deployment._configureModules (overrides BaseSetup._configure |
| V09 | ok | yes | yes | H1 H2 H3 | H1 HIGH: Deployment._configureModules |
| V10 | ok | yes | yes | H1 H2 | H2 HIGH: MaxBalanceModule._getIdentity (used by moduleCheck, moduleMi |
| V11 | ok | yes | yes | H1 H3 | H1 HIGH: Deployment._addModules (setup override) with MaxBalanceModul |
| V12 | ok | yes | yes | H1 H3 | H3 HIGH: Token.forcedTransfer (also reached via Token.recoveryAddress |
| V13 | ok | yes | yes | H1 H4 | H4 HIGH: Deployment._configureModules |

## Clean targets

| target | status | false positive | rules flagged (HIGH/MEDIUM) | first serious finding |
|---|---|---|---|---|
| C01 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimRevoked / Claim |
| C02 | ok | YES | J3 | J3 MEDIUM: BaseSetup._deployComplianceAndToken / ModularCompliance.only |
| C03 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / ClaimIs |
| C04 | ok | no | - |  |
| C05 | ok | YES | K2 | K2 HIGH: ClaimIssuer.revokeClaim / ClaimIssuer.isClaimValid / ClaimIs |
| C06 | ok | no | - |  |
| C07 | ok | YES | K2 | K2 HIGH: ClaimIssuer.isClaimValid / ClaimIssuer.revokeClaim / Identit |
| C08 | ok | no | - |  |

## How to read this

- The reviewer reads the code and setup of each target and lists rule breaks without running anything.
- Official detection needs a HIGH or MEDIUM finding on a linked rule. Strict detection also needs a word that names the changed code.
- A clean target with any HIGH or MEDIUM finding counts as a false positive.
- An empty, cut-off or invalid answer is never counted as 'no findings'.
- Stock-gap findings describe the twin-signature gap (S03 in Phase 3), a real gap of the ONCHAINID dependency that is not a seeded variant. Phase 3 kept it out of the detection and false-positive measures, so the adjusted rows ignore these findings. The rule was fixed after the first real answer and before the other answers existed. A finding that mixes S03 with a real bug would be dropped from the adjusted rows, which is the cautious direction.
