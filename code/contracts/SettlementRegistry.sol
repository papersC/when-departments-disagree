// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/// @title SettlementRegistry
/// @notice Binds each piece of employee facing guidance to the evidence that
/// produced it. The served context of every consulted department is committed
/// before drafting begins, so a citation of an artefact that was never served
/// is rejectable rather than merely implausible. The settlement then records
/// the claim set, the ordered rule trace, the lattice version in force and the
/// outcome, which is what allows an auditor holding only this record and the
/// anchored partitions to recompute the decision.
/// @dev The contract has not been audited. Gas figures reported in the paper
/// are analytical rather than chain measured.
contract SettlementRegistry {
    enum Outcome { Settled, Partial, Escalated }

    struct ContextCommitment {
        bytes32 servedRoot;   // Merkle root over the artefacts served
        uint64 committedAt;
    }

    struct Settlement {
        bytes32 claimSetHash;
        bytes32 ruleTraceHash;
        bytes32 adviceHash;
        uint256 latticeVersion;
        uint64 settledAt;
        Outcome outcome;
        address reconciler;
    }

    address public immutable anchorAuthority;
    mapping(bytes32 => mapping(address => ContextCommitment)) private context;
    mapping(bytes32 => Settlement) private settlements;

    event ContextCommitted(bytes32 indexed queryId, address indexed department,
                           bytes32 servedRoot);
    event Settled(bytes32 indexed queryId, Outcome outcome, uint256 latticeVersion,
                  bytes32 adviceHash);

    error ContextMissing();
    error AlreadySettled();
    error NotAnchorAuthority();

    constructor() {
        anchorAuthority = msg.sender;
    }

    /// @notice Commit what a department was served, before it drafts.
    function commitContext(bytes32 queryId, bytes32 servedRoot) external {
        context[queryId][msg.sender] = ContextCommitment(servedRoot,
                                                          uint64(block.timestamp));
        emit ContextCommitted(queryId, msg.sender, servedRoot);
    }

    function servedRootOf(bytes32 queryId, address department)
        external view returns (bytes32)
    {
        return context[queryId][department].servedRoot;
    }

    /// @notice Record the settlement. Reverts unless the departments named in
    /// the query committed their served context first, which is the ordering
    /// the framework depends on.
    function settle(bytes32 queryId, address[] calldata departments,
                    bytes32 claimSetHash, bytes32 ruleTraceHash,
                    bytes32 adviceHash, uint256 latticeVersion, Outcome outcome)
        external
    {
        if (settlements[queryId].settledAt != 0) revert AlreadySettled();
        for (uint256 i = 0; i < departments.length; i++) {
            if (context[queryId][departments[i]].servedRoot == bytes32(0)) {
                revert ContextMissing();
            }
        }
        settlements[queryId] = Settlement({
            claimSetHash: claimSetHash,
            ruleTraceHash: ruleTraceHash,
            adviceHash: adviceHash,
            latticeVersion: latticeVersion,
            settledAt: uint64(block.timestamp),
            outcome: outcome,
            reconciler: msg.sender
        });
        emit Settled(queryId, outcome, latticeVersion, adviceHash);
    }

    function settlementOf(bytes32 queryId) external view returns (Settlement memory) {
        return settlements[queryId];
    }

    /// @notice A citation is admissible only if the artefact was in the set
    /// committed for that department before drafting. The caller supplies the
    /// inclusion proof, so the check costs no storage.
    function citationAdmissible(bytes32 queryId, address department,
                                bytes32 leaf, bytes32[] calldata proof,
                                bool[] calldata isRight)
        external view returns (bool)
    {
        bytes32 root = context[queryId][department].servedRoot;
        if (root == bytes32(0)) revert ContextMissing();
        bytes32 cur = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            cur = isRight[i]
                ? keccak256(abi.encodePacked(bytes1(0x01), proof[i], cur))
                : keccak256(abi.encodePacked(bytes1(0x01), cur, proof[i]));
        }
        return cur == root;
    }
}
