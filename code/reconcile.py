"""The reconciliation engine.

Rules R0 to R7 are applied in a fixed order. Determinism is what makes a
settlement replayable by an auditor holding only the settlement record and the
anchored partitions, and it is what keeps the resolution of an organisational
mandate out of a model's discretion. Any rule from R3 onwards may place a claim
domain in the escalation state; escalation of one domain does not prevent
settlement of the others.

  R0  admissibility          citations must lie in the committed served set
  R1  currency               claims resting only on superseded material go
  R2  jurisdiction           only the owner's deontic claims bind
  R3  precedence             cross owner contradictions settle or escalate
  R4  evidence weight        contradictions inside one department settle
  R5  completeness probe     exact existence query, repair or record a gap
  R6  ordering synthesis     a cycle in the constraints escalates
  R7  definitional           an unmapped shared term escalates

The completeness probe sits at R5 rather than at the end because a repaired
claim must still be examined for ordering and definitional conflict.
"""

from collections import defaultdict

from vocab import (DEONTIC, BINDING, INCOMPATIBLE, DEFINED_TERMS,
                   MANDATORY_TYPES, SUBJECTS)


class Reconciler:
    def __init__(self, lattice, ledger, rules_enabled=None):
        self.lat = lattice
        self.ledger = ledger
        self.on = dict(R0=True, R1=True, R2=True, R3=True, R4=True,
                       R5=True, R6=True, R7=True, probe=True, escalate=True,
                       # review variants; both default to the order as first
                       # implemented so that the released results are unchanged
                       c5_subject_scoped=False, c5_prepass=False)
        if rules_enabled:
            self.on.update(rules_enabled)

    def reconcile(self, scenario, served_by_dept, claims, artefact_by_id,
                  probe=None, fv=None, rng=None):
        q = scenario["quarter"]
        trace, escalations = [], []
        dropped = defaultdict(int)
        detected = defaultdict(list)

        # ---- R0 admissibility --------------------------------------------
        live = []
        for c in claims:
            if self.on["R0"]:
                served_ids = {a["artefact_id"] for a in served_by_dept.get(c["dept"], [])}
                if not c["citations"] or not set(c["citations"]).issubset(served_ids):
                    dropped["R0_unserved_citation"] += 1
                    continue
                if not all(self.ledger.verify_artefact(artefact_by_id[i])
                           for i in c["citations"] if i in artefact_by_id):
                    dropped["R0_failed_inclusion"] += 1
                    continue
            live.append(dict(c))
        trace.append(("R0", len(live)))

        # ---- R1 currency --------------------------------------------------
        cur = []
        for c in live:
            hi = c["effective_to"]
            current = c["effective_from"] <= q and (hi is None or q <= hi)
            c["stale"] = not current
            if not current:
                detected["C4"].append(f"{c['ctype']}|{c['subject']}")
                if self.on["R1"]:
                    dropped["R1_superseded"] += 1
                    continue
            cur.append(c)
        trace.append(("R1", len(cur)))

        # ---- R2 jurisdiction projection -----------------------------------
        binding = []
        for c in cur:
            is_owner = self.lat.owner(c["ctype"]) == c["dept"]
            if c["modality"] in DEONTIC and not is_owner:
                detected["C3"].append(f"{c['dept']}:{c['ctype']}")
                if self.on["R2"]:
                    c["status"] = "advisory"
                    continue
            if c["modality"] in DEONTIC:
                c["status"] = "binding"
                binding.append(c)
            else:
                c["status"] = "context"
        trace.append(("R2", len(binding)))

        # ---- R3 precedence between departments ----------------------------
        def precedence_pass(bind, record=True):
            by_subject = defaultdict(list)
            for c in bind:
                by_subject[c["subject"]].append(c)
            removed = set()
            for s, cs in sorted(by_subject.items()):
                depts = sorted({c["dept"] for c in cs})
                for i in range(len(depts)):
                    for j in range(i + 1, len(depts)):
                        d1, d2 = depts[i], depts[j]
                        m1 = {c["modality"] for c in cs if c["dept"] == d1}
                        m2 = {c["modality"] for c in cs if c["dept"] == d2}
                        if not any((a, b) in INCOMPATIBLE for a in m1 for b in m2):
                            continue
                        if record:
                            detected["C1"].append(s)
                        win = self.lat.precedes(s, d1, d2) if self.on["R3"] else None
                        if win is None:
                            if self.on["escalate"]:
                                escalations.append(("C1", s, "+".join(sorted([d1, d2]))))
                                for c in cs:
                                    removed.add(c["claim_id"])
                        else:
                            lose = d2 if win == d1 else d1
                            for c in cs:
                                if c["dept"] == lose:
                                    removed.add(c["claim_id"])
            return [c for c in bind if c["claim_id"] not in removed]

        if self.on["c5_prepass"]:
            # the unmapped term test is evaluated before the contradiction
            # test, so a definitional conflict on a pair that precedence would
            # resolve is still recorded
            binding = self._definitional(binding, detected, escalations)
        binding = precedence_pass(binding)
        trace.append(("R3", len(binding)))

        # ---- R4 evidence weight inside one department ---------------------
        removed = set()
        by_ds = defaultdict(list)
        for c in binding:
            by_ds[(c["dept"], c["subject"])].append(c)
        for key, cs in sorted(by_ds.items()):
            mods = {c["modality"] for c in cs}
            if not any((a, b) in INCOMPATIBLE for a in mods for b in mods):
                continue
            if not self.on["R4"]:
                continue
            ranked = sorted(cs, key=lambda c: (-c["policy_version"], -c["quality"],
                                               -len(c["citations"]), c["claim_id"]))
            best = ranked[0]
            tie = [c for c in ranked[1:]
                   if (c["policy_version"], c["quality"], len(c["citations"]))
                   == (best["policy_version"], best["quality"], len(best["citations"]))
                   and (c["modality"], best["modality"]) in INCOMPATIBLE]
            if tie and self.on["escalate"]:
                escalations.append(("C1", key[1], key[0]))
                for c in cs:
                    removed.add(c["claim_id"])
            else:
                for c in ranked[1:]:
                    removed.add(c["claim_id"])
        binding = [c for c in binding if c["claim_id"] not in removed]
        trace.append(("R4", len(binding)))

        # ---- R5 completeness probe and repair ------------------------------
        probes, repaired, gaps = 0, 0, []
        settled = {(c["ctype"], c["subject"]) for c in binding}
        raised = set(scenario.get("subjects") or [])
        for t in scenario["types"]:
            for s in sorted(x for x in raised if t in SUBJECTS[x]):
                if (t, s) in settled:
                    continue
                art = None
                if probe is not None and self.on.get("probe", True):
                    probes += 1
                    art = probe(self.lat.owner(t), t, s, q)
                if art is None:
                    if t in MANDATORY_TYPES:
                        gaps.append((t, s))
                    continue
                repaired += 1
                modality = art["modality"]
                # the probe locates the rule; the owning department still
                # drafts the claim, so drafting failure applies to it as well
                if (fv and rng and modality in DEONTIC
                        and rng.random() < fv.get("modality", 0.0)):
                    modality = rng.choice([m for m in ["must", "must_not", "should",
                                                       "should_not"] if m != modality])
                # the probe result joins the served commitment for that
                # department before the repaired claim is admitted
                served_by_dept.setdefault(art["dept"], []).append(art)
                if modality in DEONTIC:
                    binding.append(dict(
                        claim_id=f"probe-{t}-{s}", dept=art["dept"], ctype=t,
                        subject=s, modality=modality,
                        conditions=list(art["conditions"]),
                        ordering=[list(e) for e in art["ordering"]],
                        policy_version=art["policy_version"], quality=art["quality"],
                        effective_from=art["effective_from"],
                        effective_to=art["effective_to"],
                        citations=[art["artefact_id"]], confidence=1.0, verbosity=0,
                        status="binding", stale=False, used_stale=False,
                        overreach=False, spurious=False, repaired=True))
        if repaired:
            binding = precedence_pass(binding)
        trace.append(("R5", len(binding)))

        # ---- R6 ordering synthesis ----------------------------------------
        adj, parties = defaultdict(set), defaultdict(set)
        for c in binding:
            for a, b in c["ordering"]:
                adj[a].add(b)
                parties[(a, b)].add(c["dept"])
        if self.on["R6"] and _cyclic(adj):
            detected["C2"].append("ordering")
            if self.on["escalate"]:
                ps = sorted({d for v in parties.values() for d in v})
                escalations.append(("C2", "ordering", "+".join(ps)))
        trace.append(("R6", len(binding)))

        # ---- R7 definitional normalisation --------------------------------
        if not self.on["c5_prepass"]:
            binding = self._definitional(binding, detected, escalations)
        trace.append(("R7", len(binding)))

        # ---- residual gaps recorded at R5 escalate here --------------------
        for t, s in gaps:
            detected["C6"].append(f"{t}|{s}")
            if self.on["R5"] and self.on["escalate"]:
                escalations.append(("C6", f"{t}|{s}", self.lat.owner(t)))

        obligations, attribution, support, stale_flags = {}, {}, {}, {}
        for c in sorted(binding, key=lambda c: (c["ctype"], c["subject"], c["claim_id"])):
            key = f"{c['ctype']}|{c['subject']}"
            obligations[key] = c["modality"]
            attribution[key] = c["dept"]
            support[key] = c["citations"]
            stale_flags[key] = bool(c.get("stale"))
        return dict(obligations=obligations, attribution=attribution,
                    support=support, stale_flags=stale_flags,
                    probes=probes, repaired=repaired,
                    escalations=sorted(set(escalations)),
                    detected={k: sorted(set(v)) for k, v in detected.items()},
                    dropped=dict(dropped), rule_trace=trace,
                    escalated=bool(escalations))


    def _definitional(self, binding, detected, escalations):
        """The definitional test.

        Scope is a flag. As first implemented the test fires when two
        departments carry the same defined term anywhere among their surviving
        binding claims; under c5_subject_scoped it must be the same subject,
        which is the scope C1 already uses.
        """
        term_depts = defaultdict(set)
        for c in binding:
            for tm in c["conditions"]:
                if tm in DEFINED_TERMS:
                    key = (tm, c["subject"]) if self.on["c5_subject_scoped"] else (tm, None)
                    term_depts[key].add(c["dept"])
        removed = set()
        for (term, subj), ds in sorted(term_depts.items(), key=lambda x: (x[0][0], x[0][1] or "")):
            ds = sorted(ds)
            for i in range(len(ds)):
                for j in range(i + 1, len(ds)):
                    if self.lat.terms_equated(ds[i], ds[j], term):
                        continue
                    detected["C5"].append(term)
                    if self.on["R7"] and self.on["escalate"]:
                        escalations.append(("C5", term, "+".join([ds[i], ds[j]])))
                        for c in binding:
                            if (term in c["conditions"] and c["dept"] in (ds[i], ds[j])
                                    and (subj is None or c["subject"] == subj)):
                                removed.add(c["claim_id"])
        return [c for c in binding if c["claim_id"] not in removed]


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
