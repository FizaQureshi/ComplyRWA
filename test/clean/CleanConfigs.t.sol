// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../gold/GoldInvariants.t.sol";
import "../gold/GoldScenarios.t.sol";
import "../configs/CleanCfgs.sol";

/// @notice Clean (non-vulnerable) configurations C02 to C08 (C01 is the baseline itself).
/// Every gold test must PASS on every one of them. They measure the false-positive rate.
/// The configuration contracts (Cfg02 ... Cfg08) now live in test/configs/CleanCfgs.sol.
/// This file only combines each one with the property suite (`_Invariants`) and, where the
/// start state allows, the scenario suite (`_Scenarios`). See Phase2.md section 8.

// ============================================================ C02: two topics, two issuers
contract C02_Invariants is GoldInvariantsTest, Cfg02 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _deployClaimIssuer() internal override(ComplyFixture, Cfg02) {
        Cfg02._deployClaimIssuer();
    }
    function _registerInvestors() internal override(ComplyFixture, Cfg02) {
        Cfg02._registerInvestors();
    }
}
contract C02_Scenarios is GoldScenariosTest, Cfg02 {
    function _deployClaimIssuer() internal override(ComplyFixture, Cfg02) {
        Cfg02._deployClaimIssuer();
    }
    function _registerInvestors() internal override(ComplyFixture, Cfg02) {
        Cfg02._registerInvestors();
    }
}

// ====================================== C03: same-identity move is rejected (start state)
contract C03_Invariants is GoldInvariantsTest, Cfg03 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _afterSetUp() internal override(ComplyFixture, Cfg03) {
        Cfg03._afterSetUp();
    }
}

// ============================ C04: agent forcedTransfer to a restricted country (start state)
contract C04_Invariants is GoldInvariantsTest, Cfg04 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _afterSetUp() internal override(ComplyFixture, Cfg04) {
        Cfg04._afterSetUp();
    }
}

// ================================ C05: different valid numbers (cap 500, 408 and 643 restricted)
contract C05_Invariants is GoldInvariantsTest, Cfg05 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _configure() internal override(ComplyFixture, Cfg05) {
        Cfg05._configure();
    }
}
contract C05_Scenarios is GoldScenariosTest, Cfg05 {
    function _configure() internal override(ComplyFixture, Cfg05) {
        Cfg05._configure();
    }
}

// ================================ C06: claim revoked, then re-issued with different data
contract C06_Invariants is GoldInvariantsTest, Cfg06 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _registerInvestors() internal override(ComplyFixture, Cfg06) {
        Cfg06._registerInvestors();
    }
}
contract C06_Scenarios is GoldScenariosTest, Cfg06 {
    function _registerInvestors() internal override(ComplyFixture, Cfg06) {
        Cfg06._registerInvestors();
    }
}

// ============================ C07: receiving exactly up to the cap (start state)
contract C07_Invariants is GoldInvariantsTest, Cfg07 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _afterSetUp() internal override(ComplyFixture, Cfg07) {
        Cfg07._afterSetUp();
    }
}

// ================ C08: module bound to a token that already has holders, with a CORRECT preset
contract C08_Invariants is GoldInvariantsTest, Cfg08 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) {
        GoldInvariantsTest.setUp();
    }
    function _addModules() internal override(ComplyFixture, Cfg08) {
        Cfg08._addModules();
    }
}
contract C08_Scenarios is GoldScenariosTest, Cfg08 {
    function _addModules() internal override(ComplyFixture, Cfg08) {
        Cfg08._addModules();
    }
}
