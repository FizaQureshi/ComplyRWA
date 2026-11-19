| contract | test | outcome | reason | notes |
|---|---|---|---|---|
| Cand_K1_s1 | test_noKycClaimCannotReceive | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K1_s1 | test_revokedClaimCannotReceive | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K1_s1 | test_unregisteredWalletCannotReceive | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_K1_s1 | test_verifiedInvestorCanReceiveTransfer | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_K2_s1 | test_revoked_wallet_cannot_receive_mint | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K2_s1 | test_revoked_wallet_cannot_receive_transfer | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K2_s1 | test_revoked_wallet_cannot_receive_via_transferFrom | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K2_s1 | test_unrevoked_investor_still_receives_after_other_revocation | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_K3_s1 | test_identityWithoutClaimCannotReceive | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_s1 | test_requiredTopicsListNotEmpty | KEEP | fails on variants: V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_s1 | test_revokedClaimBlocksReceiving | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| Cand_K3_s1 | test_verifiedInvestorsStillWork | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_J1_s1 | test_countryChangeBlocksAndUnblocksReceiving | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_s1 | test_mintToRestrictedCountryInvestorReverts | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_s1 | test_transferFromToRestrictedCountryInvestorReverts | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J1_s1 | test_transferToRestrictedCountryInvestorReverts | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J2_s1 | test_changeToUnrestrictedCountryStillReceives | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_J2_s1 | test_mintBlockedAfterCountryChangedToRestricted | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J2_s1 | test_receiveWorksBeforeBlockedDuringAndAllowedAfterRestore | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J2_s1 | test_transferBlockedAfterCountryChangedToRestricted | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J3_s1 | test_countryChangeToRestrictedBlocksReceiving | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J3_s1 | test_countryModuleIsBoundToCompliance | KEEP | fails on variants: V07 | ran on 5/8 clean, 12/13 variants |
| Cand_J3_s1 | test_mintToRestrictedCountryReverts | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_J3_s1 | test_transferToRestrictedBlockedButAllowedWorks | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| Cand_H1_s1 | test_mintAboveCapReverts | KEEP | fails on variants: V09 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H1_s1 | test_mintToSecondWalletOfSameIdentityOverCapReverts | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H1_s1 | test_smallTransferWithinCapWorks | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_H1_s1 | test_transferPushingIdentityOverCapReverts | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H2_s1 | test_mintToSecondWalletCountsAgainstSameIdentityCap | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H2_s1 | test_transferBetweenOwnWalletsAllowed | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| Cand_H2_s1 | test_transferFromOtherIdentityToSecondWalletRespectsSharedCap | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H2_s1 | test_twoWalletsCanFillCapButNotExceed | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_s1 | test_burnAndSameIdentityTransferKeepTrackedEqualReal | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_s1 | test_forcedTransferKeepsTrackedEqualReal | KEEP | fails on variants: V09 V10 V12 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_s1 | test_mintKeepsTrackedEqualReal | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
| Cand_H3_s1 | test_transferBetweenIdentitiesKeepsTrackedEqualReal | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
| Cand_H4_s1 | test_cap_cumulativeEnforced | KEEP | fails on variants: V09 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H4_s1 | test_cap_exactBoundary | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H4_s1 | test_mintAboveCapBlocked | KEEP | fails on variants: V09 V13 | ran on 5/8 clean, 12/13 variants |
| Cand_H4_s1 | test_normalMintBelowCapWorks | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
