pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_H1_s1 is ComplyFixture {
    function _aliceTotal() internal view returns (uint256) {
        return token.balanceOf(a1) + token.balanceOf(a2);
    }

    // Fill Alice's identity (a1 + a2) exactly up to CAP. Reaching CAP is allowed.
    function _fillAliceToCap() internal {
        uint256 bal = _aliceTotal();
        if (bal < CAP) {
            _mint(a1, CAP - bal);
        }
        assertEq(_aliceTotal(), CAP);
    }

    // A single mint larger than CAP must be rejected.
    function test_mintAboveCapReverts() public {
        uint256 before = token.balanceOf(b);
        vm.expectRevert();
        vm.prank(agent);
        token.mint(b, CAP + 1);
        assertEq(token.balanceOf(b), before);
    }

    // Alice at CAP via a1; minting 1 more to her other wallet a2 (same identity) must revert.
    function test_mintToSecondWalletOfSameIdentityOverCapReverts() public {
        _fillAliceToCap();
        uint256 a2Before = token.balanceOf(a2);
        vm.expectRevert();
        vm.prank(agent);
        token.mint(a2, 1);
        assertEq(token.balanceOf(a2), a2Before);
        assertTrue(_aliceTotal() <= CAP);
    }

    // Alice at CAP; Bob sending 1 token to her second wallet must be rejected.
    function test_transferPushingIdentityOverCapReverts() public {
        _fillAliceToCap();
        if (token.balanceOf(b) == 0) {
            _mint(b, 1);
        }
        uint256 bBefore = token.balanceOf(b);
        uint256 a2Before = token.balanceOf(a2);
        vm.expectRevert();
        vm.prank(b);
        token.transfer(a2, 1);
        assertEq(token.balanceOf(b), bBefore);
        assertEq(token.balanceOf(a2), a2Before);
        assertTrue(_aliceTotal() <= CAP);
    }

    // Normal case: a small transfer that keeps the receiver under CAP still works.
    function test_smallTransferWithinCapWorks() public {
        _mint(b, 2);
        uint256 bBefore = token.balanceOf(b);
        uint256 a1Before = token.balanceOf(a1);
        _transfer(b, a1, 1);
        assertEq(token.balanceOf(b), bBefore - 1);
        assertEq(token.balanceOf(a1), a1Before + 1);
        assertTrue(_aliceTotal() <= CAP);
    }
}
