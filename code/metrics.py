"""Deterministic scoring over the closed vocabularies.

No model judge is used anywhere. Every quantity below is computed by set
comparison against ground truth derived from the corpus and the lattice.
"""

from collections import defaultdict

from vocab import owner, DEONTIC


def score_scenario(scenario, out):
    truth = scenario["truth"]
    T = truth["obligations"]
    S = out["obligations"]
    contested = set(truth["contested"])
    contested_types = {c.split("|")[0] for c in contested if c.endswith("|*")}

    correct = {k for k in S if k in T and S[k] == T[k]}
    wrong = set(S) - correct

    m = {}
    m["n_truth"] = len(T)
    m["n_emitted"] = len(S)
    m["coverage"] = len(correct) / len(T) if T else None
    m["spurious_rate"] = len(wrong) / len(S) if S else 0.0

    # attribution: an emitted obligation is correctly attributed when it is
    # ascribed to the department that owns its claim type
    attr_ok = sum(1 for k in S
                  if out["attribution"].get(k) == owner(k.split("|")[0]))
    m["attribution_rate"] = attr_ok / len(S) if S else None
    m["jurisdiction_violation_rate"] = (
        sum(1 for k in S if out["attribution"].get(k) not in
            (None, owner(k.split("|")[0]))) / len(S)) if S else 0.0
    m["unattributed_rate"] = (
        sum(1 for k in S if out["attribution"].get(k) is None) / len(S)) if S else 0.0

    # citation validity against the served commitment
    served_ids = defaultdict(set)
    for d, arts in out.get("served", {}).items():
        for a in arts:
            served_ids[d].add(a["artefact_id"])
    all_served = set().union(*served_ids.values()) if served_ids else set()
    valid, stale = 0, 0
    for k, cits in out.get("support", {}).items():
        if cits and set(cits).issubset(all_served):
            valid += 1
    m["citation_validity"] = valid / len(S) if S else None

    # staleness of the emitted set, measured on the claim that actually
    # produced each emitted obligation rather than on any claim about it
    flags = out.get("stale_flags", {})
    m["stale_obligation_rate"] = (
        sum(1 for k in S if flags.get(k)) / len(S)) if S else 0.0

    # escalation
    m["should_escalate"] = truth["should_escalate"]
    m["did_escalate"] = bool(out["escalated"])
    silent = 0
    if truth["should_escalate"] and not out["escalated"]:
        for k in S:
            if k in contested or k.split("|")[0] in contested_types:
                silent = 1
                break
    m["silent_wrong_answer"] = silent
    # an answer asserted on a contested domain even when the system escalated
    # elsewhere is still an assertion the organisation has not made
    m["contested_assertions"] = sum(
        1 for k in S if k in contested or k.split("|")[0] in contested_types)
    m["answered"] = 1 if S and not out["escalated"] else 0
    # domain level escalation, comparing the conflicts named rather than the
    # scenario level decision to escalate at all
    tk = {(c, k) for c, k, _ in truth["escalations"]}
    pk = {(c, k) for c, k, _ in out["escalations"]}
    m["esc_tp"] = len(tk & pk)
    m["esc_fp"] = len(pk - tk)
    m["esc_fn"] = len(tk - pk)
    m["esc_fp_by_class"] = {}
    for c, k in (pk - tk):
        m["esc_fp_by_class"][c] = m["esc_fp_by_class"].get(c, 0) + 1
    return m


def aggregate(rows):
    keys = ["coverage", "spurious_rate", "attribution_rate",
            "jurisdiction_violation_rate", "unattributed_rate",
            "citation_validity", "stale_obligation_rate", "n_emitted", "n_truth",
            "contested_assertions"]
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = round(sum(vals) / len(vals), 4) if vals else None
    esc_truth = [r["should_escalate"] for r in rows]
    esc_pred = [r["did_escalate"] for r in rows]
    tp = sum(1 for a, b in zip(esc_truth, esc_pred) if a and b)
    fp = sum(1 for a, b in zip(esc_truth, esc_pred) if not a and b)
    fn = sum(1 for a, b in zip(esc_truth, esc_pred) if a and not b)
    out["escalation_precision"] = round(tp / (tp + fp), 4) if tp + fp else None
    out["escalation_recall"] = round(tp / (tp + fn), 4) if tp + fn else None
    need = [r for r in rows if r["should_escalate"]]
    out["silent_wrong_answer_rate"] = round(
        sum(r["silent_wrong_answer"] for r in need) / len(need), 4) if need else None
    out["answered_rate"] = round(sum(r["answered"] for r in rows) / len(rows), 4)
    tp = sum(r["esc_tp"] for r in rows)
    fp = sum(r["esc_fp"] for r in rows)
    fn = sum(r["esc_fn"] for r in rows)
    out["domain_escalation_precision"] = round(tp / (tp + fp), 4) if tp + fp else None
    out["domain_escalation_recall"] = round(tp / (tp + fn), 4) if tp + fn else None
    fpc = {}
    for r in rows:
        for c, v in r["esc_fp_by_class"].items():
            fpc[c] = fpc.get(c, 0) + v
    out["false_escalations_by_class"] = dict(sorted(fpc.items()))
    out["n"] = len(rows)
    return out


def detection_scores(scenario, out, claims):
    """Conflict detection against ground truth. C1, C2, C5 and C6 are
    organisational and come from the corpus. C3 and C4 are agent induced and
    come from the agent log."""
    truth_by_class = defaultdict(set)
    for c, key, _ in scenario["truth"]["escalations"]:
        truth_by_class[c].add(key)
    truth_by_class["C3"] = {f"{c['dept']}:{c['ctype']}" for c in claims
                            if c.get("overreach")}
    truth_by_class["C4"] = {f"{c['ctype']}|{c['subject']}" for c in claims
                            if c.get("used_stale")}
    det = {k: set(v) for k, v in out.get("detected", {}).items()}
    res = {}
    for cls in ["C1", "C2", "C3", "C4", "C5", "C6"]:
        t, d = truth_by_class.get(cls, set()), det.get(cls, set())
        res[cls] = dict(tp=len(t & d), fp=len(d - t), fn=len(t - d))
    return res


def merge_detection(rows):
    out = {}
    for cls in ["C1", "C2", "C3", "C4", "C5", "C6"]:
        tp = sum(r[cls]["tp"] for r in rows)
        fp = sum(r[cls]["fp"] for r in rows)
        fn = sum(r[cls]["fn"] for r in rows)
        out[cls] = dict(
            tp=tp, fp=fp, fn=fn,
            recall=round(tp / (tp + fn), 4) if tp + fn else None,
            precision=round(tp / (tp + fp), 4) if tp + fp else None,
            support=tp + fn)
    return out
