// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "./ComplyFixture.sol";

/// @notice S04 (candidate): a revoked claim is revived when the investor re-adds it with the v byte written as 0 or 1.
/// Found by the LLM-only review (Phase 4, step 4.8, target C02) and checked here by running code.
/// Why it may work: ClaimIssuer.revokedClaims is keyed by the exact signature bytes, and
/// ClaimIssuer.getRecoveredAddress adds 27 to a v byte below 27, so a signature with v = 0 or 1
/// recovers the same signer but is a different byte string, which is not in revokedClaims.
/// Same family as S03 (the twin signature). Like the other StockGaps tests, this test PASSES when the gap exists.
contract StockGapsVByteTest is ComplyFixture {
    function test_S04_revokedClaimRevivedByVByteReencoding() public {
        _mint(a1, 500);

        // 1. Bob is verified, so he can receive.
        _transfer(a1, b, 10);
        assertEq(token.balanceOf(b), 10);

        // 2. The issuer revokes Bob's claim. Receiving is blocked.
        _revokeClaim(idB);
        vm.prank(a1);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(b, 10);

        // 3. Bob re-adds the same claim, signed by the same issuer key, with the v byte written as 0 or 1.
        (uint8 v, bytes32 r, bytes32 s) = _rsv(idB, KYC_TOPIC, KYC_DATA);
        assertTrue(v == 27 || v == 28, "unexpected v from vm.sign");
        bytes memory originalSig = abi.encodePacked(r, s, v);
        bytes memory reencodedSig = abi.encodePacked(r, s, uint8(v - 27));
        assertTrue(claimIssuer.isClaimRevoked(originalSig), "the original signature must be revoked");
        assertFalse(claimIssuer.isClaimRevoked(reencodedSig), "the re-encoded signature is a different byte string");
        vm.prank(b); // Bob is the management key of his own identity
        idB.addClaim(KYC_TOPIC, 1, address(claimIssuer), reencodedSig, KYC_DATA, "");

        // 4. Bob can receive again although his claim was revoked.
        _transfer(a1, b, 10);
        assertEq(token.balanceOf(b), 20);
    }
}