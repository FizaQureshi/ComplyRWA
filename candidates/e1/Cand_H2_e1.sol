pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_H2_e1 is ComplyFixture {
    // Break attempt: a transfer from outside the identity into a2 that pushes
    // idA (a1 + a2) past CAP must revert, even though a2 alone is under CAP.
    function test_H2_transferIntoSecondWalletCountsAgainstIdentityCap() public {
        uint256 cur = _idBalance(idA);
        uint256 room = CAP - cur;
        assertTrue(room >= 2);
        uint256 half = room / 2;
        uint256 over = room - half + 1;

        _mint(a1, half);
        _mint(b, over);

        uint256 a2Before = token.balanceOf(a2);
        uint256 idBefore = _idBalance(idA);
        assertEq(idBefore, cur + half);

        vm.prank(b);
        vm.expectRevert();
        token.transfer(a2, over);

        assertEq(token.balanceOf(a2), a2Before);
        assertEq(_idBalance(idA), idBefore);
    }

    // Normal allowed case: two wallets of the same identity can together fill
    // the shared cap exactly, and the identity total equals CAP afterwards.
    function test_H2_walletsOfSameIdentityCanFillSharedCapExactly() public {
        uint256 cur = _idBalance(idA);
        uint256 room = CAP - cur;
        assertTrue(room >= 2);
        uint256 half = room / 2;
        uint256 rest = room - half;

        _mint(a1, half);
        _mint(b, rest);

        uint256 a2Before = token.balanceOf(a2);
        _transfer(b, a2, rest);

        assertEq(token.balanceOf(a2), a2Before + rest);
        assertEq(_idBalance(idA), CAP);
    }

    // Break attempt via mint: the agent cannot mint into a2 when a1 already
    // holds part of the identity's cap and the total would exceed CAP.
    function test_H2_mintToSecondWalletCountsAgainstIdentityCap() public {
        uint256 cur = _idBalance(idA);
        uint256 room = CAP - cur;
        assertTrue(room >= 2);
        uint256 half = room / 2;
        uint256 over = room - half + 1;

        _mint(a1, half);

        uint256 a2Before = token.balanceOf(a2);
        uint256 idBefore = _idBalance(idA);

        vm.prank(agent);
        vm.expectRevert();
        token.mint(a2, over);

        assertEq(token.balanceOf(a2), a2Before);
        assertEq(_idBalance(idA), idBefore);
    }

    // Normal allowed case: the cap is per identity. Once idA is full across
    // a1 and a2, a different identity (Bob) can still receive tokens under its own cap.
    function test_H2_fullIdentityDoesNotBlockOtherIdentity() public {
        uint256 cur = _idBalance(idA);
        uint256 room = CAP - cur;
        assertTrue(room >= 2);
        uint256 half = room / 2;
        uint256 rest = room - half;
        uint256 over = rest + 1;

        _mint(a1, half);
        _mint(a2, rest);
        assertEq(_idBalance(idA), CAP);

        uint256 bBefore = token.balanceOf(b);
        uint256 idBBefore = _idBalance(idB);

        _mint(b, over);

        assertEq(token.balanceOf(b), bBefore + over);
        assertEq(_idBalance(idB), idBBefore + over);
    }
}
