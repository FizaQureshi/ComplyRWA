// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../gold/GoldInvariants.t.sol";
import "../gold/GoldScenarios.t.sol";
import "../configs/VariantCfgs.sol";

/// @notice Wave 1 variants (configuration only): V04, V05, V07, V08, V09, V11, V13.
/// The configuration contracts (CfgV04 ...) now live in test/configs/VariantCfgs.sol.
/// This file only combines each one with the gold suites.

// ---------- V04: no required claim topic (K3)
contract V04_Invariants is GoldInvariantsTest, CfgV04 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _deployClaimIssuer() internal override(ComplyFixture, CfgV04) { CfgV04._deployClaimIssuer(); }
}
contract V04_Scenarios is GoldScenariosTest, CfgV04 {
    function _deployClaimIssuer() internal override(ComplyFixture, CfgV04) { CfgV04._deployClaimIssuer(); }
}

// ---------- V05: wrong country restricted, 410 instead of 408 (J1)
contract V05_Invariants is GoldInvariantsTest, CfgV05 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV05) { CfgV05._configureModules(); }
}
contract V05_Scenarios is GoldScenariosTest, CfgV05 {
    function _configureModules() internal override(ComplyFixture, CfgV05) { CfgV05._configureModules(); }
}

// ---------- V07: country module removed after setup (J3)
contract V07_Invariants is GoldInvariantsTest, CfgV07 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV07) { CfgV07._configureModules(); }
}
contract V07_Scenarios is GoldScenariosTest, CfgV07 {
    function _configureModules() internal override(ComplyFixture, CfgV07) { CfgV07._configureModules(); }
}

// ---------- V08: country module bound, no country restricted (J3)
contract V08_Invariants is GoldInvariantsTest, CfgV08 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV08) { CfgV08._configureModules(); }
}
contract V08_Scenarios is GoldScenariosTest, CfgV08 {
    function _configureModules() internal override(ComplyFixture, CfgV08) { CfgV08._configureModules(); }
}

// ---------- V09: MaxBalanceModule removed (H1)
contract V09_Invariants is GoldInvariantsTest, CfgV09 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV09) { CfgV09._configureModules(); }
}
contract V09_Scenarios is GoldScenariosTest, CfgV09 {
    function _configureModules() internal override(ComplyFixture, CfgV09) { CfgV09._configureModules(); }
}

// ---------- V13: cap set to type(uint256).max (H4)
contract V13_Invariants is GoldInvariantsTest, CfgV13 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _configureModules() internal override(ComplyFixture, CfgV13) { CfgV13._configureModules(); }
}
contract V13_Scenarios is GoldScenariosTest, CfgV13 {
    function _configureModules() internal override(ComplyFixture, CfgV13) { CfgV13._configureModules(); }
}

// ---------- V11: Bob holds 800, preset says 0 (H3). Properties only, because the start state has balances.
contract V11_Invariants is GoldInvariantsTest, CfgV11 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _addModules() internal override(ComplyFixture, CfgV11) { CfgV11._addModules(); }
}
