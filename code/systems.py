"""The six systems under comparison.

B0  language model alone, no retrieval
B1  pooled retrieval augmented generation, department field discarded
B2  pooled retrieval with the department field retained, no reconciliation
B3  independent departmental agents, outputs concatenated
B4  independent departmental agents with a referee that selects a winner
B5  the proposed framework

Every system uses the same retriever, the same drafting failure vector and the
same served volume, so differences are attributable to the architecture rather
than to the model or to the amount of context.
"""

import random
from collections import Counter, defaultdict

from vocab import DEONTIC, SUBJECTS, SUBJECT_LIST, CLAIM_TYPES, INCOMPATIBLE
from agents import DepartmentalAgent, route
from reconcile import Reconciler
from ledger import MerkleTree, leaf_hash, signable


class PooledAgent:
    """Drafts from one flat index with no notion of a partition."""

    def __init__(self, corpus, ledger, indexes, k):
        self.corpus, self.ledger, self.indexes, self.k = corpus, ledger, indexes, k

    def draft(self, scenario, types, fv, rng, keep_dept):
        from retrieval import type_focus
        hits = self.indexes.pool(type_focus(scenario["situation"], types), self.k)
        served = [a for a, _ in hits if self.ledger.verify_artefact(a)]
        rank = {a["artefact_id"]: i for i, (a, _) in enumerate(hits)}
        root = MerkleTree([leaf_hash(signable(a)) for a in served]).root
        q = scenario["quarter"]
        best = {}
        for a in served:
            if a["cls"] not in ("policy", "position") or a["claim_type"] not in types:
                continue
            key = (a["claim_type"], a["subject"])
            # pooling gives the generator no basis for choosing other than rank
            if key not in best or rank[a["artefact_id"]] < rank[best[key]["artefact_id"]]:
                best[key] = a
        claims = []
        for (ctype, subject), src in sorted(best.items()):
            if rng.random() < fv["omit"]:
                continue
            modality = src["modality"]
            if modality in DEONTIC and rng.random() < fv["modality"]:
                modality = rng.choice([m for m in ["must", "must_not", "should",
                                                   "should_not"] if m != modality])
            hi = src["effective_to"]
            stale = not (src["effective_from"] <= q and (hi is None or q <= hi))
            claims.append(dict(
                claim_id=f"P-{ctype}-{subject}", dept=(src["dept"] if keep_dept else None),
                ctype=ctype, subject=subject, modality=modality,
                conditions=list(src["conditions"]), ordering=[list(e) for e in src["ordering"]],
                policy_version=src["policy_version"], quality=src["quality"],
                effective_from=src["effective_from"], effective_to=src["effective_to"],
                citations=[src["artefact_id"]], served_root=root,
                confidence=round(rng.uniform(0.55, 0.99), 3),
                verbosity=len(src["text"]), spurious=False, overreach=False,
                used_stale=stale, fabricated_citation=False))
        n_sp = sum(1 for _ in range(max(1, len(claims))) if rng.random() < fv["spurious"])
        for _ in range(n_sp):
            t = rng.choice(list(types))
            subs = [s for s in SUBJECT_LIST if t in SUBJECTS[s]]
            if not subs or not served:
                continue
            src = served[rng.randrange(len(served))]
            claims.append(dict(
                claim_id=f"P-sp-{rng.randrange(1 << 30):08x}",
                dept=(src["dept"] if keep_dept else None), ctype=t,
                subject=rng.choice(subs), modality=rng.choice(["must", "must_not", "should"]),
                conditions=[], ordering=[], policy_version=src["policy_version"],
                quality=src["quality"], effective_from=src["effective_from"],
                effective_to=src["effective_to"], citations=[src["artefact_id"]],
                served_root=root, confidence=round(rng.uniform(0.55, 0.99), 3),
                verbosity=len(src["text"]), spurious=True, overreach=False,
                used_stale=False, fabricated_citation=False))
        return served, root, claims


class Runner:
    def __init__(self, corpus, ledger, indexes, lattice, k=8):
        self.corpus, self.ledger, self.indexes, self.lat = corpus, ledger, indexes, lattice
        self.k = k
        self.artefact_by_id = {a["artefact_id"]: a for a in corpus.artefacts}
        self.agents = {d: DepartmentalAgent(d, corpus, ledger, indexes, lattice, k)
                       for d in corpus.departments}
        self.pooled = PooledAgent(corpus, ledger, indexes, k)
        self._prior = self._generic_prior()

    def _generic_prior(self):
        c = defaultdict(Counter)
        for a in self.corpus.artefacts:
            if a["cls"] == "policy":
                c[(a["claim_type"], a["subject"])][a["modality"]] += 1
        return {k: v.most_common(1)[0][0] for k, v in c.items()}

    # -- systems ------------------------------------------------------------
    def b0(self, scenario, fv, rng):
        """No retrieval. Generic professional practice, unconditioned on this
        organisation's policy state."""
        obligations, attribution = {}, {}
        for t in scenario["types"]:
            for s in [x for x in SUBJECT_LIST if t in SUBJECTS[x]]:
                m = self._prior.get((t, s))
                if m in DEONTIC:
                    obligations[f"{t}|{s}"] = m
                    attribution[f"{t}|{s}"] = None
        extra = [t for t in self.corpus.types if t not in scenario["types"]]
        for t in rng.sample(extra, min(2, len(extra))):
            for s in [x for x in SUBJECT_LIST if t in SUBJECTS[x]][:2]:
                m = self._prior.get((t, s))
                if m in DEONTIC:
                    obligations[f"{t}|{s}"] = m
                    attribution[f"{t}|{s}"] = None
        return dict(obligations=obligations, attribution=attribution, support={},
                    escalations=[], escalated=False, served={}, claims=[],
                    detected={}, served_count=0)

    def _pooled_system(self, scenario, fv, rng, keep_dept):
        plan = route(self.lat, scenario["types"])
        k = self.k * max(1, len(plan))
        self.pooled.k = k
        served, root, claims = self.pooled.draft(scenario, scenario["types"], fv,
                                                 rng, keep_dept)
        obligations, attribution, support, stale_flags = {}, {}, {}, {}
        for c in claims:
            if c["modality"] not in DEONTIC:
                continue
            key = f"{c['ctype']}|{c['subject']}"
            obligations[key] = c["modality"]
            attribution[key] = c["dept"]
            support[key] = c["citations"]
            stale_flags[key] = bool(c.get("used_stale"))
        return dict(obligations=obligations, attribution=attribution, support=support,
                    stale_flags=stale_flags,
                    escalations=[], escalated=False, served={"POOL": served},
                    claims=claims, detected={}, served_count=len(served))

    def b1(self, scenario, fv, rng):
        return self._pooled_system(scenario, fv, rng, keep_dept=False)

    def b2(self, scenario, fv, rng):
        return self._pooled_system(scenario, fv, rng, keep_dept=True)

    def _departmental(self, scenario, fv, rng, mandate_aware, all_departments,
                      adversary=None, captured=None):
        if all_departments:
            plan = {d: sorted(scenario["types"]) for d in self.corpus.departments}
        else:
            plan = {d: ts for d, ts in route(self.lat, scenario["types"]).items()
                    if d in self.agents}
        served_by, claims = {}, []
        for d, types in plan.items():
            adv = adversary if (captured and d == captured) else None
            s, root, cs = self.agents[d].draft(scenario, types, fv, rng, adv,
                                               mandate_aware=mandate_aware)
            served_by[d] = s
            claims.extend(cs)
        return plan, served_by, claims

    def b3(self, scenario, fv, rng):
        _, served_by, claims = self._departmental(scenario, fv, rng, False, True)
        obligations, attribution, support, stale_flags = {}, {}, {}, {}
        for c in claims:
            if c["modality"] not in DEONTIC:
                continue
            key = f"{c['ctype']}|{c['subject']}"
            obligations[key] = c["modality"]
            attribution[key] = c["dept"]
            support[key] = c["citations"]
            stale_flags[key] = bool(c.get("used_stale"))
        return dict(obligations=obligations, attribution=attribution, support=support,
                    stale_flags=stale_flags,
                    escalations=[], escalated=False, served=served_by, claims=claims,
                    detected={}, served_count=sum(len(v) for v in served_by.values()))

    def b3p(self, scenario, fv, rng):
        """Departmental agents with the completeness probe but without the
        lattice. Every department is probed for every raised pair, because
        without a lattice there is no owner to probe, and everything found is
        admitted. This isolates whether the probe alone accounts for the
        difference or whether it depends on the projection."""
        from vocab import SUBJECTS as SUBJ
        out = self.b3(scenario, fv, rng)
        settled = {tuple(k.split("|")) for k in out["obligations"]}
        for t in scenario["types"]:
            for sub in sorted(x for x in scenario.get("subjects", []) if t in SUBJ[x]):
                if (t, sub) in settled:
                    continue
                for d, ag in self.agents.items():
                    art = ag.probe(t, sub, scenario["quarter"])
                    if art is None:
                        continue
                    key = f"{t}|{sub}"
                    if key in out["obligations"]:
                        continue
                    out["obligations"][key] = art["modality"]
                    out["attribution"][key] = art["dept"]
                    out["support"][key] = [art["artefact_id"]]
                    out["stale_flags"][key] = False
        return out

    def b4(self, scenario, fv, rng):
        """A referee selects among contradictory claims by reported confidence,
        breaking ties by length. This is a proxy for a model judge and carries
        the verbosity preference such judges are documented to exhibit; it is
        not a measurement of any particular model."""
        _, served_by, claims = self._departmental(scenario, fv, rng, False, True)
        by_subject = defaultdict(list)
        for c in claims:
            if c["modality"] in DEONTIC:
                by_subject[c["subject"]].append(c)
        obligations, attribution, support, stale_flags = {}, {}, {}, {}
        for s, cs in sorted(by_subject.items()):
            mods = {c["modality"] for c in cs}
            if any((a, b) in INCOMPATIBLE for a in mods for b in mods):
                cs = [max(cs, key=lambda c: (c["confidence"], c["verbosity"]))]
            for c in cs:
                key = f"{c['ctype']}|{c['subject']}"
                if key in obligations:
                    continue
                obligations[key] = c["modality"]
                attribution[key] = c["dept"]
                support[key] = c["citations"]
                stale_flags[key] = bool(c.get("used_stale"))
        return dict(obligations=obligations, attribution=attribution, support=support,
                    stale_flags=stale_flags,
                    escalations=[], escalated=False, served=served_by, claims=claims,
                    detected={}, served_count=sum(len(v) for v in served_by.values()))

    def b5(self, scenario, fv, rng, rules_enabled=None, lattice=None,
            adversary=None, captured=None):
        lat = lattice or self.lat
        rec = Reconciler(lat, self.ledger, rules_enabled)
        saved = self.lat
        self.lat = lat
        for a in self.agents.values():
            a.lattice = lat
        try:
            plan, served_by, claims = self._departmental(
                scenario, fv, rng, True, False, adversary=adversary, captured=captured)
        finally:
            self.lat = saved
            for a in self.agents.values():
                a.lattice = saved
        def probe(dept, ctype, subject, quarter):
            ag = self.agents.get(dept)
            return ag.probe(ctype, subject, quarter) if ag else None

        out = rec.reconcile(scenario, served_by, claims, self.artefact_by_id,
                            probe=probe, fv=fv, rng=rng)
        out["served"] = served_by
        out["claims"] = claims
        out["served_count"] = sum(len(v) for v in served_by.values())
        return out


SYSTEMS = ["B0", "B1", "B2", "B3", "B3P", "B4", "B5"]
SYSTEM_LABELS = {
    "B0": "no retrieval",
    "B1": "pooled RAG",
    "B2": "pooled RAG, dept labels",
    "B3": "departmental agents, concatenated",
    "B3P": "departmental agents with completeness probe, no lattice",
    "B4": "departmental agents, referee",
    "B5": "BRAIN",
}
