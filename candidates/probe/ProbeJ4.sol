// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../../test/ComplyFixture.sol";

// Known-exception probe (rule J4): an agent's forcedTransfer to a restricted country is allowed.
// This test is expected to PASS everywhere. The demo report labels it INFO, not a vulnerability.
contract Probe_J4 is ComplyFixture {
    function test_J4_forcedTransferToRestrictedCountrySucceeds() public {
        _mint(a1, CAP / 10);
        uint256 carolBefore = token.balanceOf(c);
        vm.prank(agent);
        token.forcedTransfer(a1, c, CAP / 20);
        assertEq(token.balanceOf(c), carolBefore + CAP / 20);
    }
}
