// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "forge-std/Test.sol";
import "../ComplyFixture.sol";

/// @notice Random-action driver for the gold PROPERTY tests (G01a, G01b, G03a, G03b, G05a, G05b).
/// It keeps its own "ground truth" (ghost state) of who is KYC-verified and who lives in a
/// restricted country, because the contracts under audit may be the thing that is broken.
/// A property is violated when an action SUCCEEDS although the ground truth says it must not.
contract GoldHandler is Test {
    struct Ctx {
        Token token;
        IdentityRegistry ir;
        MaxBalanceModule mbm;
        address compliance;
        address agent;
        address issuerAdmin;
        ClaimIssuer issuer;
        uint256 topic;
        uint256 cap;
        uint16 restrictedA;
        uint16 restrictedB; // 0 = none
    }

    Ctx internal x;
    address internal immutable owner; // only the test contract may register identities and wallets
    address[] internal wallets;
    Identity[] internal ids;
    mapping(address => uint256) internal idIdx; // wallet -> index in ids
    mapping(uint256 => bool) internal kycOK; // ground truth, per identity index
    mapping(address => bool) internal restricted; // ground truth: wallet is in a restricted country

    // Violation counters (every one must stay 0)
    uint256 public k1Transfer; // G01a
    uint256 public k1MintForced; // G01b
    uint256 public j1Transfer; // G03a
    uint256 public j1Mint; // G03b
    uint256 public h3Transfer; // G05a
    uint256 public h3Other; // G05b

    // Reachability counters (successful actions), useful to see the run did something
    uint256 public okTransfer;
    uint256 public okMint;
    uint256 public okForced;
    uint256 public okBurn;
    uint256 public okRevoke;
    uint256 public okCountry;

    constructor(Ctx memory ctx) {
        x = ctx;
        owner = msg.sender;
    }

    // ------------------------------------------------------------- registration
    function addIdentity(Identity id, bool kyc) external returns (uint256 idx) {
        require(msg.sender == owner, "setup only");
        ids.push(id);
        idx = ids.length - 1;
        kycOK[idx] = kyc;
    }

    function addWallet(address w, uint256 idx, bool isRestricted) external {
        require(msg.sender == owner, "setup only");
        wallets.push(w);
        idIdx[w] = idx;
        restricted[w] = isRestricted;
    }

    // ------------------------------------------------------------------ views
    function idsLength() external view returns (uint256) {
        return ids.length;
    }

    function realOf(uint256 idx) public view returns (uint256 total) {
        for (uint256 i = 0; i < wallets.length; i++) {
            if (idIdx[wallets[i]] == idx) total += x.token.balanceOf(wallets[i]);
        }
    }

    // ---------------------------------------------------------------- actions
    function mint(uint256 toSeed, uint256 amount) external {
        address to = _w(toSeed);
        amount = bound(amount, 1, x.cap + 200);
        vm.prank(x.agent);
        try x.token.mint(to, amount) {
            okMint++;
            if (!kycOK[idIdx[to]]) k1MintForced++;
            if (restricted[to]) j1Mint++;
            if (_h3Broken()) h3Other++;
        } catch {}
    }

    function transfer(uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        address from = _w(fromSeed);
        address to = _w(toSeed);
        uint256 bal = x.token.balanceOf(from);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(from);
        try x.token.transfer(to, amount) returns (bool) {
            _afterTransfer(to);
        } catch {}
    }

    function transferFrom(uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        address from = _w(fromSeed);
        address to = _w(toSeed);
        uint256 bal = x.token.balanceOf(from);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(from);
        x.token.approve(address(this), amount);
        try x.token.transferFrom(from, to, amount) returns (bool) {
            _afterTransfer(to);
        } catch {}
    }

    function forcedTransfer(uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        address from = _w(fromSeed);
        address to = _w(toSeed);
        uint256 bal = x.token.balanceOf(from);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(x.agent);
        try x.token.forcedTransfer(from, to, amount) returns (bool) {
            okForced++;
            if (!kycOK[idIdx[to]]) k1MintForced++;
            // J1 is NOT checked here: forcedTransfer is a known exception (D1, J4).
            if (_h3Broken()) h3Other++;
        } catch {}
    }

    function burn(uint256 fromSeed, uint256 amount) external {
        address from = _w(fromSeed);
        uint256 bal = x.token.balanceOf(from);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(x.agent);
        try x.token.burn(from, amount) {
            okBurn++;
            if (_h3Broken()) h3Other++;
        } catch {}
    }

    /// @dev Revokes the KYC claim of an identity at the issuer. Identities without a claim are skipped.
    function revokeKyc(uint256 idSeed) external {
        uint256 idx = bound(idSeed, 0, ids.length - 1);
        if (!kycOK[idx]) return;
        bytes32 claimId = keccak256(abi.encode(address(x.issuer), x.topic));
        vm.prank(x.issuerAdmin);
        try x.issuer.revokeClaim(claimId, address(ids[idx])) returns (bool) {
            kycOK[idx] = false;
            okRevoke++;
        } catch {}
    }

    /// @dev Moves a wallet into a restricted country (policy list) or back to 356.
    function setRestricted(uint256 walletSeed, bool flag) external {
        address w = _w(walletSeed);
        vm.prank(x.agent);
        uint16 country = 356;
        if (flag) country = (walletSeed % 2 == 1 && x.restrictedB != 0) ? x.restrictedB : x.restrictedA;
        try x.ir.updateCountry(w, country) {
            restricted[w] = flag;
            okCountry++;
        } catch {}
    }

    // ---------------------------------------------------------------- internals
    function _afterTransfer(address to) internal {
        okTransfer++;
        if (!kycOK[idIdx[to]]) k1Transfer++;
        if (restricted[to]) j1Transfer++;
        if (_h3Broken()) h3Transfer++;
    }

    function _w(uint256 seed) internal view returns (address) {
        return wallets[bound(seed, 0, wallets.length - 1)];
    }

    /// @dev True if the module's tracked balance differs from the real balance for any identity.
    function _h3Broken() internal view returns (bool) {
        for (uint256 i = 0; i < ids.length; i++) {
            if (x.mbm.getIDBalance(x.compliance, address(ids[i])) != realOf(i)) return true;
        }
        return false;
    }
}
