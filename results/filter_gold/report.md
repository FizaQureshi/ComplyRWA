| contract | test | outcome | reason | notes |
|---|---|---|---|---|
| GoldInvariantsTest | invariant_G01a_transferReceiverIsVerified | KEEP | fails on variants: V01 V02 V03 V04 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G01b_mintAndForcedReceiverIsVerified | KEEP | fails on variants: V01 V02 V03 V04 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G03a_transferReceiverNotRestricted | KEEP | fails on variants: V05 V06 V07 V08 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G03b_mintReceiverNotRestricted | KEEP | fails on variants: V05 V06 V07 V08 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G04_noIdentityAboveCap | KEEP | fails on variants: V09 V10 V11 V12 V13 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G05a_trackedEqualsRealAfterTransfer | KEEP | fails on variants: V09 V10 V11 V12 | ran on 8/8 clean, 13/13 variants |
| GoldInvariantsTest | invariant_G05b_trackedEqualsRealAfterMintBurnForced | KEEP | fails on variants: V09 V10 V11 V12 | ran on 8/8 clean, 13/13 variants |
| GoldScenariosTest | test_G02a_requiredTopicsNotEmpty | KEEP | fails on variants: V04 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G02b_registeredWalletWithoutClaimCannotReceive | KEEP | fails on variants: V01 V02 V04 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G05b_recoveryKeepsTrackedBalance | KEEP | fails on variants: V09 V10 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G06a_deleteIdentityBlocksReceiving | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G06b_removeTrustedIssuerBlocksReceiving | KEEP | fails on variants: V04 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G06c_revokedClaimBlocksReceiving | KEEP | fails on variants: V01 V02 V03 V04 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G07_countryChangeBlocksReceiving | KEEP | fails on variants: V05 V06 V07 V08 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G08_countryModuleBoundAndConfigured | KEEP | fails on variants: V05 V07 V08 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G09_walletsOfOneIdentityShareTheCap | KEEP | fails on variants: V09 V10 V13 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G10_capEqualsPolicyNumber | KEEP | fails on variants: V09 V13 | ran on 5/8 clean, 12/13 variants |
| GoldScenariosTest | test_G13_forcedTransferToRestrictedCountryIsKnownException | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
