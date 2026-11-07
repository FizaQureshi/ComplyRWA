// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../gold/GoldInvariants.t.sol";
import "../gold/GoldScenarios.t.sol";
import "../../variants/IdentityRegistryV01.sol";
import "../../variants/IdentityRegistryV06.sol";
import "../../variants/ClaimIssuerV02.sol";
import "../../variants/ClaimIssuerV03.sol";
import "../../variants/MaxBalanceModuleV10.sol";

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

// ---------- V03: claim issuer ignores revocation (K2)
abstract contract CfgV03 is ComplyFixture {
    function _newClaimIssuer(address admin) internal virtual override returns (ClaimIssuer) {
        return ClaimIssuer(address(new ClaimIssuerV03(admin)));
    }
}
contract V03_Invariants is GoldInvariantsTest, CfgV03 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV03) returns (ClaimIssuer) { return CfgV03._newClaimIssuer(admin); }
}
contract V03_Scenarios is GoldScenariosTest, CfgV03 {
    function _newClaimIssuer(address admin) internal override(ComplyFixture, CfgV03) returns (ClaimIssuer) { return CfgV03._newClaimIssuer(admin); }
}

// ---------- V02: claim issuer accepts any signature (K1)
abstract contract CfgV02 is ComplyFixture {
    function _newClaimIssuer(address admin) internal virtual override returns (ClaimIssuer) {
        return ClaimIssuer(address(new ClaimIssuerV02(admin)));
    }

    function _registerInvestors() internal virtual override {
        super._registerInvestors();
        // Mallory adds a topic 1 claim signed by a random key that the issuer never trusted.
        // The stock issuer would refuse it ("invalid claim"). The V02 issuer accepts it.
        uint256 fakeKey = uint256(keccak256("not-the-issuer"));
        _issueClaimFrom(claimIssuer, fakeKey, idM, m, KYC_TOPIC, KYC_DATA);
    }
}
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
abstract contract CfgV10 is ComplyFixture {
    function _maxBalanceImpl() internal virtual override returns (address) {
        return address(new MaxBalanceModuleV10());
    }
}
contract V10_Invariants is GoldInvariantsTest, CfgV10 {
    function setUp() public override(GoldInvariantsTest, ComplyFixture) { GoldInvariantsTest.setUp(); }
    function _maxBalanceImpl() internal override(ComplyFixture, CfgV10) returns (address) { return CfgV10._maxBalanceImpl(); }
}
contract V10_Scenarios is GoldScenariosTest, CfgV10 {
    function _maxBalanceImpl() internal override(ComplyFixture, CfgV10) returns (address) { return CfgV10._maxBalanceImpl(); }
}