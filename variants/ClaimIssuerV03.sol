// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.17;

import "@onchain-id/solidity/contracts/interface/IClaimIssuer.sol";
import "@onchain-id/solidity/contracts/Identity.sol";

contract ClaimIssuerV03 is IClaimIssuer, Identity {
    mapping (bytes => bool) public revokedClaims;

    constructor(address initialManagementKey) Identity(initialManagementKey, false) {}

    function revokeClaimBySignature(bytes calldata signature) external override delegatedOnly onlyManager {
        require(!revokedClaims[signature], "Conflict: Claim already revoked");
        revokedClaims[signature] = true;
        emit ClaimRevoked(signature);
    }

    function revokeClaim(bytes32 _claimId, address _identity) external override delegatedOnly onlyManager returns(bool) {
        uint256 foundClaimTopic;
        uint256 scheme;
        address issuer;
        bytes memory sig;
        bytes memory data;

        ( foundClaimTopic, scheme, issuer, sig, data, ) = Identity(_identity).getClaim(_claimId);

        require(!revokedClaims[sig], "Conflict: Claim already revoked");
        revokedClaims[sig] = true;
        emit ClaimRevoked(sig);
        return true;
    }

    function isClaimValid(
        IIdentity _identity,
        uint256 claimTopic,
        bytes memory sig,
        bytes memory data)
    external override view returns (bool claimValid)
    {
        bytes32 dataHash = keccak256(abi.encode(_identity, claimTopic, data));
        bytes32 prefixedHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", dataHash));
        address recovered = getRecoveredAddress(sig, prefixedHash);
        bytes32 hashedAddr = keccak256(abi.encode(recovered));

        // V03 BUG: the stock code also requires (isClaimRevoked(sig) == false). Revocation is ignored here.
        if (keyHasPurpose(hashedAddr, 3)) {
            return true;
        }
        return false;
    }

    function isClaimRevoked(bytes memory _sig) public override view returns (bool) {
        if (revokedClaims[_sig]) {
            return true;
        }
        return false;
    }

    function getRecoveredAddress(bytes memory sig, bytes32 dataHash)
        public override
        pure
        returns (address addr)
    {
        bytes32 ra;
        bytes32 sa;
        uint8 va;

        if (sig.length != 65) {
            return address(0);
        }

        // solhint-disable-next-line no-inline-assembly
        assembly {
            ra := mload(add(sig, 32))
            sa := mload(add(sig, 64))
            va := byte(0, mload(add(sig, 96)))
        }

        if (va < 27) {
            va += 27;
        }

        address recoveredAddress = ecrecover(dataHash, va, ra, sa);
        return (recoveredAddress);
    }
}