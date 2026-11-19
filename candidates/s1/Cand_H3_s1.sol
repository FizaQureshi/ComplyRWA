pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_H3_s1 is ComplyFixture {
    function realA() internal view returns (uint256) {
        return token.balanceOf(a1) + token.balanceOf(a2);
    }

    function test_mintKeepsTrackedEqualReal() public {
        uint256 x = CAP / 10;
        uint256 realBeforeA = realA();
        uint256 realBeforeB = token.balanceOf(b);
        _mint(a1, x);
        _mint(b, x);
        assertEq(realA(), realBeforeA + x, "real A");
        assertEq(token.balanceOf(b), realBeforeB + x, "real B");
        assertEq(_idBalance(idA), realA(), "tracked A != real A after mint");
        assertEq(_idBalance(idB), token.balanceOf(b), "tracked B != real B after mint");
    }

    function test_transferBetweenIdentitiesKeepsTrackedEqualReal() public {
        uint256 x = CAP / 10;
        uint256 y = CAP / 20;
        _mint(a1, x);
        uint256 realBeforeB = token.balanceOf(b);
        uint256 realBeforeA = realA();
        _transfer(a1, b, y);
        assertEq(realA(), realBeforeA - y, "real A");
        assertEq(token.balanceOf(b), realBeforeB + y, "real B");
        assertEq(_idBalance(idA), realA(), "tracked A drifted after transfer");
        assertEq(_idBalance(idB), token.balanceOf(b), "tracked B drifted after transfer");
    }

    function test_burnAndSameIdentityTransferKeepTrackedEqualReal() public {
        uint256 x = CAP / 10;
        uint256 y = CAP / 20;
        _mint(a1, x);
        // move between Alice's own wallets: identity total must not change
        uint256 trackedBefore = _idBalance(idA);
        _transfer(a1, a2, y);
        assertEq(_idBalance(idA), trackedBefore, "tracked changed on same-identity transfer");
        assertEq(_idBalance(idA), realA(), "tracked A != real A after wallet move");
        // burn part of it
        uint256 z = CAP / 100 + 1;
        uint256 realBefore = realA();
        vm.prank(agent);
        token.burn(a2, z);
        assertEq(realA(), realBefore - z, "real A after burn");
        assertEq(_idBalance(idA), realA(), "tracked A != real A after burn");
    }

    function test_forcedTransferKeepsTrackedEqualReal() public {
        uint256 x = CAP / 10;
        uint256 y = CAP / 20;
        _mint(a1, x);
        uint256 realBeforeB = token.balanceOf(b);
        uint256 realBeforeA = realA();
        vm.prank(agent);
        token.forcedTransfer(a1, b, y);
        assertEq(realA(), realBeforeA - y, "real A");
        assertEq(token.balanceOf(b), realBeforeB + y, "real B");
        assertEq(_idBalance(idA), realA(), "tracked A drifted after forcedTransfer");
        assertEq(_idBalance(idB), token.balanceOf(b), "tracked B drifted after forcedTransfer");
    }
}
