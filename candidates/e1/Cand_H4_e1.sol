pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_H4_e1 is ComplyFixture {

    // Policy: the cap must not be 0. A one-unit holding must be allowed.
    function test_H4_capIsNotZero() public {
        uint256 held = _idBalance(idM);
        assertTrue(held < CAP);
        assertTrue(CAP > 0);
        assertTrue(
            maxBalanceModule.moduleCheck(address(0), m, 1, address(compliance)),
            "a one-unit holding must fit under the policy cap"
        );
    }

    // Policy: the cap must not be the maximum uint256. A holding of max must be refused.
    function test_H4_capIsNotMaxUint256() public {
        assertTrue(CAP < type(uint256).max);
        uint256 held = _idBalance(idM);
        assertTrue(held == 0, "precondition: Mallory holds nothing");
        assertFalse(
            maxBalanceModule.moduleCheck(address(0), m, type(uint256).max, address(compliance)),
            "a max-uint256 holding must be refused"
        );
    }

    // Policy: the cap equals the issuer's number. Filling exactly up to CAP is allowed, one more is not.
    function test_H4_capMatchesPolicyNumber() public {
        uint256 held = _idBalance(idM);
        assertTrue(held < CAP);
        uint256 room = CAP - held;
        assertTrue(
            maxBalanceModule.moduleCheck(address(0), m, room, address(compliance)),
            "filling exactly up to the policy cap must be allowed"
        );
        assertFalse(
            maxBalanceModule.moduleCheck(address(0), m, room + 1, address(compliance)),
            "one unit above the policy cap must be refused"
        );
    }

    // Normal allowed case: a small mint well within the cap succeeds and updates the balance.
    function test_H4_normalMintWithinCapWorks() public {
        uint256 heldB = _idBalance(idB);
        assertTrue(heldB < CAP);
        uint256 before = token.balanceOf(b);
        _mint(b, 1);
        assertEq(token.balanceOf(b), before + 1);
    }
}
