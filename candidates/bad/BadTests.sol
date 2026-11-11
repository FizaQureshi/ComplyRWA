// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../../test/ComplyFixture.sol";

/// @notice Deliberately bad tests, used only to prove that the validity filter (step 4.2)
/// rejects them. They use nothing from the fixture except being a ComplyFixture test.
/// Expected outcomes:
///   BAD1  REJECT   (fails on every clean configuration)
///   BAD2  VACUOUS  (no assertion at all)
///   BAD3  VACUOUS  (assertion that is always true, so no variant is ever detected)
contract BadTests is ComplyFixture {
    function test_BAD1_failsEverywhere() public {
        assertTrue(false, "always fails");
    }

    function test_BAD2_noAssertion() public {
        uint256 x = 1;
        x = x + 1;
    }

    function test_BAD3_alwaysTrue() public {
        assertTrue(true);
    }
}
