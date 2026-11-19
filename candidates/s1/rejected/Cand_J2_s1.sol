pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_J2_s1 is ComplyFixture {
    function _amt() internal view returns (uint256) {
        return CAP / 20;
    }

    // Mint to a wallet whose country was changed to RESTRICTED must fail.
    function test_mintBlockedAfterCountryChangedToRestricted() public {
        uint256 before = token.balanceOf(b);
        // sanity: Bob (INDIA) can receive before the change
        _mint(b, _amt());
        assertEq(token.balanceOf(b), before + _amt());

        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);

        uint256 mid = token.balanceOf(b);
        vm.prank(agent);
        vm.expectRevert();
        token.mint(b, _amt());
        assertEq(token.balanceOf(b), mid);
    }

    // Transfer to a wallet whose country changed to RESTRICTED must fail.
    function test_transferBlockedAfterCountryChangedToRestricted() public {
        _mint(a1, _amt() * 2);
        uint256 bBefore = token.balanceOf(b);
        uint256 aBefore = token.balanceOf(a1);

        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);

        vm.prank(a1);
        vm.expectRevert();
        token.transfer(b, _amt());
        assertEq(token.balanceOf(b), bBefore);
        assertEq(token.balanceOf(a1), aBefore);

        // Alice's second wallet (same identity) is also blocked once its own country changes
        vm.prank(agent);
        ir.updateCountry(a2, RESTRICTED);
        uint256 a2Before = token.balanceOf(a2);
        vm.prank(a1);
        vm.expectRevert();
        token.transfer(a2, _amt());
        assertEq(token.balanceOf(a2), a2Before);

        // second restricted country, if the configuration has one
        if (RESTRICTED2 != 0) {
            vm.prank(agent);
            ir.updateCountry(b, INDIA);
            vm.prank(agent);
            ir.updateCountry(b, RESTRICTED2);
            vm.prank(a1);
            vm.expectRevert();
            token.transfer(b, _amt());
            assertEq(token.balanceOf(b), bBefore);
        }
    }

    // Normal case works, is blocked while restricted, and works again after moving back.
    function test_receiveWorksBeforeBlockedDuringAndAllowedAfterRestore() public {
        _mint(a1, _amt() * 3);
        uint256 bStart = token.balanceOf(b);

        _transfer(a1, b, _amt());
        assertEq(token.balanceOf(b), bStart + _amt());

        vm.prank(agent);
        ir.updateCountry(b, RESTRICTED);
        vm.prank(a1);
        vm.expectRevert();
        token.transfer(b, _amt());
        assertEq(token.balanceOf(b), bStart + _amt());

        vm.prank(agent);
        ir.updateCountry(b, INDIA);
        _transfer(a1, b, _amt());
        assertEq(token.balanceOf(b), bStart + _amt() * 2);
    }

    // Changing country to a non-restricted one does not block receiving.
    function test_changeToUnrestrictedCountryStillReceives() public {
        uint16 other = INDIA + 1;
        while (other == RESTRICTED || (RESTRICTED2 != 0 && other == RESTRICTED2)) {
            other++;
        }
        _mint(a1, _amt() * 2);
        uint256 bStart = token.balanceOf(b);

        vm.prank(agent);
        ir.updateCountry(b, other);

        _transfer(a1, b, _amt());
        assertEq(token.balanceOf(b), bStart + _amt());

        uint256 b2 = token.balanceOf(b);
        _mint(b, _amt());
        assertEq(token.balanceOf(b), b2 + _amt());
    }
}
