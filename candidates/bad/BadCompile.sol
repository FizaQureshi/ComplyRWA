// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../../test/ComplyFixture.sol";

/// @notice Deliberately broken: calls a function that does not exist.
/// Expected outcome: REJECT (does not compile). Used only to prove the validity filter.
contract BadCompile is ComplyFixture {
    function test_BAD4_doesNotCompile() public {
        thisFunctionDoesNotExist();
    }
}
