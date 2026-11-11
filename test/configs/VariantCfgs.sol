// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../ComplyFixture.sol";
import "../../variants/IdentityRegistryV01.sol";
import "../../variants/IdentityRegistryV06.sol";
import "../../variants/ClaimIssuerV02.sol";
import "../../variants/ClaimIssuerV03.sol";
import "../../variants/MaxBalanceModuleV10.sol";
import "../../variants/TokenV12.sol";

/// @notice Seeded vulnerable variants V01 to V13.
/// Moved here from test/variants/Wave1.t.sol and Wave2.t.sol (Phase 4, step 4.0) so that any test
/// file, including generated ones, can import them and run on a variant.
/// The list of hooks per variant is recorded in pipeline/configs.json and checked by
/// pipeline/check_manifest.py.

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

// ---------- V03: claim issuer ignores revocation (K2)
abstract contract CfgV03 is ComplyFixture {
    function _newClaimIssuer(address admin) internal virtual override returns (ClaimIssuer) {
        return ClaimIssuer(address(new ClaimIssuerV03(admin)));
    }
}

// ---------- V04: no required claim topic (K3)
abstract contract CfgV04 is ComplyFixture {
    function _deployClaimIssuer() internal virtual override {
        super._deployClaimIssuer();
        ctr.removeClaimTopic(KYC_TOPIC);
    }
}

// ---------- V05: wrong country restricted, 410 instead of 408 (J1)
abstract contract CfgV05 is ComplyFixture {
    function _configureModules() internal virtual override {
        _restrictCountry(410);
        _setCap(CAP);
    }
}

// ---------- V06: registry ignores updateCountry (J2)
abstract contract CfgV06 is ComplyFixture {
    function _newIdentityRegistry() internal virtual override returns (IdentityRegistry) {
        return IdentityRegistry(address(new IdentityRegistryV06()));
    }
}

// ---------- V07: country module removed after setup (J3)
abstract contract CfgV07 is ComplyFixture {
    function _configureModules() internal virtual override {
        super._configureModules();
        compliance.removeModule(address(countryModule));
    }
}

// ---------- V08: country module bound, no country restricted (J3)
abstract contract CfgV08 is ComplyFixture {
    function _configureModules() internal virtual override {
        _setCap(CAP);
    }
}

// ---------- V09: MaxBalanceModule removed (H1)
abstract contract CfgV09 is ComplyFixture {
    function _configureModules() internal virtual override {
        super._configureModules();
        compliance.removeModule(address(maxBalanceModule));
    }
}

// ---------- V10: cap keyed by wallet instead of identity (H2)
abstract contract CfgV10 is ComplyFixture {
    function _maxBalanceImpl() internal virtual override returns (address) {
        return address(new MaxBalanceModuleV10());
    }
}

// ---------- V11: Bob holds 800, preset says 0 (H3). Properties only, because the start state has balances.
abstract contract CfgV11 is ComplyFixture {
    function _addModules() internal virtual override {
        _mint(b, 800); // no modules yet, so canTransfer is vacuously true
        address[] memory ids = new address[](1);
        ids[0] = address(idB);
        uint256[] memory bal = new uint256[](1);
        bal[0] = 0;
        maxBalanceModule.batchPreSetModuleState(address(compliance), ids, bal);
        super._addModules();
    }
}

// ---------- V12: forcedTransfer does not notify compliance (H3)
abstract contract CfgV12 is ComplyFixture {
    function _newToken() internal virtual override returns (Token) {
        return Token(address(new TokenV12()));
    }
}

// ---------- V13: cap set to type(uint256).max (H4)
abstract contract CfgV13 is ComplyFixture {
    function _configureModules() internal virtual override {
        _restrictCountry(RESTRICTED);
        _setCap(type(uint256).max);
    }
}
