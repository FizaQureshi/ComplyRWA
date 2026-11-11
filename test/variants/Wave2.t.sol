// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../gold/GoldInvariants.t.sol";
import "../gold/GoldScenarios.t.sol";
import "../configs/VariantCfgs.sol";

/// @notice Wave 2 variants (code copies in variants/): V01, V02, V03, V06, V10, V12.
/// The configuration contracts (CfgV01 ...) now live in test/configs/VariantCfgs.sol, which also
/// imports the copied contracts from variants/. This file only combines each one with the gold suites.

// ---------- V01: OR instead of AND across required topics (K1)
contract V01_Invariants is GoldInvariantsTest, CfgV01 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV01) returns (IdentityRegistry) { return CfgV01._newIdentityRegistry(); }
    function _deployClaimIssuer() internal override(ComplyFixture, CfgV01) { CfgV01._deployClaimIssuer(); }
    function _registerInvestors() internal override(ComplyFixture, CfgV01) { CfgV01._registerInvestors(); }
}
contract V01_Scenarios is GoldScenariosTest, CfgV01 {
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV01) returns (IdentityRegistry) { return CfgV01._newIdentityRegistry(); }
    function _deployClaimIssuer() internal override(ComplyFixture, CfgV01) { CfgV01._deployClaimIssuer(); }
    function _registerInvestors() internal override(ComplyFixture, CfgV01) { CfgV01._registerInvestors(); }
}

// ---------- V06: registry ignores updateCountry (J2)
contract V06_Invariants is GoldInvariantsTest, CfgV06 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV06) returns (IdentityRegistry) { return CfgV06._newIdentityRegistry(); }
}
contract V06_Scenarios is GoldScenariosTest, CfgV06 {
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV06) returns (IdentityRegistry) { return CfgV06._newIdentityRegistry(); }
}

// ---------- V03: claim issuer ignores revocation (K2)
contract V03_Invariants is GoldInvariantsTest, CfgV03 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV03) returns (ClaimIssuer) { return CfgV03._newClaimIssuer(admin); }
}
contract V03_Scenarios is GoldScenariosTest, CfgV03 {
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV03) returns (ClaimIssuer) { return CfgV03._newClaimIssuer(admin); }
}

// ---------- V02: claim issuer accepts any signature (K1)
contract V02_Invariants is GoldInvariantsTest, CfgV02 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV02) returns (ClaimIssuer) { return CfgV02._newClaimIssuer(admin); }
    function _registerInvestors() internal override(ComplyFixture, CfgV02) { CfgV02._registerInvestors(); }
}
contract V02_Scenarios is GoldScenariosTest, CfgV02 {
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV02) returns (ClaimIssuer) { return CfgV02._newClaimIssuer(admin); }
    function _registerInvestors() internal override(ComplyFixture, CfgV02) { CfgV02._registerInvestors(); }
}

// ---------- V10: cap keyed by wallet instead of identity (H2)
contract V10_Invariants is GoldInvariantsTest, CfgV10 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _maxBalanceImpl() internal override(ComplyFixture, CfgV10) returns (address) { return CfgV10._maxBalanceImpl(); }
}
contract V10_Scenarios is GoldScenariosTest, CfgV10 {
    function _maxBalanceImpl() internal override(ComplyFixture, CfgV10) returns (address) { return CfgV10._maxBalanceImpl(); }
}

// ---------- V12: forcedTransfer does not notify compliance (H3)
contract V12_Invariants is GoldInvariantsTest, CfgV12 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newToken() internal override(ComplyFixture, CfgV12) returns (Token) { return CfgV12._newToken(); }
}
contract V12_Scenarios is GoldScenariosTest, CfgV12 {
    function _newToken() internal override(ComplyFixture, CfgV12) returns (Token) { return CfgV12._newToken(); }
}
