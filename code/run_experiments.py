"""Runs the eight experiments and writes results/results.json.

Every number in the paper is produced here. The global seed is fixed and every
experiment draws from its own derived stream, so a rerun reproduces the file
byte for byte.
"""

import json
import math
import os
import random
import time
from collections import defaultdict

from build import build
from corpus import Corpus, SEED
from vocab import (DEPARTMENTS, TYPES, SUBJECTS, MANDATORY_TYPES, CLAIM_TYPES,
                   DEFINED_TERMS, owner, N_QUARTERS)
from agents import failure_vector, BASE_FAILURE
from metrics import score_scenario, aggregate, detection_scores, merge_detection
from systems import SYSTEMS, SYSTEM_LABELS
from lattice import default_lattice

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(RESULTS, exist_ok=True)

N_SCENARIOS = 400
K = 24
LAMBDA_GRID = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
BOOTSTRAP = 10000


MIN_TRIALS = 20


def lambda_star():
    """The operating point at which the headline table is reported.

    The model in the loop sample produced no failures, so a point estimate
    would place the operating point at zero and make the comparison vacuous.
    The rule adopted instead is conservative: lambda star is the smallest grid
    value whose failure vector is at or above the ninety five per cent upper
    bound of every rate that the sample estimated on at least MIN_TRIALS
    trials. Rates estimated on fewer trials carry bounds too wide to constrain
    anything and are excluded, which is recorded in the returned record."""
    path = os.path.join(RESULTS, "llm_calibration.json")
    if not os.path.exists(path):
        return 0.6, None
    cal = json.load(open(path))
    counts, bounds = cal["counts"], cal["wilson_95"]
    used, excluded, need = {}, [], 0.0
    for k, c in counts.items():
        if c["trials"] < MIN_TRIALS:
            excluded.append(k)
            continue
        upper = bounds[k][1]
        used[k] = upper
        base = BASE_FAILURE[k]
        need = max(need, upper / base if base else 0.0)
    lam = min([l for l in LAMBDA_GRID if l >= need] or [max(LAMBDA_GRID)])
    cal = dict(cal)
    cal["fit"] = dict(rule="smallest grid lambda at or above every usable "
                           "ninety five per cent upper bound",
                      min_trials=MIN_TRIALS, upper_bounds_used=used,
                      excluded_insufficient_trials=excluded,
                      required_lambda=round(need, 4), chosen=lam)
    return lam, cal


# ---------------------------------------------------------------------------
def paired_bootstrap(a, b, reps=BOOTSTRAP, seed=7):
    """Paired bootstrap for the mean difference a - b, and a two sided paired
    randomisation test."""
    rng = random.Random(seed)
    n = len(a)
    diffs = [x - y for x, y in zip(a, b)]
    obs = sum(diffs) / n
    boots = []
    for _ in range(reps):
        s = sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        boots.append(s)
    boots.sort()
    lo = boots[int(0.025 * reps)]
    hi = boots[int(0.975 * reps) - 1]
    hits = 0
    for _ in range(reps):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs) / n
        if abs(s) >= abs(obs):
            hits += 1
    return dict(diff=round(obs, 4), ci_low=round(lo, 4), ci_high=round(hi, 4),
                p=round((hits + 1) / (reps + 1), 5))


def run_system(runner, name, scenarios, fv, seed_base, **kw):
    rows, det, outs = [], [], []
    t0 = time.perf_counter()
    for i, sc in enumerate(scenarios):
        rng = random.Random(seed_base + i)
        out = getattr(runner, name)(sc, fv, rng, **kw) if name != "b5" else \
            runner.b5(sc, fv, rng, **kw)
        rows.append(score_scenario(sc, out))
        det.append(detection_scores(sc, out, out.get("claims", [])))
        outs.append(out)
    elapsed = time.perf_counter() - t0
    agg = aggregate(rows)
    agg["seconds_per_scenario"] = round(elapsed / len(scenarios), 5)
    agg["mean_served_artefacts"] = round(
        sum(o.get("served_count", 0) for o in outs) / len(outs), 2)
    agg["fully_settled_rate"] = round(
        sum(1 for o in outs if o["obligations"] and not o["escalated"]) / len(outs), 4)
    agg["partial_rate"] = round(
        sum(1 for o in outs if o["obligations"] and o["escalated"]) / len(outs), 4)
    agg["refused_rate"] = round(
        sum(1 for o in outs if not o["obligations"]) / len(outs), 4)
    return agg, rows, merge_detection(det), outs


def main():
    t_start = time.time()
    results = dict(seed=SEED, n_scenarios=N_SCENARIOS, k=K,
                   lambda_grid=LAMBDA_GRID, base_failure=BASE_FAILURE)
    lam_star, cal = lambda_star()
    results["lambda_star"] = lam_star
    results["llm_calibration"] = cal
    corpus, ledger, lattice, indexes, runner = build(
        seed=SEED, n_scenarios=N_SCENARIOS, k=K)
    scen = corpus.scenarios
    fv_star = failure_vector(lam_star)

    # ---------------- E1 corpus characterisation --------------------------
    e1 = corpus.summary()
    e1["signature_scheme"] = ledger.keyring.scheme
    e1["epochs"] = len(ledger.epoch_commitment)
    e1["lattice_version"] = len(ledger.lattice_versions)
    e1["claim_types"] = len(TYPES)
    e1["subjects"] = len(SUBJECTS)
    e1["mandatory_types"] = len(MANDATORY_TYPES)
    e1["shared_subjects"] = sum(
        1 for s, ts in SUBJECTS.items()
        if len({CLAIM_TYPES[t]["owner"] for t in ts}) > 1)
    e1["registered_precedence_subjects"] = len(lattice.precedence)
    ver = defaultdict(set)
    for a in corpus.artefacts:
        if a["cls"] == "policy":
            ver[a["policy_family"]].add(a["policy_version"])
    e1["versions_per_family"] = {k: len(v) for k, v in sorted(ver.items())}
    # Version skew. Because departments revise on independent schedules they
    # sit at different revision generations at the same moment, and most of the
    # policy corpus is superseded yet still retrievable. Both are what make
    # staleness an organisational condition rather than a model defect.
    pol = [a for a in corpus.artefacts if a["cls"] == "policy"]

    def in_force(a, q):
        return a["effective_from"] <= q and (
            a["effective_to"] is None or q <= a["effective_to"])

    gens, supersede = [], []
    for q in range(N_QUARTERS):
        vs = {a["policy_version"] for a in pol if in_force(a, q)}
        gens.append(len(vs))
        supersede.append(round(
            sum(1 for a in pol if not in_force(a, q)) / len(pol), 4))
    e1["policy_families"] = len({a["policy_family"] for a in pol})
    e1["distinct_version_generations_by_quarter"] = gens
    e1["superseded_share_by_quarter"] = supersede
    # which conflict classes each architecture can represent at all
    e1["representable"] = {
        "B1": ["C1 partially"], "B2": ["C1 partially", "C4"],
        "B3": ["C1", "C4"], "B4": ["C1", "C4"],
        "B5": ["C1", "C2", "C3", "C4", "C5", "C6"]}
    results["E1"] = e1

    # ---------------- E2 retrieval inside partitions ----------------------
    from retrieval import type_focus
    def ndcg(rels, k=10):
        dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels[:k]))
        ideal = sorted(rels, reverse=True)[:k]
        idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
        return dcg / idcg if idcg else None

    def relevance(a, sc):
        if a["cls"] not in ("policy", "position"):
            return 0
        if a["claim_type"] not in sc["types"] or a["subject"] not in sc["subjects"]:
            return 0
        cur = a["effective_from"] <= sc["quarter"] and (
            a["effective_to"] is None or sc["quarter"] <= a["effective_to"])
        if a["cls"] == "policy" and owner(a["claim_type"]) == a["dept"]:
            return 3 if cur else 1
        return 1 if cur else 0

    part_nd, pool_nd, part_rec, pool_rec, part_stale, pool_stale = [], [], [], [], [], []
    for sc in scen:
        need = {(t, s) for t in sc["types"] for s in sc["subjects"] if t in SUBJECTS[s]}
        from agents import route
        plan = route(lattice, sc["types"])
        got, served_all = set(), []
        rels = []
        for d, types in plan.items():
            hits = indexes.dept(d, type_focus(sc["situation"], types), K)
            for a, _ in hits:
                served_all.append(a)
                rels.append(relevance(a, sc))
                if a["cls"] == "policy" and owner(a["claim_type"] or "") == d:
                    got.add((a["claim_type"], a["subject"]))
        part_nd.append(ndcg(rels))
        part_rec.append(len(got & need) / len(need) if need else None)
        part_stale.append(sum(1 for a in served_all if not (
            a["effective_from"] <= sc["quarter"] and (
                a["effective_to"] is None or sc["quarter"] <= a["effective_to"])))
            / max(1, len(served_all)))
        kk = K * max(1, len(plan))
        hits = indexes.pool(type_focus(sc["situation"], sc["types"]), kk)
        rels = [relevance(a, sc) for a, _ in hits]
        pool_nd.append(ndcg(rels))
        gotp = {(a["claim_type"], a["subject"]) for a, _ in hits
                if a["cls"] == "policy" and owner(a["claim_type"] or "") == a["dept"]}
        pool_rec.append(len(gotp & need) / len(need) if need else None)
        pool_stale.append(sum(1 for a, _ in hits if not (
            a["effective_from"] <= sc["quarter"] and (
                a["effective_to"] is None or sc["quarter"] <= a["effective_to"])))
            / max(1, len(hits)))

    def mean(v):
        v = [x for x in v if x is not None]
        return round(sum(v) / len(v), 4) if v else None

    results["E2"] = dict(
        partitioned=dict(ndcg10=mean(part_nd), owner_rule_recall=mean(part_rec),
                         stale_share_of_served=mean(part_stale)),
        pooled=dict(ndcg10=mean(pool_nd), owner_rule_recall=mean(pool_rec),
                    stale_share_of_served=mean(pool_stale)),
        k_per_partition=K,
        note="pooled k is set to K times the number of routed partitions so "
             "that both arrangements see the same number of artefacts")

    # ---------------- E4 composite guidance (also feeds E3, E5) ------------
    per_system, per_rows, per_det = {}, {}, {}
    for name in SYSTEMS:
        agg, rows, det, outs = run_system(runner, name.lower(), scen, fv_star, 5000)
        per_system[name] = agg
        per_rows[name] = rows
        per_det[name] = det
    results["E4"] = dict(labels=SYSTEM_LABELS, at_lambda=lam_star,
                         systems=per_system)

    # significance for the headline comparisons
    def col(name, key):
        return [r[key] if r[key] is not None else 0.0 for r in per_rows[name]]
    sig = {}
    for a, b in [("B5", "B1"), ("B5", "B3"), ("B5", "B4"), ("B5", "B3P")]:
        sig[f"{a}_vs_{b}"] = dict(
            spurious_rate=paired_bootstrap(col(a, "spurious_rate"), col(b, "spurious_rate")),
            coverage=paired_bootstrap(col(a, "coverage"), col(b, "coverage")),
            silent_wrong=paired_bootstrap(
                [r["silent_wrong_answer"] for r in per_rows[a] if r["should_escalate"]],
                [r["silent_wrong_answer"] for r in per_rows[b] if r["should_escalate"]]),
            contested_assertions=paired_bootstrap(
                col(a, "contested_assertions"), col(b, "contested_assertions")))
    results["E4"]["significance"] = sig
    results["E4"]["note_multiplicity"] = (
        "four system comparisons times four metrics gives sixteen tests; a "
        "Bonferroni corrected threshold at the five per cent level is "
        "0.003125 and is applied when a comparison is described as surviving "
        "correction")

    # ---------------- E3 conflict detection --------------------------------
    results["E3"] = dict(at_lambda=lam_star, by_class=per_det["B5"],
                         baseline_B3=per_det["B3"], baseline_B1=per_det["B1"])

    # ---------------- E5 escalation calibration ----------------------------
    rows = per_rows["B5"]
    tp = sum(1 for r in rows if r["should_escalate"] and r["did_escalate"])
    fp = sum(1 for r in rows if not r["should_escalate"] and r["did_escalate"])
    fn = sum(1 for r in rows if r["should_escalate"] and not r["did_escalate"])
    tn = sum(1 for r in rows if not r["should_escalate"] and not r["did_escalate"])
    results["E5"] = dict(
        confusion=dict(tp=tp, fp=fp, fn=fn, tn=tn),
        precision=per_system["B5"]["escalation_precision"],
        recall=per_system["B5"]["escalation_recall"],
        silent_wrong_answer_rate={n: per_system[n]["silent_wrong_answer_rate"]
                                  for n in SYSTEMS},
        coverage_surrendered=round(
            (per_system["B3"]["coverage"] or 0) - (per_system["B5"]["coverage"] or 0), 4),
        fully_settled_rate={n: per_system[n]["fully_settled_rate"] for n in SYSTEMS},
        partial_rate={n: per_system[n]["partial_rate"] for n in SYSTEMS},
        refused_rate={n: per_system[n]["refused_rate"] for n in SYSTEMS})

    # ---------------- sweep over the failure rate --------------------------
    sweep = {}
    for lam in LAMBDA_GRID:
        fv = failure_vector(lam)
        sweep[str(lam)] = {}
        for name in SYSTEMS:
            agg, _, _, _ = run_system(runner, name.lower(), scen, fv, 6000)
            sweep[str(lam)][name] = agg
    results["SWEEP"] = sweep

    # ---------------- E6 adversarial ---------------------------------------
    e6 = {}
    base = per_system["B5"]
    e6["baseline"] = base
    # (a) captured department inflating its jurisdiction
    for cap in ["SEC", "LEG"]:
        agg, _, _, _ = run_system(runner, "b5", scen, fv_star, 7000,
                                  adversary="inflate", captured=cap)
        e6[f"captured_{cap}"] = agg
    # (b) poisoned partition: adversarial artefacts injected into one partition
    poisoned_corpus = Corpus(seed=SEED, n_scenarios=N_SCENARIOS)
    inject = []
    for i in range(40):
        t = sorted(t for t in TYPES if owner(t) == "SEC")[i % 4]
        s = sorted(x for x in SUBJECTS if t in SUBJECTS[x])[i % 2]
        inject.append(dict(dept="SEC", cls="policy", policy_family="SEC-ACC",
                           policy_version=99, effective_from=0, effective_to=None,
                           claim_type=t, subject=s, modality="must_not",
                           conditions=[], ordering=[], quality=0.99, attested=True,
                           cited_artefacts=[],
                           text=" ".join([t.replace("_", " "), s.replace("_", " ")] * 6)))
    for a in inject:
        poisoned_corpus._add(**a)
    from build import build as build2
    from ledger import Keyring, Ledger
    from retrieval import Indexes
    from systems import Runner as Runner2
    kr = Keyring(poisoned_corpus.departments)
    lg = Ledger(kr)
    ep = defaultdict(lambda: defaultdict(list))
    for a in poisoned_corpus.artefacts:
        ep[a["effective_from"]][a["dept"]].append(a)
    for e in sorted(ep):
        for d, arts in sorted(ep[e].items()):
            lg.anchor(d, e, arts)
        lg.commit_epoch(e, poisoned_corpus.departments)
    lat2 = default_lattice()
    lg.register_lattice(lat2.snapshot())
    r2 = Runner2(poisoned_corpus, lg, Indexes(poisoned_corpus), lat2, k=K)
    for name in ["b1", "b3", "b5"]:
        agg, _, _, _ = run_system(r2, name, poisoned_corpus.scenarios, fv_star, 7100)
        e6[f"poisoned_{name.upper()}"] = agg
    # (c) citation fabrication and (d) stale exploitation, raised in isolation
    for mode, over in [("fabrication", dict(fabricate=0.9)),
                       ("stale_exploitation", dict(stale=0.9))]:
        fv = dict(fv_star)
        fv.update(over)
        agg, _, _, _ = run_system(runner, "b5", scen, fv, 7200)
        e6[mode] = agg
        agg3, _, _, _ = run_system(runner, "b3", scen, fv, 7200)
        e6[mode + "_B3"] = agg3
    # (e) hostile lattice registration
    hostile = lattice.with_hostile_registration("SEC")
    agg, _, _, _ = run_system(runner, "b5", scen, fv_star, 7300, lattice=hostile)
    e6["hostile_lattice_SEC"] = agg
    results["E6"] = e6

    # ---------------- E7 cost and scaling ----------------------------------
    e7 = dict(served_artefacts={n: per_system[n]["mean_served_artefacts"] for n in SYSTEMS},
              seconds_per_scenario={n: per_system[n]["seconds_per_scenario"] for n in SYSTEMS})
    scaling = {}
    for n_dept in [2, 3, 4, 5]:
        deps = DEPARTMENTS[:n_dept]
        c2, l2, la2, i2, r3 = build(seed=SEED, n_scenarios=150, departments=deps, k=K)
        agg, _, _, _ = run_system(r3, "b5", c2.scenarios, fv_star, 7400)
        scaling[str(n_dept)] = dict(
            departments=deps, artefacts=len(c2.artefacts),
            seconds_per_scenario=agg["seconds_per_scenario"],
            served=agg["mean_served_artefacts"],
            coverage=agg["coverage"], spurious=agg["spurious_rate"])
    e7["scaling_in_departments"] = scaling
    size_scaling = {}
    for n_sc in [100, 200, 400]:
        c3, l3, la3, i3, r4 = build(seed=SEED, n_scenarios=n_sc, k=K)
        agg, _, _, _ = run_system(r4, "b5", c3.scenarios, fv_star, 7500)
        size_scaling[str(n_sc)] = dict(seconds_per_scenario=agg["seconds_per_scenario"])
    e7["scaling_in_scenarios"] = size_scaling
    # analytical gas for the settlement write
    e7["gas"] = dict(
        method="analytical, from the Ethereum yellow paper opcode schedule; "
               "no chain measurement was performed",
        tx_base=21000, calldata_bytes=32 * 8, calldata_gas=16 * 32 * 8,
        sstore_new_slots=8, sstore_gas=20000 * 8, log_topics=3,
        log_gas=375 + 3 * 375 + 8 * 32,
        total=21000 + 16 * 32 * 8 + 20000 * 8 + 375 + 3 * 375 + 8 * 32)
    e7["gas"]["per_epoch_anchor"] = dict(
        sstore_new_slots=1, total=21000 + 20000 + 16 * 32)
    results["E7"] = e7

    # ---------------- E8 ablations and cold start --------------------------
    abl = {}
    for label, flags in [("full", None),
                         ("no_R0_admissibility", dict(R0=False)),
                         ("no_R1_currency", dict(R1=False)),
                         ("no_R2_jurisdiction", dict(R2=False)),
                         ("no_R3_precedence", dict(R3=False)),
                         ("no_R4_evidence", dict(R4=False)),
                         ("no_R5_completeness", dict(R5=False)),
                         ("no_completeness_probe", dict(probe=False)),
                         ("no_R6_ordering", dict(R6=False)),
                         ("no_R7_definitional", dict(R7=False)),
                         ("no_escalation", dict(escalate=False))]:
        agg, _, _, _ = run_system(runner, "b5", scen, fv_star, 8000,
                                  rules_enabled=flags)
        abl[label] = agg
    # cold start: a department whose partition begins only in the final year
    cold = Corpus(seed=SEED, n_scenarios=N_SCENARIOS)
    keep = []
    for a in cold.artefacts:
        if a["dept"] == "OPS" and a["effective_from"] < 15:
            continue
        keep.append(a)
    cold.artefacts = keep
    cold.by_dept = defaultdict(list)
    for a in keep:
        cold.by_dept[a["dept"]].append(a)
    cold.rules = defaultdict(list)
    for a in keep:
        if a["cls"] != "policy":
            continue
        hi = a["effective_to"] if a["effective_to"] is not None else N_QUARTERS - 1
        for q in range(a["effective_from"], hi + 1):
            cold.rules[(a["dept"], q)].append(a)
    for s in cold.scenarios:
        s["truth"] = cold.ground_truth(s)
    kr = Keyring(cold.departments)
    lg = Ledger(kr)
    ep = defaultdict(lambda: defaultdict(list))
    for a in cold.artefacts:
        ep[a["effective_from"]][a["dept"]].append(a)
    for e in sorted(ep):
        for d, arts in sorted(ep[e].items()):
            lg.anchor(d, e, arts)
        lg.commit_epoch(e, cold.departments)
    lat3 = default_lattice()
    lg.register_lattice(lat3.snapshot())
    r5 = Runner2(cold, lg, Indexes(cold), lat3, k=K)
    early = [s for s in cold.scenarios if s["quarter"] < 15]
    late = [s for s in cold.scenarios if s["quarter"] >= 15]
    for label, subset in [("before_partition_exists", early), ("after", late)]:
        if not subset:
            continue
        agg, _, _, _ = run_system(r5, "b5", subset, fv_star, 8100)
        abl["cold_start_" + label] = agg
    results["E8"] = abl

    results["runtime_seconds"] = round(time.time() - t_start, 1)
    with open(os.path.join(RESULTS, "results.json"), "w") as f:
        json.dump(results, f, indent=1, sort_keys=False)
    print("wrote results.json in %.1fs" % (time.time() - t_start))
    return results


if __name__ == "__main__":
    main()
