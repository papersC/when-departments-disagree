"""Canonical serialisation, signatures, Merkle batching and the on chain
state of the BRAIN framework.

Departmental artefacts are hashed as canonical JSON leaves, signed with the
departmental key and committed one Merkle root per department per epoch. The
departmental roots for an epoch are then bound into a single cross department
commitment, which is what prevents a department from rewriting its own history
in isolation.
"""

import hashlib
import hmac
import json

try:  # pragma: no cover - environment dependent
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    SIGNATURE_SCHEME = "ed25519"
except Exception:  # pragma: no cover
    Ed25519PrivateKey = None
    SIGNATURE_SCHEME = "hmac-sha256"


def canonical(obj) -> bytes:
    """Canonical JSON: sorted keys, no insignificant whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def leaf_hash(obj) -> str:
    return h(b"\x00" + canonical(obj))


def node_hash(a: str, b: str) -> str:
    return h(b"\x01" + bytes.fromhex(a) + bytes.fromhex(b))


class MerkleTree:
    """Binary Merkle tree with duplicate-last padding and inclusion proofs."""

    def __init__(self, leaves):
        self.leaves = list(leaves)
        self.levels = []
        if not self.leaves:
            self.root = h(b"")
            return
        level = list(self.leaves)
        self.levels.append(level)
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = level + [level[-1]]
            nxt = [node_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            self.levels.append(nxt)
            level = nxt
        self.root = level[0]

    def proof(self, index):
        path = []
        idx = index
        for level in self.levels[:-1]:
            lvl = level + [level[-1]] if len(level) % 2 == 1 else level
            sib = idx ^ 1
            path.append((lvl[sib], idx % 2))
            idx //= 2
        return path

    @staticmethod
    def verify(leaf, path, root):
        cur = leaf
        for sib, side in path:
            cur = node_hash(sib, cur) if side == 1 else node_hash(cur, sib)
        return cur == root


class Keyring:
    """One signing key per department."""

    def __init__(self, departments, seed=b"brain-2026"):
        self.scheme = SIGNATURE_SCHEME
        self._priv = {}
        self.pub = {}
        for d in departments:
            material = hashlib.sha256(seed + d.encode()).digest()
            if SIGNATURE_SCHEME == "ed25519":
                k = Ed25519PrivateKey.from_private_bytes(material)
                self._priv[d] = k
                self.pub[d] = k.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw).hex()
            else:
                self._priv[d] = material
                self.pub[d] = h(material)

    def sign(self, dept, payload) -> str:
        msg = canonical(payload)
        if SIGNATURE_SCHEME == "ed25519":
            return self._priv[dept].sign(msg).hex()
        return hmac.new(self._priv[dept], msg, hashlib.sha256).hexdigest()

    def verify(self, dept, payload, signature) -> bool:
        msg = canonical(payload)
        if SIGNATURE_SCHEME == "ed25519":
            from cryptography.exceptions import InvalidSignature
            try:
                self._priv[dept].public_key().verify(bytes.fromhex(signature), msg)
                return True
            except (InvalidSignature, ValueError):
                return False
        return hmac.compare_digest(
            hmac.new(self._priv[dept], msg, hashlib.sha256).hexdigest(), signature)


SIGNABLE_FIELDS = ("artefact_id", "dept", "cls", "policy_family", "policy_version",
                   "effective_from", "effective_to", "claim_type", "subject",
                   "modality", "conditions", "ordering", "text", "quality",
                   "attested", "cited_artefacts")


def signable(artefact):
    return {k: artefact[k] for k in SIGNABLE_FIELDS if k in artefact}


class Ledger:
    """The on chain state: departmental roots, the cross department
    commitment, the versioned authority lattice, the term map and the
    settlement registry."""

    def __init__(self, keyring):
        self.keyring = keyring
        self.dept_roots = {}          # (dept, epoch) -> root
        self.epoch_commitment = {}    # epoch -> root over departmental roots
        self.epoch_departments = {}   # epoch -> departments covered by that root
        self.leaf_index = {}          # artefact_id -> (dept, epoch, index, leaf)
        self.trees = {}               # (dept, epoch) -> MerkleTree
        self.lattice_versions = []    # list of lattice snapshots
        self.settlements = {}         # query_id -> settlement record
        self.tombstones = set()

    def anchor(self, dept, epoch, artefacts):
        leaves = []
        for i, a in enumerate(artefacts):
            payload = signable(a)
            a["signature"] = self.keyring.sign(dept, payload)
            lf = leaf_hash(payload)
            leaves.append(lf)
            self.leaf_index[a["artefact_id"]] = (dept, epoch, i, lf)
        tree = MerkleTree(leaves)
        self.trees[(dept, epoch)] = tree
        self.dept_roots[(dept, epoch)] = tree.root
        return tree.root

    def commit_epoch(self, epoch, departments):
        deps = sorted(departments)
        self.epoch_departments[epoch] = deps
        roots = [self.dept_roots.get((d, epoch), h(b"")) for d in deps]
        self.epoch_commitment[epoch] = MerkleTree(roots).root
        return self.epoch_commitment[epoch]

    def verify_artefact(self, artefact):
        """Inclusion verification at the point of use. Returns True only if the
        artefact hashes to a leaf covered by its departmental root and that
        root is covered by the cross department commitment for its epoch."""
        aid = artefact["artefact_id"]
        if aid in self.tombstones or aid not in self.leaf_index:
            return False
        dept, epoch, idx, stored_leaf = self.leaf_index[aid]
        if leaf_hash(signable(artefact)) != stored_leaf:
            return False
        tree = self.trees[(dept, epoch)]
        if not MerkleTree.verify(stored_leaf, tree.proof(idx), tree.root):
            return False
        if epoch not in self.epoch_commitment:
            return False
        roots = [self.dept_roots.get((d, epoch), h(b""))
                 for d in self.epoch_departments[epoch]]
        return MerkleTree(roots).root == self.epoch_commitment[epoch]

    def register_lattice(self, lattice_snapshot):
        version = len(self.lattice_versions) + 1
        record = dict(version=version, hash=h(canonical(lattice_snapshot)),
                      snapshot=lattice_snapshot)
        self.lattice_versions.append(record)
        return version

    def settle(self, record):
        record = dict(record)
        record["record_hash"] = h(canonical(record))
        self.settlements[record["query_id"]] = record
        return record["record_hash"]
