"""Departmental agents.

A departmental agent retrieves from its own partition, commits the served set
and drafts typed claims against it. The agent is simulated by a parameterised
generator with six failure modes, each corresponding to a failure documented
for language models grounded in retrieved context: omission of supported
content, unsupported assertion, modality drift, reliance on superseded
material, citation of unserved material, and assertion outside the agent's own
mandate. The failure vector is scaled by a single parameter lambda, and every
reported result is a function of lambda rather than a value at an assumed
operating point.
"""

import random

from vocab import DEONTIC, BINDING, CLAIM_TYPES, SUBJECTS, SUBJECT_LIST
from ledger import MerkleTree, leaf_hash, signable

BASE_FAILURE = dict(
    omit=0.25,        # a supported rule is not asserted
    spurious=0.20,    # an obligation is asserted that no served rule supports
    modality=0.15,    # the modality of a supported rule is drifted
    stale=0.30,       # a superseded served artefact is preferred
    fabricate=0.12,   # a citation is emitted that was never served
    overreach=0.25,   # a deontic claim is issued outside the agent's mandate
)


def failure_vector(lam, base=None):
    base = base or BASE_FAILURE
    return {k: min(1.0, lam * v) for k, v in base.items()}


class DepartmentalAgent:
    def __init__(self, dept, corpus, ledger, indexes, lattice, k=8):
        self.dept = dept
        self.corpus = corpus
        self.ledger = ledger
        self.indexes = indexes
        self.lattice = lattice
        self.k = k

    # -- retrieval and commitment ------------------------------------------
    def serve(self, situation, types):
        from retrieval import type_focus
        hits = self.indexes.dept(self.dept, type_focus(situation, types), self.k)
        served = [a for a, _ in hits if self.ledger.verify_artefact(a)]
        root = MerkleTree([leaf_hash(signable(a)) for a in served]).root
        return served, root

    # -- completeness probe -------------------------------------------------
    def probe(self, ctype, subject, quarter):
        """Exact existence query over this department's own partition.

        Similarity retrieval answers what a partition says about a situation.
        It cannot answer whether a partition says anything at all, because the
        absence of a passage from a ranked list is not the absence of a rule.
        The probe is a deterministic lookup on claim type, subject and date,
        which a department can answer over its own store at negligible cost,
        and it is what separates an organisational gap from a retrieval miss."""
        for a in self.corpus.rules.get((self.dept, quarter), ()):
            if a["claim_type"] == ctype and a["subject"] == subject:
                return a
        return None

    # -- drafting -----------------------------------------------------------
    def draft(self, scenario, types, fv, rng, adversary=None, mandate_aware=True):
        """Return (served, served_root, claims). types is the set of claim
        types the lattice routed to this department. When mandate_aware is
        False the agent asserts deontically on every type it is asked about,
        which is the behaviour of a departmental assistant deployed without a
        lattice."""
        served, root = self.serve(scenario["situation"], types)
        q = scenario["quarter"]
        claims = []
        by_key = {}
        for a in served:
            if a["cls"] not in ("policy", "position") or a["claim_type"] is None:
                continue
            if a["claim_type"] not in types:
                continue
            by_key.setdefault((a["claim_type"], a["subject"]), []).append(a)

        def in_window(a):
            hi = a["effective_to"]
            return a["effective_from"] <= q and (hi is None or q <= hi)

        for (ctype, subject), cands in sorted(by_key.items()):
            current = [a for a in cands if in_window(a)]
            stale = [a for a in cands if not in_window(a)]
            if rng.random() < fv["stale"] and stale:
                src = max(stale, key=lambda a: a["policy_version"])
            elif current:
                src = max(current, key=lambda a: a["policy_version"])
            elif stale:
                src = max(stale, key=lambda a: a["policy_version"])
            else:
                continue
            if rng.random() < fv["omit"]:
                continue
            is_owner = self.lattice.owner(ctype) == self.dept
            modality = src["modality"]
            overreach = False
            if not is_owner and mandate_aware:
                # a well behaved consulted department contributes context, not
                # obligation; overreach is the failure that does otherwise
                if rng.random() >= fv["overreach"]:
                    modality = "fact"
                else:
                    overreach = modality in DEONTIC
            elif not is_owner:
                overreach = modality in DEONTIC
            if adversary == "inflate" and not is_owner:
                modality = src["modality"] if src["modality"] in DEONTIC else "must"
                overreach = True
            if modality in DEONTIC and rng.random() < fv["modality"]:
                modality = rng.choice([m for m in ["must", "must_not", "should",
                                                   "should_not"] if m != modality])
            citations = [src["artefact_id"]]
            if rng.random() < fv["fabricate"]:
                citations = citations + [f"A{rng.randrange(90000, 99999)}"]
            cl = self._claim(rng, ctype, subject, modality, src, citations, root)
            cl["overreach"] = overreach
            cl["used_stale"] = not in_window(src)
            cl["fabricated_citation"] = len(citations) > 1
            claims.append(cl)

        # unsupported assertion
        n_spurious = sum(1 for _ in range(max(1, len(claims)))
                         if rng.random() < fv["spurious"])
        owned = [t for t in types if self.lattice.owner(t) == self.dept] or list(types)
        for _ in range(n_spurious):
            t = rng.choice(owned)
            subs = [s for s in SUBJECT_LIST if t in SUBJECTS[s]]
            if not subs:
                continue
            s = rng.choice(subs)
            src = served[rng.randrange(len(served))] if served else None
            cl = self._claim(
                rng, t, s, rng.choice(["must", "must_not", "should"]),
                src, [src["artefact_id"]] if src else [], root, spurious=True)
            cl["overreach"] = self.lattice.owner(t) != self.dept
            cl["used_stale"] = False
            cl["fabricated_citation"] = False
            claims.append(cl)
        return served, root, claims

    def _claim(self, rng, ctype, subject, modality, src, citations, root,
               spurious=False):
        return dict(
            claim_id=f"{self.dept}-{ctype}-{subject}-{rng.randrange(1 << 30):08x}",
            dept=self.dept, ctype=ctype, subject=subject, modality=modality,
            conditions=list(src["conditions"]) if src else [],
            ordering=[list(e) for e in (src.get("ordering") or [])] if src else [],
            policy_family=src["policy_family"] if src else None,
            policy_version=src["policy_version"] if src else 0,
            effective_from=src["effective_from"] if src else 0,
            effective_to=src["effective_to"] if src else None,
            quality=src["quality"] if src else 0.5,
            citations=list(citations), served_root=root,
            confidence=round(rng.uniform(0.55, 0.99), 3),
            verbosity=len(src["text"]) if src else 0,
            spurious=spurious,
        )


def route(lattice, types):
    """Departments the lattice routes to, with the claim types each is asked
    about."""
    plan = {}
    for t in types:
        for d in lattice.routed(t):
            plan.setdefault(d, set()).add(t)
    return {d: sorted(ts) for d, ts in sorted(plan.items())}
