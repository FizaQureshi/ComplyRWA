// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "./ComplyFixture.sol";

/// @notice Stock T-REX behaviour that Phase 2 says violates a rule (S01, S02) plus the
/// signature-malleability hypothesis (S03). These tests assert what stock actually does.
contract StockGapsTest is ComplyFixture {
    // S01 / K4: a claim whose data says "expired" is still accepted.
    function test_S01_expiredClaimStillAccepted() public {
        Identity idD = new Identity(makeAddr("dave"), false);
        address dave = makeAddr("dave");
        vm.prank(agent);
        ir.registerIdentity(dave, IIdentity(address(idD)), INDIA);
        _issueClaim(idD, dave, KYC_TOPIC, bytes("valid-until:2025-01-01"));
        vm.warp(1_800_000_000); // year 2027
        _mint(a1, 500);
        _transfer(a1, dave, 100);
        assertEq(token.balanceOf(dave), 100);
    }

    // S02 / K5: a sender whose claim was revoked can still send.
    function test_S02_revokedSenderCanStillSend() public {
        _mint(b, 500);
        _revokeClaim(idB);
        assertFalse(ir.isVerified(b));
        _transfer(b, a1, 100);
        assertEq(token.balanceOf(a1), 100);
    }

    // K2 control: receiving is blocked after revocation.
    function test_K2_revokedReceiverIsBlocked() public {
        _mint(a1, 500);
        _revokeClaim(idB);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);
    }

    // S03 hypothesis: re-adding the claim with the "twin" signature (s' = n - s, flipped v)
    // is not in revokedClaims, so revocation can be undone by the investor.
    function test_S03_revokedClaimRevivedByTwinSignature() public {
        _mint(a1, 500);
        _revokeClaim(idB);
        vm.expectRevert(bytes("Transfer not possible"));
        _transfer(a1, b, 100);

        (uint8 v, bytes32 r, bytes32 s) = _rsv(idB, KYC_TOPIC, KYC_DATA);
        uint256 n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
        bytes32 s2 = bytes32(n - uint256(s));
        uint8 v2 = v == 27 ? 28 : 27;
        vm.prank(b);
        idB.addClaim(KYC_TOPIC, 1, address(claimIssuer), abi.encodePacked(r, s2, v2), KYC_DATA, "");

        assertTrue(ir.isVerified(b)); // revocation undone
        _transfer(a1, b, 100);
        assertEq(token.balanceOf(b), 100);
    }
}
