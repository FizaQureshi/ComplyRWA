// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "./GoldHandler.sol";

/// @notice Gold PROPERTY tests. Each `invariant_*` must hold after any sequence of actions.
/// They must pass on every clean configuration (C01 to C08).
contract GoldInvariantsTest is ComplyFixture {
    GoldHandler internal handler;

    function setUp() public virtual override {
        super.setUp();
        handler = new GoldHandler(
            GoldHandler.Ctx({
                token: token,
                ir: ir,
                mbm: maxBalanceModule,
                compliance: address(compliance),
                agent: agent,
                issuerAdmin: issuerAdmin,
                issuer: claimIssuer,
                topic: KYC_TOPIC,
                cap: CAP
            })
        );
        uint256 iA = handler.addIdentity(idA, true);
        uint256 iB = handler.addIdentity(idB, true);
        uint256 iC = handler.addIdentity(idC, true);
        uint256 iM = handler.addIdentity(idM, false); // Mallory: registered, no claim
        handler.addWallet(a1, iA, false);
        handler.addWallet(a2, iA, false);
        handler.addWallet(b, iB, false);
        handler.addWallet(c, iC, true); // Carol lives in country 408
        handler.addWallet(m, iM, false);
        targetContract(address(handler));
    }

    /// G01a (K1): after any successful transfer / transferFrom, the receiver is KYC-verified.
    function invariant_G01a_transferReceiverIsVerified() public {
        assertEq(handler.k1Transfer(), 0, "transfer reached a non-verified receiver");
    }

    /// G01b (K1): after any successful mint / forcedTransfer, the receiver is KYC-verified.
    function invariant_G01b_mintAndForcedReceiverIsVerified() public {
        assertEq(handler.k1MintForced(), 0, "mint or forcedTransfer reached a non-verified receiver");
    }

    /// G03a (J1): after any successful transfer / transferFrom, the receiver is not in a restricted country.
    function invariant_G03a_transferReceiverNotRestricted() public {
        assertEq(handler.j1Transfer(), 0, "transfer reached a restricted-country receiver");
    }

    /// G03b (J1): after any successful mint, the receiver is not in a restricted country.
    function invariant_G03b_mintReceiverNotRestricted() public {
        assertEq(handler.j1Mint(), 0, "mint reached a restricted-country receiver");
    }

    /// G04 (H1): no identity holds more than the POLICY cap (real balances, summed over its wallets).
    function invariant_G04_noIdentityAboveCap() public {
        for (uint256 i = 0; i < handler.idsLength(); i++) {
            assertLe(handler.realOf(i), CAP, "identity above the policy cap");
        }
    }

    /// G05a (H3): after transfer / transferFrom, tracked balance equals real balance for every identity.
    function invariant_G05a_trackedEqualsRealAfterTransfer() public {
        assertEq(handler.h3Transfer(), 0, "counter drift after transfer");
    }

    /// G05b (H3): after mint / burn / forcedTransfer, tracked balance equals real balance for every identity.
    function invariant_G05b_trackedEqualsRealAfterMintBurnForced() public {
        assertEq(handler.h3Other(), 0, "counter drift after mint, burn or forcedTransfer");
    }
}
