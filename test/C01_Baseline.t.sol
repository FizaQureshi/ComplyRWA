// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "./ComplyFixture.sol";

/// @notice Sanity tests for the clean baseline C01. They prove the fixture works and
/// check the Phase 2 claims that were confirmed by reading code (D1, D3, C07, mint messages).
contract C01_BaselineTest is ComplyFixture {
    function test_modulesBoundAndConfigured() public {
        address[] memory mods = compliance.getModules();
        assertEq(mods.length, 2);
        assertTrue(compliance.isModuleBound(address(countryModule)));
        assertTrue(compliance.isModuleBound(address(maxBalanceModule)));
        assertTrue(countryModule.isCountryRestricted(address(compliance), RESTRICTED));
        assertFalse(countryModule.isCountryRestricted(address(compliance), INDIA));
        assertEq(ctr.getClaimTopics().length, 1);
        assertTrue(ir.isVerified(a1) && ir.isVerified(b) && ir.isVerified(c));
        assertFalse(ir.isVerified(m)); // Mallory: registered, no claim
    }

    function test_transferToVerifiedSucceeds() public {
        _mint(a1, 500);
        _transfer(a1, b, 100);
        assertEq(token.balanceOf(b), 100);
        assertEq(_idBalance(idB), 100);
        assertEq(_idBalance(idA), 400);
    }

    function test_transferToUnverifiedReverts() public {
        _mint(a1, 500);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, m, 100);
    }

    function test_transferToRestrictedCountryReverts() public {
        _mint(a1, 500);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, c, 100);
    }

    function test_transferOverCapReverts() public {
        _mint(b, 900);
        _mint(a1, 500);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 200); // C01: Bob would hold 1100
    }

    function test_C07_exactlyAtCapSucceeds() public {
        _mint(b, 900);
        _mint(a1, 500);
        _transfer(a1, b, 100); // Bob ends at exactly 1000
        assertEq(token.balanceOf(b), 1000);
    }

    function test_C03_sameIdentityMoveIsRejected() public {
        _mint(a1, 600);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, a2, 500); // D3: moduleCheck adds 600 + 500 > 1000
    }

    function test_sameIdentityForcedMoveSucceeds() public {
        _mint(a1, 600);
        vm.prank(agent);
        token.forcedTransfer(a1, a2, 500); // write side nets to zero for one identity
        assertEq(token.balanceOf(a2), 500);
        assertEq(_idBalance(idA), 600);
    }

    function test_C04_forcedTransferToRestrictedCountrySucceeds() public {
        _mint(a1, 500);
        vm.prank(agent);
        token.forcedTransfer(a1, c, 100); // D1: CountryRestrictModule write hooks are empty
        assertEq(token.balanceOf(c), 100);
    }

    function test_forcedTransferOverCapRevertsOnWriteSide() public {
        _mint(b, 900);
        _mint(a1, 500);
        vm.prank(agent);
        vm.expectRevert(abi.encodeWithSelector(MaxBalanceModule.MaxBalanceExceeded.selector, address(compliance), 200));
        token.forcedTransfer(a1, b, 200);
    }

    function test_mintRevertMessagesDiffer() public {
        vm.startPrank(agent);
        vm.expectRevert(bytes("Identity is not verified."));
        token.mint(m, 10);
        vm.expectRevert(bytes("Compliance not followed"));
        token.mint(c, 10);
        vm.stopPrank();
    }
}
