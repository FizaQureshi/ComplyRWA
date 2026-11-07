// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../gold/GoldInvariants.t.sol";
import "../gold/GoldScenarios.t.sol";
import "../../variants/IdentityRegistryV01.sol";
import "../../variants/IdentityRegistryV06.sol";

// ---------- V01: OR instead of AND across required topics (K1)
abstract contract CfgV01 is ComplyFixture {
    uint256 internal constant TOPIC_2 = 2;

    function _newIdentityRegistry() internal virtual override returns (IdentityRegistry) {
        return IdentityRegistry(address(new IdentityRegistryV01()));
    }

    function _deployClaimIssuer() internal virtual override {
        super._deployClaimIssuer(); // issuer X, topic 1
        ctr.addClaimTopic(TOPIC_2);
        uint256[] memory both = new uint256[](2);
        both[0] = KYC_TOPIC;
        both[1] = TOPIC_2;
        tir.updateIssuerClaimTopics(IClaimIssuer(address(claimIssuer)), both);
    }

    function _registerInvestors() internal virtual override {
        super._registerInvestors(); // topic 1 for Alice, Bob, Carol
        _issueClaim(idA, a1, TOPIC_2, KYC_DATA);
        _issueClaim(idB, b, TOPIC_2, KYC_DATA);
        _issueClaim(idC, c, TOPIC_2, KYC_DATA);
        _issueClaim(idM, m); // Mallory: topic 1 ONLY, so she is NOT verified
    }
}
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
abstract contract CfgV06 is ComplyFixture {
    function _newIdentityRegistry() internal virtual override returns (IdentityRegistry) {
        return IdentityRegistry(address(new IdentityRegistryV06()));
    }
}
contract V06_Invariants is GoldInvariantsTest, CfgV06 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV06) returns (IdentityRegistry) { return CfgV06._newIdentityRegistry(); }
}
contract V06_Scenarios is GoldScenariosTest, CfgV06 {
    function _newIdentityRegistry() internal override(ComplyFixture, CfgV06) returns (IdentityRegistry) { return CfgV06._newIdentityRegistry(); }
}