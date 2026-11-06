// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../ComplyFixture.sol";

/// @notice Gold SCENARIO and CONFIGURATION tests (G02a, G02b, G05b recovery, G06 to G10, G13).
/// They must pass on every clean configuration (C01 to C08).
contract GoldScenariosTest is ComplyFixture {
    // ---- G02a (K3): the issuer requires at least one claim topic
    function test_G02a_requiredTopicsNotEmpty() public {
        assertGt(ctr.getClaimTopics().length, 0, "no required claim topic: KYC is vacuous");
    }

    // ---- G02b (K3): a registered wallet with no claim (Mallory) cannot receive
    function test_G02b_registeredWalletWithoutClaimCannotReceive() public {
        _mint(a1, 500);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, m, 100);
        vm.prank(agent);
        vm.expectRevert(bytes("Identity is not verified."));
        token.mint(m, 10);
    }

    // ---- G05b (H3): recoveryAddress keeps the module's records equal to real balances
    function test_G05b_recoveryKeepsTrackedBalance() public {
        _mint(a1, 400);
        address newWallet = makeAddr("alice3");
        vm.prank(a1);
        idA.addKey(keccak256(abi.encode(newWallet)), 1, 1);
        vm.prank(agent);
        token.recoveryAddress(a1, newWallet, address(idA));
        assertEq(token.balanceOf(newWallet), 400);
        assertEq(
            _idBalance(idA),
            token.balanceOf(a1) + token.balanceOf(a2) + token.balanceOf(newWallet),
            "tracked != real after recovery"
        );
    }

    // ---- G06 (K2): each revocation route blocks receiving
    function test_G06a_deleteIdentityBlocksReceiving() public {
        _mint(a1, 500);
        vm.prank(agent);
        ir.deleteIdentity(b);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }

    function test_G06b_removeTrustedIssuerBlocksReceiving() public {
        _mint(a1, 500);
        tir.removeTrustedIssuer(IClaimIssuer(address(claimIssuer)));
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }

    function test_G06c_revokedClaimBlocksReceiving() public {
        _mint(a1, 500);
        _revokeClaim(idB);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }

    // ---- G07 (J2): a country change to a restricted country blocks future receiving
    function test_G07_countryChangeBlocksReceiving() public {
        _mint(a1, 500);
        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }

    // ---- G08 (J3): country module bound and configured as the policy says (only 408 restricted)
    function test_G08_countryModuleBoundAndConfigured() public {
        assertTrue(compliance.isModuleBound(address(countryModule)), "module not bound");
        bool listed;
        address[] memory mods = compliance.getModules();
        for (uint256 i = 0; i < mods.length; i++) {
            if (mods[i] == address(countryModule)) listed = true;
        }
        assertTrue(listed, "module not in getModules()");
        assertTrue(countryModule.isCountryRestricted(address(compliance), RESTRICTED), "policy country not restricted");
        if (RESTRICTED2 != 0) {
            assertTrue(countryModule.isCountryRestricted(address(compliance), RESTRICTED2), "second policy country not restricted");
        }
        assertFalse(countryModule.isCountryRestricted(address(compliance), 356), "356 wrongly restricted");
        assertFalse(countryModule.isCountryRestricted(address(compliance), 840), "840 wrongly restricted");
    }

    // ---- G09 (H2): two wallets under one identity share one cap
    function test_G09_walletsOfOneIdentityShareTheCap() public {
        uint256 sixty = (CAP * 6) / 10;
        _mint(a1, sixty);
        _mint(b, sixty);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(b, a2, sixty); // Alice's identity would hold 120% of the cap
    }

    // ---- G10 (H4): the cap equals the policy number (probed through canTransfer, no getter exists)
    function test_G10_capEqualsPolicyNumber() public {
        assertTrue(compliance.canTransfer(a1, b, CAP), "cap below policy number (or zero)");
        assertFalse(compliance.canTransfer(a1, b, CAP + 1), "cap above policy number (or disabled)");
    }

    // ---- G13 (J4): forcedTransfer to a restricted country succeeds. The audit report must
    // label this "known exception: agent-only path", not "vulnerability".
    function test_G13_forcedTransferToRestrictedCountryIsKnownException() public {
        _mint(a1, 500);
        uint256 before = token.balanceOf(c); // Carol may already hold tokens (C08)
        vm.prank(agent);
        token.forcedTransfer(a1, c, 100);
        assertEq(token.balanceOf(c), before + 100);
    }
}
