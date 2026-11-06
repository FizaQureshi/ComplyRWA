// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "../ComplyFixture.sol";

/// @notice Special gold tests for rules that STOCK T-REX / ONCHAINID VIOLATES (K4, K5, K2 twin
/// signature). They state the POLICY, so on stock they are EXPECTED TO FAIL. Keep them out of
/// the default run:  forge test --no-match-contract GoldSpecial
contract GoldSpecialTest is ComplyFixture {
    // ---- G11 (K4): an expired claim must be rejected. Expected on stock: FAIL (S01).
    function test_G11_expiredClaimIsRejected() public {
        address dave = makeAddr("dave");
        Identity idD = new Identity(dave, false);
        vm.prank(agent);
        ir.registerIdentity(dave, IIdentity(address(idD)), INDIA);
        _issueClaim(idD, dave, KYC_TOPIC, bytes("valid-until:2025-01-01"));
        vm.warp(1_800_000_000); // year 2027
        _mint(a1, 500);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, dave, 100);
    }

    // ---- G12 (K5): a sender whose claim was revoked cannot send. Expected on stock: FAIL (S02).
    function test_G12_revokedSenderCannotSend() public {
        _mint(b, 500);
        _revokeClaim(idB);
        vm.expectRevert();
        _transfer(b, a1, 100);
    }

    // ---- G14 (K2): a revoked claim cannot be revived by re-adding it with a twin signature.
    // Expected on stock: FAIL (S03).
    function test_G14_revokedClaimCannotBeRevived() public {
        _mint(a1, 500);
        _revokeClaim(idB);
        (uint8 v, bytes32 r, bytes32 s) = _rsv(idB, KYC_TOPIC, KYC_DATA);
        uint256 n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
        vm.prank(b);
        try idB.addClaim(KYC_TOPIC, 1, address(claimIssuer), abi.encodePacked(r, bytes32(n - uint256(s)), v == 27 ? 28 : 27), KYC_DATA, "") {} catch {}
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }
}
