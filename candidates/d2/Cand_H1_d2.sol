pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_H1_d2 is ComplyFixture {
    // Break attempt: minting Bob past the holding cap must be refused and leave his balances untouched.
    function test_mintPastCapIsRefused() public {
        uint256 bal = _idBalance(idB);
        assertTrue(bal <= CAP);
        uint256 room = CAP - bal;
        uint256 pre = token.balanceOf(b);

        vm.prank(agent);
        (bool ok, ) = address(token).call(abi.encodeWithSelector(Token.mint.selector, b, room + 1));

        assertFalse(ok);
        assertEq(token.balanceOf(b), pre);
        assertEq(_idBalance(idB), bal);
    }

    // Break attempt across wallets: Alice's two wallets share idA, so a2 must count a1's balance.
    function test_transferToSecondWalletCannotExceedIdentityCap() public {
        uint256 bal = _idBalance(idA);
        assertTrue(bal <= CAP);
        uint256 room = CAP - bal;
        assertGt(room, 1);

        uint256 r1 = room / 2;
        uint256 t = room - r1 + 1; // bal + r1 + t = CAP + 1 for idA

        vm.prank(agent);
        token.mint(a1, r1);
        vm.prank(agent);
        token.mint(b, t);

        uint256 pre = token.balanceOf(a2);
        vm.prank(b);
        (bool ok, ) = address(token).call(abi.encodeWithSelector(Token.transfer.selector, a2, t));

        assertFalse(ok);
        assertEq(token.balanceOf(a2), pre);
        assertEq(_idBalance(idA), bal + r1);
    }

    // Normal case: minting up to (but within) the cap succeeds and is tracked for the identity.
    function test_mintWithinCapSucceeds() public {
        uint256 bal = _idBalance(idB);
        assertTrue(bal <= CAP);
        uint256 room = CAP - bal;
        assertGt(room, 1);
        uint256 amt = room / 2;

        uint256 pre = token.balanceOf(b);
        vm.prank(agent);
        token.mint(b, amt);

        assertEq(token.balanceOf(b), pre + amt);
        assertEq(_idBalance(idB), bal + amt);
        assertTrue(_idBalance(idB) <= CAP);
    }

    // Normal case: a transfer that keeps Alice's identity within the cap goes through.
    function test_transferWithinIdentityCapSucceeds() public {
        uint256 roomA = CAP - _idBalance(idA);
        assertGt(roomA, 1);
        uint256 amt = roomA / 2;

        vm.prank(agent);
        token.mint(b, amt);

        uint256 bBefore = token.balanceOf(b);
        uint256 aBefore = _idBalance(idA);
        uint256 a2Before = token.balanceOf(a2);

        vm.prank(b);
        assertTrue(token.transfer(a2, amt));

        assertEq(token.balanceOf(b), bBefore - amt);
        assertEq(token.balanceOf(a2), a2Before + amt);
        assertEq(_idBalance(idA), aBefore + amt);
        assertTrue(_idBalance(idA) <= CAP);
    }
}
