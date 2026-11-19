pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_K2_s1 is ComplyFixture {
    function _amt() internal view returns (uint256) {
        return CAP / 20;
    }

    // Normal case first, then the revocation: the same wallet can no longer receive a transfer.
    function test_revoked_wallet_cannot_receive_transfer() public {
        uint256 amt = _amt();
        _mint(a1, amt * 2);

        // Before revocation Bob can receive.
        uint256 bBefore = token.balanceOf(b);
        _transfer(a1, b, amt);
        assertEq(token.balanceOf(b), bBefore + amt);

        // KYC revoked.
        _revokeClaim(idB);

        uint256 a1Bal = token.balanceOf(a1);
        uint256 bBal = token.balanceOf(b);
        vm.prank(a1);
        vm.expectRevert();
        token.transfer(b, amt);

        assertEq(token.balanceOf(b), bBal);
        assertEq(token.balanceOf(a1), a1Bal);
    }

    // Minting to a wallet whose KYC was revoked must fail.
    function test_revoked_wallet_cannot_receive_mint() public {
        uint256 amt = _amt();
        _revokeClaim(idB);

        uint256 bBal = token.balanceOf(b);
        uint256 supply = token.totalSupply();

        vm.prank(agent);
        vm.expectRevert();
        token.mint(b, amt);

        assertEq(token.balanceOf(b), bBal);
        assertEq(token.totalSupply(), supply);
    }

    // Normal allowed case: revoking Bob does not affect Alice, who can still receive and move tokens.
    function test_unrevoked_investor_still_receives_after_other_revocation() public {
        uint256 amt = _amt();
        _revokeClaim(idB);

        uint256 a1Before = token.balanceOf(a1);
        uint256 a2Before = token.balanceOf(a2);

        _mint(a1, amt);
        assertEq(token.balanceOf(a1), a1Before + amt);

        _transfer(a1, a2, amt);
        assertEq(token.balanceOf(a1), a1Before);
        assertEq(token.balanceOf(a2), a2Before + amt);
    }

    // The allowance path (transferFrom) must also refuse a revoked receiver.
    function test_revoked_wallet_cannot_receive_via_transferFrom() public {
        uint256 amt = _amt();
        _mint(a1, amt);

        _revokeClaim(idB);

        vm.prank(a1);
        token.approve(a2, amt);

        uint256 a1Bal = token.balanceOf(a1);
        uint256 bBal = token.balanceOf(b);

        vm.prank(a2);
        vm.expectRevert();
        token.transferFrom(a1, b, amt);

        assertEq(token.balanceOf(b), bBal);
        assertEq(token.balanceOf(a1), a1Bal);
    }
}
