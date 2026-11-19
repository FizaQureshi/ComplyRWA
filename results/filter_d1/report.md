| contract | test | outcome | reason | notes |
|---|---|---|---|---|
| Cand_K1_d1 | test_mintToUnverifiedWalletReverts | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K1_d1 | test_transferToUnverifiedWalletReverts | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K1_d1 | test_transferToVerifiedInvestorWorks | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_K1_d1 | test_transferToWalletWithRevokedClaimReverts | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_d1 | test_K3_mintToUnclaimedWalletRejected | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_d1 | test_K3_requiredTopicsNonEmptyAndIncludeKyc | KEEP | fails on variants: V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_d1 | test_K3_transferToKycWalletWorks | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_K3_d1 | test_K3_transferToUnclaimedWalletRejected | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_d1 | test_mintToRestrictedCountryIsBlocked | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_d1 | test_transferFromToRestrictedCountryIsBlocked | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_d1 | test_transferToAllowedCountryStillWorks | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_J1_d1 | test_transferToRestrictedCountryIsBlocked | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_d1 | test_H3_rejectedTransferDoesNotDrift | KEEP | fails on variants: V01 V02 V03 V04 V09 V10 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_d1 | test_H3_sameIdentityTransferKeepsTrackedTotal | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_d1 | test_H3_trackedMatchesRealAfterBurnAndForcedTransfer | KEEP | fails on variants: V09 V10 V12 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_d1 | test_H3_trackedMatchesRealAfterMintAndTransfers | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
