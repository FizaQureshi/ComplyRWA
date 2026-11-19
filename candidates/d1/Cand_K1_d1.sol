pragma solidity ^0.8.17;
import "../../test/ComplyFixture.sol";

contract Cand_K1_d1 is ComplyFixture {
    // Policy: only investors with a valid KYC claim from a trusted issuer may receive tokens.

    // Mallory is registered but holds no KYC claim, so a transfer to her must be refused.
    function test_transferToUnverifiedWalletReverts() public {
        _mint(a1, 10);

        uint256 senderBefore = token.balanceOf(a1);
        uint256 recipientBefore = token.balanceOf(m);

        vm.prank(a1);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(m, 1);

        assertEq(token.balanceOf(a1), senderBefore, "sender balance changed on refused transfer");
        assertEq(token.balanceOf(m), recipientBefore, "unverified wallet received tokens");
    }

    // The agent must not be able to mint to a wallet without a valid KYC claim.
    function test_mintToUnverifiedWalletReverts() public {
        uint256 before = token.balanceOf(m);

        vm.prank(agent);
        vm.expectRevert(bytes("Identity is not verified."));
        token.mint(m, 1);

        assertEq(token.balanceOf(m), before, "unverified wallet was minted tokens");
    }

    // Once Bob's KYC claim is revoked, he is no longer a valid recipient.
    function test_transferToWalletWithRevokedClaimReverts() public {
        _mint(a1, 10);
        _revokeClaim(idB);

        uint256 senderBefore = token.balanceOf(a1);
        uint256 recipientBefore = token.balanceOf(b);

        vm.prank(a1);
        vm.expectRevert(bytes("Transfer not possible"));
        token.transfer(b, 1);

        assertEq(token.balanceOf(a1), senderBefore, "sender balance changed on refused transfer");
        assertEq(token.balanceOf(b), recipientBefore, "investor with revoked KYC received tokens");
    }

    // A verified investor (Alice's second wallet, same KYC identity) can still receive tokens.
    function test_transferToVerifiedInvestorWorks() public {
        _mint(a1, 10);

        uint256 senderBefore = token.balanceOf(a1);
        uint256 recipientBefore = token.balanceOf(a2);

        vm.prank(a1);
        bool ok = token.transfer(a2, 4);

        assertTrue(ok, "transfer to verified investor returned false");
        assertEq(token.balanceOf(a1), senderBefore - 4, "sender balance wrong after transfer");
        assertEq(token.balanceOf(a2), recipientBefore + 4, "verified investor did not receive tokens");
    }
}
