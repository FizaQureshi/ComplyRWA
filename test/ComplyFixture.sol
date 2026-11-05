// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "forge-std/Test.sol";

import "T-REX/contracts/token/Token.sol";
import "T-REX/contracts/registry/implementation/IdentityRegistry.sol";
import "T-REX/contracts/registry/implementation/IdentityRegistryStorage.sol";
import "T-REX/contracts/registry/implementation/ClaimTopicsRegistry.sol";
import "T-REX/contracts/registry/implementation/TrustedIssuersRegistry.sol";
import "T-REX/contracts/compliance/modular/ModularCompliance.sol";
import "T-REX/contracts/compliance/modular/modules/CountryRestrictModule.sol";
import "T-REX/contracts/compliance/modular/modules/MaxBalanceModule.sol";
import "T-REX/contracts/compliance/modular/modules/ModuleProxy.sol";
import "@onchain-id/solidity/contracts/Identity.sol";
import "@onchain-id/solidity/contracts/ClaimIssuer.sol";

/// @notice Shared fixture for ComplyRWA. Builds the clean baseline configuration C01
/// (see Phase2_Scope.md section 1 and section 8). Every step is `internal virtual`,
/// so a variant test can inherit this contract and override only the step it changes.
contract ComplyFixture is Test {
    // ---------------------------------------------------------------- constants
    uint256 internal constant KYC_TOPIC = 1;
    uint16 internal constant INDIA = 356;
    uint16 internal constant RESTRICTED = 408;
    uint256 internal constant CAP = 1000;
    bytes internal constant KYC_DATA = "KYC-OK";

    // ------------------------------------------------------------------- actors
    address internal agent;
    address internal issuerAdmin;
    address internal issuerSigner;
    uint256 internal issuerKey;

    // Alice has two wallets (a1, a2) under one identity (idA). Bob = b, Carol = c, Mallory = m.
    address internal a1;
    address internal a2;
    address internal b;
    address internal c;
    address internal m;
    Identity internal idA;
    Identity internal idB;
    Identity internal idC;
    Identity internal idM;

    // -------------------------------------------------------------------- suite
    ClaimTopicsRegistry internal ctr;
    TrustedIssuersRegistry internal tir;
    IdentityRegistryStorage internal irs;
    IdentityRegistry internal ir;
    ModularCompliance internal compliance;
    Token internal token;
    ClaimIssuer internal claimIssuer;
    CountryRestrictModule internal countryModule;
    MaxBalanceModule internal maxBalanceModule;

    // ------------------------------------------------------------------- set up
    function setUp() public virtual {
        _makeActors();
        _deployRegistries();
        _deployClaimIssuer();
        _deployComplianceAndToken();
        _registerInvestors();
        _wireModules();
        vm.prank(agent);
        token.unpause(); // a fresh T-REX token starts paused
    }

    function _makeActors() internal virtual {
        agent = makeAddr("agent");
        issuerAdmin = makeAddr("issuerAdmin");
        (issuerSigner, issuerKey) = makeAddrAndKey("issuerSigner");
        a1 = makeAddr("alice1");
        a2 = makeAddr("alice2");
        b = makeAddr("bob");
        c = makeAddr("carol");
        m = makeAddr("mallory");
    }

    function _deployRegistries() internal virtual {
        ctr = new ClaimTopicsRegistry();
        ctr.init();
        tir = new TrustedIssuersRegistry();
        tir.init();
        irs = new IdentityRegistryStorage();
        irs.init();
        ir = new IdentityRegistry();
        ir.init(address(tir), address(ctr), address(irs));
        irs.bindIdentityRegistry(address(ir));
        ir.addAgent(agent);
    }

    function _deployClaimIssuer() internal virtual {
        claimIssuer = new ClaimIssuer(issuerAdmin);
        vm.prank(issuerAdmin);
        claimIssuer.addKey(keccak256(abi.encode(issuerSigner)), 3, 1); // purpose 3 = claim signer
        ctr.addClaimTopic(KYC_TOPIC);
        uint256[] memory topics = new uint256[](1);
        topics[0] = KYC_TOPIC;
        tir.addTrustedIssuer(IClaimIssuer(address(claimIssuer)), topics);
    }

    function _deployComplianceAndToken() internal virtual {
        compliance = new ModularCompliance();
        compliance.init();
        token = new Token();
        token.init(address(ir), address(compliance), "ComplyToken", "CPLY", 0, address(0));
        token.addAgent(agent);
        ir.addAgent(address(token)); // needed by recoveryAddress
    }

    function _registerInvestors() internal virtual {
        idA = new Identity(a1, false);
        idB = new Identity(b, false);
        idC = new Identity(c, false);
        idM = new Identity(m, false);

        vm.startPrank(agent);
        ir.registerIdentity(a1, IIdentity(address(idA)), INDIA);
        ir.registerIdentity(a2, IIdentity(address(idA)), INDIA);
        ir.registerIdentity(b, IIdentity(address(idB)), INDIA);
        ir.registerIdentity(c, IIdentity(address(idC)), RESTRICTED);
        ir.registerIdentity(m, IIdentity(address(idM)), INDIA); // registered, but no claim
        vm.stopPrank();

        _issueClaim(idA, a1);
        _issueClaim(idB, b);
        _issueClaim(idC, c);
    }

    function _wireModules() internal virtual {
        CountryRestrictModule crImpl = new CountryRestrictModule();
        countryModule = CountryRestrictModule(
            address(new ModuleProxy(address(crImpl), abi.encodeWithSelector(CountryRestrictModule.initialize.selector)))
        );
        MaxBalanceModule mbImpl = new MaxBalanceModule();
        maxBalanceModule = MaxBalanceModule(
            address(new ModuleProxy(address(mbImpl), abi.encodeWithSelector(MaxBalanceModule.initialize.selector)))
        );

        // The token is already bound (Token.init does it), and no tokens exist yet,
        // so MaxBalanceModule.canComplianceBind is true.
        compliance.addModule(address(countryModule));
        compliance.addModule(address(maxBalanceModule));
        compliance.callModuleFunction(
            abi.encodeWithSelector(CountryRestrictModule.addCountryRestriction.selector, RESTRICTED),
            address(countryModule)
        );
        compliance.callModuleFunction(
            abi.encodeWithSelector(MaxBalanceModule.setMaxBalance.selector, CAP),
            address(maxBalanceModule)
        );
    }

    // ------------------------------------------------------------------ helpers
    /// @dev Signs exactly what ClaimIssuer.isClaimValid rebuilds: the data hash with the
    /// "Ethereum Signed Message" prefix. Returns r, s, v separately for malleability tests.
    function _rsv(Identity id, uint256 topic, bytes memory data)
        internal
        view
        returns (uint8 v, bytes32 r, bytes32 s)
    {
        bytes32 dataHash = keccak256(abi.encode(address(id), topic, data));
        bytes32 prefixed = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", dataHash));
        (v, r, s) = vm.sign(issuerKey, prefixed);
    }

    function _issueClaim(Identity id, address wallet) internal {
        _issueClaim(id, wallet, KYC_TOPIC, KYC_DATA);
    }

    function _issueClaim(Identity id, address wallet, uint256 topic, bytes memory data) internal {
        (uint8 v, bytes32 r, bytes32 s) = _rsv(id, topic, data);
        vm.prank(wallet); // the investor's wallet is the management key of its own identity
        id.addClaim(topic, 1, address(claimIssuer), abi.encodePacked(r, s, v), data, "");
    }

    function _revokeClaim(Identity id) internal {
        bytes32 claimId = keccak256(abi.encode(address(claimIssuer), KYC_TOPIC));
        vm.prank(issuerAdmin);
        claimIssuer.revokeClaim(claimId, address(id));
    }

    function _mint(address to, uint256 amount) internal {
        vm.prank(agent);
        token.mint(to, amount);
    }

    function _transfer(address from, address to, uint256 amount) internal {
        vm.prank(from);
        token.transfer(to, amount);
    }

    function _idBalance(Identity id) internal view returns (uint256) {
        return maxBalanceModule.getIDBalance(address(compliance), address(id));
    }
}
