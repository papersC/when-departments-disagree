"""Two baseline arms added after review.

B2F  a pooled index with department labels that also has the affordances any
     enterprise index has and that the proposed framework was previously alone
     in using: an effective-window currency filter applied at retrieval, and an
     exact metadata lookup for a raised pair the ranked list did not surface.
     It has no lattice, so no owner, no precedence and no escalation state.
     Its purpose is to separate the value of those affordances from the value
     of the registered mandate.

B4A  the referee of B4 given an abstention state. Where two departments assert
     incompatible modalities on one subject, the referee declines that subject
     instead of selecting a winner, which is the abstention mechanism the
     selective-prediction literature describes. Its purpose is to compare the
     escalation of the proposed framework against a system that can refuse,
     rather than against systems that structurally cannot.
"""

from collections import defaultdict

from vocab import DEONTIC, SUBJECTS, SUBJECT_LIST, INCOMPATIBLE
from agents import route
from ledger import MerkleTree, leaf_hash, signable
from retrieval import type_focus


def b2f(runner, scenario, fv, rng):
    plan = route(runner.lat, scenario["types"])
    k = runner.k * max(1, len(plan))
    q = scenario["quarter"]
    hits = runner.indexes.pool(type_focus(scenario["situation"], scenario["types"]), k)
    served = [a for a, _ in hits if runner.ledger.verify_artefact(a)]
    # affordance 1: an effective-window filter applied at retrieval
    def current(a):
        hi = a["effective_to"]
        return a["effective_from"] <= q and (hi is None or q <= hi)
    served = [a for a in served if current(a)]
    rank = {a["artefact_id"]: i for i, (a, _) in enumerate(hits)}
    root = MerkleTree([leaf_hash(signable(a)) for a in served]).root
    best = {}
    for a in served:
        if a["cls"] not in ("policy", "position") or a["claim_type"] not in scenario["types"]:
            continue
        key = (a["claim_type"], a["subject"])
        if key not in best or rank[a["artefact_id"]] < rank[best[key]["artefact_id"]]:
            best[key] = a
    obligations, attribution, support, stale_flags, claims = {}, {}, {}, {}, []
    for (ctype, subject), src in sorted(best.items()):
        if rng.random() < fv["omit"]:
            continue
        modality = src["modality"]
        if modality in DEONTIC and rng.random() < fv["modality"]:
            modality = rng.choice([m for m in ["must", "must_not", "should",
                                               "should_not"] if m != modality])
        c = dict(claim_id=f"F-{ctype}-{subject}", dept=src["dept"], ctype=ctype,
                 subject=subject, modality=modality, conditions=list(src["conditions"]),
                 ordering=[list(e) for e in src["ordering"]],
                 policy_version=src["policy_version"], quality=src["quality"],
                 effective_from=src["effective_from"], effective_to=src["effective_to"],
                 citations=[src["artefact_id"]], served_root=root,
                 confidence=round(rng.uniform(0.55, 0.99), 3), verbosity=len(src["text"]),
                 spurious=False, overreach=False, used_stale=False,
                 fabricated_citation=False)
        claims.append(c)
        if modality in DEONTIC:
            key = f"{ctype}|{subject}"
            obligations[key] = modality
            attribution[key] = src["dept"]
            support[key] = [src["artefact_id"]]
            stale_flags[key] = False
    n_sp = sum(1 for _ in range(max(1, len(claims))) if rng.random() < fv["spurious"])
    for _ in range(n_sp):
        t = rng.choice(list(scenario["types"]))
        subs = [s for s in SUBJECT_LIST if t in SUBJECTS[s]]
        if not subs or not served:
            continue
        src = served[rng.randrange(len(served))]
        sub = rng.choice(subs)
        m = rng.choice(["must", "must_not", "should"])
        claims.append(dict(claim_id=f"F-sp-{rng.randrange(1 << 30):08x}", dept=src["dept"],
                           ctype=t, subject=sub, modality=m, conditions=[], ordering=[],
                           policy_version=src["policy_version"], quality=src["quality"],
                           effective_from=src["effective_from"],
                           effective_to=src["effective_to"],
                           citations=[src["artefact_id"]], served_root=root,
                           confidence=round(rng.uniform(0.55, 0.99), 3),
                           verbosity=len(src["text"]), spurious=True, overreach=False,
                           used_stale=False, fabricated_citation=False))
        key = f"{t}|{sub}"
        if key not in obligations:
            obligations[key] = m
            attribution[key] = src["dept"]
            support[key] = [src["artefact_id"]]
            stale_flags[key] = False
    # affordance 2: an exact metadata lookup over the whole index, no owner
    for t in scenario["types"]:
        for sub in sorted(x for x in scenario.get("subjects", []) if t in SUBJECTS[x]):
            key = f"{t}|{sub}"
            if key in obligations:
                continue
            for d, ag in runner.agents.items():
                art = ag.probe(t, sub, q)
                if art is None:
                    continue
                obligations[key] = art["modality"]
                attribution[key] = art["dept"]
                support[key] = [art["artefact_id"]]
                stale_flags[key] = False
                break
    return dict(obligations=obligations, attribution=attribution, support=support,
                stale_flags=stale_flags, escalations=[], escalated=False,
                served={"pooled": served}, claims=claims, detected={},
                served_count=len(served))


def b4a(runner, scenario, fv, rng):
    _, served_by, claims = runner._departmental(scenario, fv, rng, False, True)
    by_subject = defaultdict(list)
    for c in claims:
        if c["modality"] in DEONTIC:
            by_subject[c["subject"]].append(c)
    obligations, attribution, support, stale_flags = {}, {}, {}, {}
    escalations = []
    for s, cs in sorted(by_subject.items()):
        mods = {c["modality"] for c in cs}
        depts = {c["dept"] for c in cs}
        conflict = any((a, b) in INCOMPATIBLE for a in mods for b in mods)
        if conflict and len(depts) > 1:
            # the referee declines rather than selecting a winner
            escalations.append(("C1", s, "+".join(sorted(d for d in depts if d))))
            continue
        if conflict:
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
                stale_flags=stale_flags, escalations=sorted(set(escalations)),
                escalated=bool(escalations), served=served_by, claims=claims,
                detected={}, served_count=sum(len(v) for v in served_by.values()))
