// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/// @title AuthorityLattice
/// @notice The versioned allocation of mandate. For each claim type the
/// lattice names the owning department and the departments that are consulted,
/// and for each subject on which two owners can collide it carries a
/// precedence chain. A registration is refused unless it is signed by a quorum
/// of registrars, which is the only mitigation the design offers against the
/// governance single point of failure the paper states plainly.
/// @dev The contract has not been audited. Gas figures reported in the paper
/// are analytical rather than chain measured.
contract AuthorityLattice {
    struct TypeRule {
        bytes32 claimType;
        address owner;          // the owning department's registered identity
        bytes32 consultedHash;  // commitment to the consulted set
        bool mandatory;
    }

    struct Version {
        bytes32 latticeHash;    // canonical hash of the whole snapshot
        uint64 registeredAt;
        address[] approvals;
    }

    address public admin;
    uint8 public quorum;
    mapping(address => bool) public registrar;
    mapping(bytes32 => TypeRule) private rules;      // claimType => rule
    mapping(bytes32 => bytes32) private precedence;  // subject => chain hash
    Version[] public versions;

    mapping(bytes32 => mapping(address => bool)) private approved;
    mapping(bytes32 => uint8) private approvals;

    event LatticeProposed(bytes32 indexed latticeHash, address indexed by);
    event LatticeRegistered(uint256 indexed version, bytes32 indexed latticeHash);

    error NotRegistrar();
    error AlreadyApproved();
    error QuorumNotMet();

    constructor(address[] memory registrars, uint8 q) {
        admin = msg.sender;
        quorum = q;
        for (uint256 i = 0; i < registrars.length; i++) {
            registrar[registrars[i]] = true;
        }
    }

    modifier onlyRegistrar() {
        if (!registrar[msg.sender]) revert NotRegistrar();
        _;
    }

    /// @notice Approve a candidate lattice snapshot. Registration happens
    /// automatically once the quorum is reached, and the version number is the
    /// value every settlement records.
    function approve(bytes32 latticeHash) external onlyRegistrar {
        if (approved[latticeHash][msg.sender]) revert AlreadyApproved();
        approved[latticeHash][msg.sender] = true;
        approvals[latticeHash] += 1;
        emit LatticeProposed(latticeHash, msg.sender);
        if (approvals[latticeHash] >= quorum) {
            versions.push();
            Version storage v = versions[versions.length - 1];
            v.latticeHash = latticeHash;
            v.registeredAt = uint64(block.timestamp);
            emit LatticeRegistered(versions.length, latticeHash);
        }
    }

    function setTypeRule(bytes32 claimType, address owner_, bytes32 consultedHash,
                         bool mandatory) external onlyRegistrar {
        rules[claimType] = TypeRule(claimType, owner_, consultedHash, mandatory);
    }

    function setPrecedence(bytes32 subject, bytes32 chainHash) external onlyRegistrar {
        precedence[subject] = chainHash;
    }

    function ownerOf(bytes32 claimType) external view returns (address) {
        return rules[claimType].owner;
    }

    function isMandatory(bytes32 claimType) external view returns (bool) {
        return rules[claimType].mandatory;
    }

    function precedenceOf(bytes32 subject) external view returns (bytes32) {
        return precedence[subject];
    }

    function currentVersion() external view returns (uint256) {
        return versions.length;
    }
}
