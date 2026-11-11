// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../ComplyFixture.sol";

/// @notice Clean (non-vulnerable) configuration contracts C01 to C08.
/// Moved here from test/clean/CleanConfigs.t.sol (Phase 4, step 4.0) so that any test file,
/// including generated ones, can import them and run on a configuration.
/// Each one overrides at most a few fixture hooks. The list of hooks per configuration is
/// recorded in pipeline/configs.json and checked by pipeline/check_manifest.py.

// ============================================================ C01: baseline (no changes)
abstract contract Cfg01 is ComplyFixture {}

// ============================================================ C02: two topics, two issuers
/// Topics 1 and 2 are both required (AND). Issuers X and Y are both trusted for both topics (OR).
/// Every investor holds topic 1 from X. Topic 2 comes from Y (Alice, Carol) or from X (Bob).
abstract contract Cfg02 is ComplyFixture {
    uint256 internal constant TOPIC_2 = 2;

    function _deployClaimIssuer() internal virtual override {
        super._deployClaimIssuer(); // issuer X, topic 1
        ctr.addClaimTopic(TOPIC_2);
        (issuer2Signer, issuer2Key) = makeAddrAndKey("issuer2Signer");
        address admin2 = makeAddr("issuer2Admin");
        claimIssuer2 = new ClaimIssuer(admin2);
        vm.prank(admin2);
        claimIssuer2.addKey(keccak256(abi.encode(issuer2Signer)), 3, 1);

        uint256[] memory both = new uint256[](2);
        both[0] = KYC_TOPIC;
        both[1] = TOPIC_2;
        tir.updateIssuerClaimTopics(IClaimIssuer(address(claimIssuer)), both);
        tir.addTrustedIssuer(IClaimIssuer(address(claimIssuer2)), both);
    }

    function _registerInvestors() internal virtual override {
        super._registerInvestors(); // topic 1 from X for Alice, Bob, Carol
        _issueClaimFrom(claimIssuer2, issuer2Key, idA, a1, TOPIC_2, KYC_DATA);
        _issueClaimFrom(claimIssuer, issuerKey, idB, b, TOPIC_2, KYC_DATA);
        _issueClaimFrom(claimIssuer2, issuer2Key, idC, c, TOPIC_2, KYC_DATA);
    }
}

// ====================================== C03: same-identity move is rejected (start state)
/// Alice holds 600 and tries to move 500 between her own two wallets. The module rejects it (D3).
abstract contract Cfg03 is ComplyFixture {
    function _afterSetUp() internal virtual override {
        _mint(a1, 600);
        vm.prank(a1);
        try token.transfer(a2, 500) {
            revert("C03: the same-identity move should have been rejected");
        } catch {}
    }
}

// ============================ C04: agent forcedTransfer to a restricted country (start state)
/// Known exception (D1, J4): an agent moves 100 tokens to Carol (country 408).
abstract contract Cfg04 is ComplyFixture {
    function _afterSetUp() internal virtual override {
        _mint(a1, 500);
        vm.prank(agent);
        token.forcedTransfer(a1, c, 100);
    }
}

// ================================ C05: different valid numbers (cap 500, 408 and 643 restricted)
abstract contract Cfg05 is ComplyFixture {
    function _configure() internal virtual override {
        CAP = 500;
        RESTRICTED2 = 643;
    }
}

// ================================ C06: claim revoked, then re-issued with different data
abstract contract Cfg06 is ComplyFixture {
    function _registerInvestors() internal virtual override {
        super._registerInvestors();
        _revokeClaim(idB);
        // Identical data would give the same signature, which stays revoked. So the data changes.
        _issueClaim(idB, b, KYC_TOPIC, bytes("KYC-OK-v2"));
    }
}

// ============================ C07: receiving exactly up to the cap (start state)
/// Bob holds 900 and receives exactly 100, ending at exactly 1000. The check uses ">", so this is allowed.
abstract contract Cfg07 is ComplyFixture {
    function _afterSetUp() internal virtual override {
        _mint(b, 900);
        _mint(a1, 500);
        _transfer(a1, b, 100);
    }
}

// ================ C08: module bound to a token that already has holders, with a CORRECT preset
/// Carol holds 300 and Alice's second wallet holds 100 BEFORE MaxBalanceModule exists. The owner presets
/// the real balances with batchPreSetModuleState, then binds the module.
abstract contract Cfg08 is ComplyFixture {
    function _addModules() internal virtual override {
        _mint(c, 300); // no modules yet, so canTransfer is vacuously true
        _mint(a2, 100);
        address[] memory presetIds = new address[](2);
        presetIds[0] = address(idC);
        presetIds[1] = address(idA);
        uint256[] memory presetBalances = new uint256[](2);
        presetBalances[0] = 300;
        presetBalances[1] = 100;
        maxBalanceModule.batchPreSetModuleState(address(compliance), presetIds, presetBalances);
        super._addModules();
    }
}
