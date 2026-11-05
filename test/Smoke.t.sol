// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "forge-std/Test.sol";

contract SmokeTest is Test {
    function test_signAndRecover() public {
        (address signer, uint256 pk) = makeAddrAndKey("issuerKey");
        bytes32 h = keccak256("hello");
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, h);
        assertEq(ecrecover(h, v, r, s), signer);
    }
}
