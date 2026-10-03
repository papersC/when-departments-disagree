"""Corpus generator.

Five departments issue policy artefacts on independent revision schedules over
twenty quarters. Every artefact is a single rule, so retrieval granularity and
assertion granularity coincide. Precedents and definitions are generated as
additional retrievable material. Scenarios are employee questions that engage
several claim types owned by different departments, and each scenario carries
ground truth computed from the corpus and the lattice alone, without reference
to any system that will later be evaluated.
"""

import random
from collections import defaultdict

from vocab import (DEPARTMENTS, CLAIM_TYPES, TYPES, SUBJECTS, SUBJECT_LIST,
                   PREDICATES, DEFINED_TERMS, POLICY_FAMILIES, FAMILY_TYPES,
                   TYPE_FAMILY, REVISION_CADENCE, N_QUARTERS, MANDATORY_TYPES,
                   BINDING, INCOMPATIBLE, DEONTIC, ORDER_CYCLES, ORDER_P)

ORDER_LOOKUP = {}
for tA, sA, tB, sB in ORDER_CYCLES:
    ORDER_LOOKUP[(tA, sA)] = (sA, sB)
    ORDER_LOOKUP[(tB, sB)] = (sB, sA)

SEED = 20260902

# Subjects spoken about by claim types with two different owners.
SHARED_SUBJECTS = {}
for s, ts in SUBJECTS.items():
    owners = {CLAIM_TYPES[t]["owner"] for t in ts}
    if len(owners) > 1:
        SHARED_SUBJECTS[s] = ts

FILLER = ("procedure applies organisation wide and supersedes local practice "
          "the responsible unit records the decision and retains supporting "
          "evidence for subsequent review").split()

SUBJECT_WORDS = {s: s.replace("_", " ") for s in SUBJECT_LIST}
TYPE_WORDS = {t: t.replace("_", " ") for t in TYPES}


def _text(rng, ctype, subject, modality, conditions):
    words = [TYPE_WORDS[ctype], SUBJECT_WORDS[subject]]
    words += [c.replace("_", " ") for c in conditions]
    words.append({"must": "is required to", "must_not": "is prohibited from",
                  "should": "is expected to", "should_not": "is discouraged from",
                  "may": "is permitted to", "fact": "is recorded as"}[modality])
    words += rng.sample(FILLER, k=6)
    rng.shuffle(words)
    return " ".join(words)


class Corpus:
    def __init__(self, seed=SEED, n_scenarios=400, departments=None):
        self.rng = random.Random(seed)
        self.departments = departments or list(DEPARTMENTS)
        self.types = [t for t in TYPES if CLAIM_TYPES[t]["owner"] in self.departments]
        self.artefacts = []
        self.by_dept = defaultdict(list)
        self.rules = defaultdict(list)      # (dept, quarter) -> artefacts effective
        self.definitions = {}               # (dept, term) -> definition id
        self._build_definitions()
        self._build_policies()
        self._build_positions()
        self._build_precedents()
        self.scenarios = self._build_scenarios(n_scenarios)

    # -- artefact construction ---------------------------------------------
    def _add(self, **kw):
        kw.setdefault("artefact_id", f"A{len(self.artefacts):05d}")
        kw.setdefault("conditions", [])
        kw.setdefault("ordering", [])
        kw.setdefault("cited_artefacts", [])
        kw.setdefault("quality", round(self.rng.uniform(0.55, 0.98), 3))
        kw.setdefault("attested", self.rng.random() < 0.7)
        self.artefacts.append(kw)
        self.by_dept[kw["dept"]].append(kw)
        return kw

    def _build_definitions(self):
        from vocab import TERM_MAP
        equated = defaultdict(list)
        for d1, d2, term in TERM_MAP:
            equated[term].append((d1, d2))
        for term in DEFINED_TERMS:
            groups = {}
            for d in self.departments:
                placed = False
                for other, gid in list(groups.items()):
                    if (d, other) in equated[term] or (other, d) in equated[term]:
                        groups[d] = gid
                        placed = True
                        break
                if not placed:
                    groups[d] = f"{term}::{d}"
            for d in self.departments:
                self.definitions[(d, term)] = groups[d]
                self._add(dept=d, cls="definition", policy_family=f"{d}-DEF",
                          policy_version=1, effective_from=0, effective_to=None,
                          claim_type=None, subject=None, modality="fact",
                          conditions=[term],
                          text=f"definition of {term.replace('_',' ')} for "
                               f"{d} {' '.join(self.rng.sample(FILLER, 5))}")

    def _pick_conditions(self, rng):
        n = rng.choices([0, 1, 2], weights=[0.30, 0.45, 0.25])[0]
        if n == 0:
            return []
        conds = rng.sample(PREDICATES, n)
        # a defined term, whose meaning differs by department, appears in
        # roughly two fifths of conditioned rules
        if rng.random() < 0.40:
            conds[0] = rng.choice(DEFINED_TERMS)
        return sorted(conds)

    def _build_policies(self):
        rng = self.rng
        # initial modality per (type, subject), biased to create genuine
        # cross owner disagreement on shared subjects
        init = {}
        for s, ts in SUBJECTS.items():
            owners = {t: CLAIM_TYPES[t]["owner"] for t in ts}
            if s in SHARED_SUBJECTS and rng.random() < 0.55:
                pair = list(ts)[:2]
                init[(pair[0], s)] = "must"
                init[(pair[1], s)] = "must_not"
                for t in list(ts)[2:]:
                    init[(t, s)] = rng.choice(["must", "should", "may"])
            else:
                for t in ts:
                    init[(t, s)] = rng.choices(
                        ["must", "must_not", "should", "should_not", "may"],
                        weights=[0.40, 0.20, 0.20, 0.10, 0.10])[0]

        for dept in self.departments:
            cadence = REVISION_CADENCE[dept]
            for fam in POLICY_FAMILIES[dept]:
                ftypes = [t for t in FAMILY_TYPES[fam] if t in self.types]
                if not ftypes:
                    continue
                pairs = [(t, s) for t in ftypes for s in SUBJECT_LIST
                         if t in SUBJECTS[s]]
                state = {}
                for (t, s) in pairs:
                    state[(t, s)] = dict(modality=init[(t, s)],
                                         conditions=self._pick_conditions(rng),
                                         present=True)
                version = 0
                q = 0
                while q < N_QUARTERS:
                    version += 1
                    nxt = min(q + cadence, N_QUARTERS)
                    if version > 1:
                        for key in pairs:
                            st = state[key]
                            r = rng.random()
                            if r < 0.32:
                                st["modality"] = rng.choice(
                                    [m for m in ["must", "must_not", "should",
                                                 "should_not", "may"]
                                     if m != st["modality"]])
                            elif r < 0.55:
                                st["conditions"] = self._pick_conditions(rng)
                            if version > 2 and rng.random() < 0.022:
                                st["present"] = not st["present"]
                    for (t, s) in pairs:
                        st = state[(t, s)]
                        if not st["present"]:
                            continue
                        ordering = []
                        pair = ORDER_LOOKUP.get((t, s))
                        if pair and rng.random() < ORDER_P:
                            ordering = [list(pair)]
                        self._add(dept=dept, cls="policy", policy_family=fam,
                                  policy_version=version, effective_from=q,
                                  effective_to=(nxt - 1 if nxt < N_QUARTERS else None),
                                  claim_type=t, subject=s,
                                  modality=st["modality"],
                                  conditions=list(st["conditions"]),
                                  ordering=ordering,
                                  text=_text(rng, t, s, st["modality"],
                                             st["conditions"]))
                    q = nxt

        # index rules effective per quarter
        for a in self.artefacts:
            if a["cls"] != "policy":
                continue
            hi = a["effective_to"] if a["effective_to"] is not None else N_QUARTERS - 1
            for q in range(a["effective_from"], hi + 1):
                self.rules[(a["dept"], q)].append(a)

    def _build_positions(self):
        """A consulted department holds its own written position on a claim
        type it does not own. Positions are retrievable and are the material a
        consulted agent draws on; they never bind, and they are not part of
        ground truth."""
        rng = self.rng
        for t in self.types:
            spec = CLAIM_TYPES[t]
            for d in spec["consulted"]:
                if d not in self.departments:
                    continue
                cadence = REVISION_CADENCE[d]
                subs = [s for s in SUBJECT_LIST if t in SUBJECTS[s]]
                for s in subs:
                    if rng.random() > 0.75:
                        continue
                    modality = rng.choices(
                        ["must", "must_not", "should", "should_not", "may"],
                        weights=[0.35, 0.25, 0.20, 0.10, 0.10])[0]
                    version, q = 0, 0
                    while q < N_QUARTERS:
                        version += 1
                        nxt = min(q + cadence, N_QUARTERS)
                        if version > 1 and rng.random() < 0.25:
                            modality = rng.choice(
                                [m for m in ["must", "must_not", "should",
                                             "should_not", "may"] if m != modality])
                        conds = self._pick_conditions(rng)
                        self._add(dept=d, cls="position", policy_family=f"{d}-POS",
                                  policy_version=version, effective_from=q,
                                  effective_to=(nxt - 1 if nxt < N_QUARTERS else None),
                                  claim_type=t, subject=s, modality=modality,
                                  conditions=conds, ordering=[],
                                  text=_text(rng, t, s, modality, conds))
                        q = nxt

    def _build_precedents(self):
        rng = self.rng
        policies = [a for a in self.artefacts if a["cls"] == "policy"]
        for _ in range(int(len(policies) * 0.9)):
            p = rng.choice(policies)
            self._add(dept=p["dept"], cls="precedent",
                      policy_family=p["policy_family"],
                      policy_version=p["policy_version"],
                      effective_from=p["effective_from"],
                      effective_to=p["effective_to"],
                      claim_type=p["claim_type"], subject=p["subject"],
                      modality=p["modality"], conditions=list(p["conditions"]),
                      cited_artefacts=[p["artefact_id"]],
                      text="case handled where " + p["text"])

    # -- ground truth -------------------------------------------------------
    def current_rules(self, dept, quarter, ctype=None):
        out = [a for a in self.rules[(dept, quarter)]
               if ctype is None or a["claim_type"] == ctype]
        return out

    def owner_rule(self, ctype, quarter):
        """The rule set the owning department has in force for a claim type."""
        from vocab import owner
        return self.current_rules(owner(ctype), quarter, ctype)

    # -- scenarios ----------------------------------------------------------
    def _build_scenarios(self, n):
        rng = self.rng
        scen = []
        shared = [s for s in SHARED_SUBJECTS
                  if all(CLAIM_TYPES[t]["owner"] in self.departments
                         for t in SUBJECTS[s])]
        for i in range(n):
            q = rng.randrange(4, N_QUARTERS)
            # seed the scenario on a shared subject so that cross owner
            # interaction is the common case rather than an injected rarity
            s0 = None
            r0 = rng.random()
            if r0 < 0.20:
                tA, sA, tB, sB = rng.choice(ORDER_CYCLES)
                seed_types = [t for t in (tA, tB) if t in self.types]
                s0 = sA
                forced = [sA, sB]
            elif shared and r0 < 0.85:
                s0 = rng.choice(shared)
                seed_types = [t for t in SUBJECTS[s0] if t in self.types]
                forced = None
            else:
                seed_types = [rng.choice(self.types)]
                forced = None
            engaged = list(dict.fromkeys(seed_types))
            extra = rng.randrange(0, 3)
            pool = [t for t in self.types if t not in engaged]
            engaged += rng.sample(pool, min(extra, len(pool)))
            engaged = sorted(set(engaged))
            pool_subj = sorted({s for t in engaged for s in SUBJECT_LIST
                                if t in SUBJECTS[s]})
            n_sub = rng.randrange(2, 6)
            raised = set(rng.sample(pool_subj, min(n_sub, len(pool_subj))))
            if s0 is not None:
                raised.add(s0)
            if forced:
                raised.update(forced)
            raised = sorted(raised)
            words = [TYPE_WORDS[t] for t in engaged]
            words += [SUBJECT_WORDS[s] for s in raised]
            words += rng.sample(FILLER, 5)
            rng.shuffle(words)
            scen.append(dict(scenario_id=f"S{i:04d}", quarter=q, types=engaged,
                             subjects=raised, situation=" ".join(words)))
        for s in scen:
            s["truth"] = self.ground_truth(s)
        return scen

    def ground_truth(self, scenario):
        """What the organisation's own rules and mandate imply, computed from
        the corpus and the lattice without any retrieval, agent or system."""
        from vocab import owner
        from lattice import default_lattice
        lat = default_lattice()
        q = scenario["quarter"]
        obligations = {}          # (ctype, subject) -> modality
        escalations = []          # (class, key, parties)
        contested = set()         # obligation keys on which the organisation
                                  # holds no reconciled position
        conds_of = {}             # (ctype, subject) -> conditions
        subject_claims = defaultdict(list)   # subject -> [(dept, ctype, modality)]
        ordering_edges = []
        term_use = defaultdict(set)          # defined term -> departments

        raised = set(scenario.get("subjects") or [])
        for t in scenario["types"]:
            rules = [r for r in self.owner_rule(t, q)
                     if not raised or r["subject"] in raised]
            expected = [s for s in raised if t in SUBJECTS[s]]
            have = {r["subject"] for r in rules}
            if t in MANDATORY_TYPES:
                for s_missing in sorted(set(expected) - have):
                    escalations.append(("C6", f"{t}|{s_missing}", [owner(t)]))
                    contested.add(f"{t}|{s_missing}")
            if not rules:
                continue
            for r in rules:
                obligations[(t, r["subject"])] = r["modality"]
                conds_of[(t, r["subject"])] = list(r["conditions"])
                subject_claims[r["subject"]].append((r["dept"], t, r["modality"]))
                for e in r["ordering"]:
                    ordering_edges.append((tuple(e), r["dept"]))
                for c in r["conditions"]:
                    if c in DEFINED_TERMS:
                        term_use[c].add(r["dept"])

        # C1 cross owner contradiction on a shared subject
        for s, entries in subject_claims.items():
            depts = {}
            for d, t, m in entries:
                depts.setdefault(d, set()).add(m)
            pairs = [(d1, m1, d2, m2)
                     for d1, ms1 in depts.items() for m1 in ms1
                     for d2, ms2 in depts.items() for m2 in ms2
                     if d1 < d2 and (m1, m2) in INCOMPATIBLE]
            for d1, m1, d2, m2 in pairs:
                win = lat.precedes(s, d1, d2)
                if win is None:
                    escalations.append(("C1", s, sorted([d1, d2])))
                    for (t, sub) in list(obligations):
                        if sub == s:
                            contested.add(f"{t}|{sub}")
                            obligations.pop((t, sub))
                else:
                    lose = d2 if win == d1 else d1
                    for (t, sub) in list(obligations):
                        if sub == s and lat.owner(t) == lose:
                            obligations.pop((t, sub))

        # C2 ordering cycle across departments
        edges = {e for e, _ in ordering_edges}
        adj = defaultdict(set)
        for a, b in edges:
            adj[a].add(b)
        if self._cyclic(adj):
            parties = sorted({d for e, d in ordering_edges})
            escalations.append(("C2", "ordering", parties))

        # C5 definitional conflict on an unmapped term
        for term, depts in term_use.items():
            ds = sorted(depts)
            for i in range(len(ds)):
                for j in range(i + 1, len(ds)):
                    if not lat.terms_equated(ds[i], ds[j], term):
                        escalations.append(("C5", term, [ds[i], ds[j]]))
                        for key, cs in conds_of.items():
                            if term in cs and owner(key[0]) in (ds[i], ds[j]):
                                contested.add(f"{key[0]}|{key[1]}")
                                obligations.pop(key, None)

        binding = {k: m for k, m in obligations.items() if m in BINDING}
        deontic = {k: m for k, m in obligations.items() if m in DEONTIC}
        return dict(obligations={f"{k[0]}|{k[1]}": m for k, m in sorted(deontic.items())},
                    binding={f"{k[0]}|{k[1]}": m for k, m in sorted(binding.items())},
                    escalations=sorted({(c, k, "+".join(p)) for c, k, p in escalations}),
                    contested=sorted(contested),
                    should_escalate=bool(escalations))

    @staticmethod
    def _cyclic(adj):
        colour = {}

        def visit(n):
            colour[n] = 1
            for m in adj.get(n, ()):
                if colour.get(m) == 1:
                    return True
                if colour.get(m) is None and visit(m):
                    return True
            colour[n] = 2
            return False

        return any(colour.get(n) is None and visit(n) for n in list(adj))

    # -- summary ------------------------------------------------------------
    def summary(self):
        cls = defaultdict(int)
        for a in self.artefacts:
            cls[a["cls"]] += 1
        esc = defaultdict(int)
        for s in self.scenarios:
            for c, _, _ in s["truth"]["escalations"]:
                esc[c] += 1
        return dict(
            n_artefacts=len(self.artefacts),
            by_class=dict(cls),
            by_dept={d: len(v) for d, v in sorted(self.by_dept.items())},
            n_scenarios=len(self.scenarios),
            mean_types_per_scenario=round(
                sum(len(s["types"]) for s in self.scenarios) / len(self.scenarios), 3),
            mean_departments_per_scenario=round(
                sum(len({CLAIM_TYPES[t]["owner"] for t in s["types"]})
                    for s in self.scenarios) / len(self.scenarios), 3),
            scenarios_requiring_escalation=sum(
                1 for s in self.scenarios if s["truth"]["should_escalate"]),
            escalation_by_class=dict(esc),
            mean_obligations=round(
                sum(len(s["truth"]["obligations"]) for s in self.scenarios)
                / len(self.scenarios), 3),
        )
