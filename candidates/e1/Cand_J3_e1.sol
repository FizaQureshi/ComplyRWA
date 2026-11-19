pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_J3_e1 is ComplyFixture {
    // Policy: a bound country module with the right countries set is what makes a
    // country restriction real. Each test checks one part of that.

    // Normal allowed case: an Indian-resident investor with valid KYC can receive tokens.
    function test_J3_allowedCountryStillReceivesTokens() public {
        uint256 amount = CAP / 10;
        uint256 before = token.balanceOf(b);

        _mint(b, amount);

        assertEq(token.balanceOf(b), before + amount, "allowed investor should receive minted tokens");
    }

    // Break attempt: unbind the country module from compliance. The restriction would then be
    // a dead rule. The fixture binding must hold, and minting into the restricted country must
    // still be blocked by policy.
    function test_J3_restrictedCountryMintBlockedWhileModuleBound() public {
        assertTrue(
            compliance.isModuleBound(address(countryModule)),
            "country module must be bound to compliance"
        );

        uint256 before = token.balanceOf(c);
        vm.expectRevert();
        _mint(c, CAP / 10);

        assertEq(token.balanceOf(c), before, "restricted-country investor must not receive tokens");
    }

    // Break attempt: the module is bound, but the restricted countries are not set as policy requires.
    function test_J3_restrictedCountriesAreConfiguredInModule() public {
        assertTrue(
            countryModule.isCountryRestricted(address(compliance), RESTRICTED),
            "RESTRICTED country must be set as restricted in the module"
        );

        if (RESTRICTED2 != 0) {
            assertTrue(
                countryModule.isCountryRestricted(address(compliance), RESTRICTED2),
                "RESTRICTED2 country must be set as restricted in the module"
            );
        }

        if (INDIA != RESTRICTED && INDIA != RESTRICTED2) {
            assertFalse(
                countryModule.isCountryRestricted(address(compliance), INDIA),
                "INDIA is not a restricted country and must not be set as restricted"
            );
        }
    }

    // Break attempt via the realistic path: a transfer from an allowed investor into the
    // restricted country must fail. Mint first, then check that the precondition holds.
    function test_J3_transferIntoRestrictedCountryBlocked() public {
        uint256 amount = CAP / 10;

        uint256 aBefore = token.balanceOf(a1);
        _mint(a1, amount);
        assertEq(token.balanceOf(a1), aBefore + amount, "setup: a1 must hold tokens before the transfer");

        uint256 cBefore = token.balanceOf(c);
        vm.expectRevert();
        _transfer(a1, c, amount);

        assertEq(token.balanceOf(c), cBefore, "transfer into restricted country must not credit the recipient");
    }
}
