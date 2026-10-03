"""The authority lattice.

The lattice is a versioned artefact registered on the ledger. For each claim
type it names the owning department, the consulted departments and whether the
type is mandatory. For each subject on which two owners can collide it carries
a precedence chain. Registration refuses a lattice whose precedence relation
contains a cycle or whose mandatory types lack a single owner, because either
condition would make deterministic resolution impossible.
"""

from vocab import CLAIM_TYPES, PRECEDENCE, TERM_MAP, TYPES, DEPARTMENTS


class LatticeError(Exception):
    pass


class AuthorityLattice:
    def __init__(self, claim_types=None, precedence=None, term_map=None):
        self.claim_types = {t: dict(v) for t, v in (claim_types or CLAIM_TYPES).items()}
        self.precedence = {s: list(c) for s, c in (precedence or PRECEDENCE).items()}
        self.term_map = {tuple(sorted(x[:2])) + (x[2],) for x in (term_map or TERM_MAP)}
        self.validate()

    # -- registration conditions -------------------------------------------
    def validate(self):
        for t, v in self.claim_types.items():
            if v["owner"] not in DEPARTMENTS:
                raise LatticeError(f"unknown owner for {t}")
            if v["mandatory"] and not v["owner"]:
                raise LatticeError(f"mandatory type {t} without an owner")
            if v["owner"] in v["consulted"]:
                raise LatticeError(f"owner of {t} also listed as consulted")
        for s, chain in self.precedence.items():
            if len(set(chain)) != len(chain):
                raise LatticeError(f"precedence chain for {s} is not a strict order")
        if self._has_cycle():
            raise LatticeError("precedence relation contains a cycle")
        return True

    def _has_cycle(self):
        """The union of the per subject chains must be acyclic as a global
        department relation, otherwise precedence is inconsistent across the
        organisation."""
        edges = set()
        for chain in self.precedence.values():
            for i in range(len(chain) - 1):
                edges.add((chain[i], chain[i + 1]))
        colour = {}

        def visit(n):
            colour[n] = 1
            for a, b in edges:
                if a == n:
                    if colour.get(b) == 1:
                        return True
                    if colour.get(b) is None and visit(b):
                        return True
            colour[n] = 2
            return False

        return any(colour.get(d) is None and visit(d) for d in DEPARTMENTS)

    # -- queries ------------------------------------------------------------
    def owner(self, t):
        return self.claim_types[t]["owner"]

    def consulted(self, t):
        return list(self.claim_types[t]["consulted"])

    def routed(self, t):
        return [self.owner(t)] + self.consulted(t)

    def mandatory(self, t):
        return self.claim_types[t]["mandatory"]

    def precedes(self, subject, d1, d2):
        """Return d1 if d1 outranks d2 on subject, d2 if d2 outranks d1,
        or None if the subject has no registered chain or the departments are
        incomparable under it."""
        chain = self.precedence.get(subject)
        if not chain or d1 not in chain or d2 not in chain:
            return None
        return d1 if chain.index(d1) < chain.index(d2) else d2

    def terms_equated(self, d1, d2, term):
        return (tuple(sorted((d1, d2))) + (term,)) in self.term_map

    def snapshot(self):
        return dict(
            claim_types={t: dict(owner=v["owner"], consulted=sorted(v["consulted"]),
                                 mandatory=v["mandatory"])
                         for t, v in sorted(self.claim_types.items())},
            precedence={s: c for s, c in sorted(self.precedence.items())},
            term_map=sorted("|".join(x) for x in self.term_map),
        )

    # -- ablation and attack helpers ---------------------------------------
    def without_lattice(self):
        """Every department owns every type it is routed to. Used for the
        no lattice ablation."""
        ct = {t: dict(owner=v["owner"], consulted=v["consulted"], mandatory=v["mandatory"])
              for t, v in self.claim_types.items()}
        lat = AuthorityLattice(ct, self.precedence, self.term_map)
        lat.no_projection = True
        return lat

    def with_hostile_registration(self, captured):
        """An adversary with registry write access reassigns ownership of every
        type the captured department is consulted on to that department."""
        ct = {}
        for t, v in self.claim_types.items():
            if captured in v["consulted"]:
                ct[t] = dict(owner=captured,
                             consulted=[x for x in v["consulted"] if x != captured] + [v["owner"]],
                             mandatory=v["mandatory"])
            else:
                ct[t] = dict(v)
        return AuthorityLattice(ct, self.precedence, self.term_map)


def default_lattice():
    lat = AuthorityLattice()
    lat.no_projection = False
    return lat


def types_owned_by(lat, dept):
    return [t for t in TYPES if lat.owner(t) == dept]
