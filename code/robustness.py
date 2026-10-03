"""Phase A robustness runs.

E9  agent-seed spread: the headline comparison repeated over five independent
    agent noise realisations on the same corpus and the same scenarios.
E10 ablation noise floor: the ablation set repeated over three seeds, so that
    a rule effect can be told apart from seed noise.
E11 modality drift sensitivity: the operating point does not cover modality
    drift, whose Wilson upper bound is 0.259 and which no grid value reaches.
    The base rate is raised until the simulated rate meets that bound.
"""
import json, os, statistics, sys, time

from build import build
from corpus import SEED
from agents import failure_vector, BASE_FAILURE
from metrics import merge_detection
from systems import SYSTEMS
from run_experiments import run_system, lambda_star, N_SCENARIOS, K

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")

SEED_BASES = [5000, 5100, 5200, 5300, 5400]
ABL_SEEDS = [8000, 8100, 8200]
METRICS = ["coverage", "spurious_rate", "attribution_rate",
           "jurisdiction_violation_rate", "citation_validity",
           "stale_obligation_rate", "silent_wrong_answer_rate",
           "escalation_precision", "escalation_recall", "n_emitted"]

ABLATIONS = [("full", None), ("no_R0_admissibility", dict(R0=False)),
             ("no_R1_currency", dict(R1=False)), ("no_R2_jurisdiction", dict(R2=False)),
             ("no_R3_precedence", dict(R3=False)), ("no_R4_evidence", dict(R4=False)),
             ("no_R5_completeness", dict(R5=False)), ("no_completeness_probe", dict(probe=False)),
             ("no_R6_ordering", dict(R6=False)), ("no_R7_definitional", dict(R7=False)),
             ("no_escalation", dict(escalate=False))]


def spread(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return dict(mean=round(statistics.mean(vals), 4), lo=round(min(vals), 4),
                hi=round(max(vals), 4), range=round(max(vals) - min(vals), 4),
                sd=round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0,
                n=len(vals))


def main(stage):
    t0 = time.time()
    lam, _ = lambda_star()
    fv = failure_vector(lam)
    corpus, ledger, lattice, indexes, runner = build(seed=SEED, n_scenarios=N_SCENARIOS, k=K)
    scen = corpus.scenarios
    out_path = os.path.join(RESULTS, "robustness.json")
    out = json.load(open(out_path)) if os.path.exists(out_path) else {}
    out.setdefault("meta", dict(seed=SEED, n_scenarios=N_SCENARIOS, k=K,
                                lambda_star=lam, base_failure=BASE_FAILURE))

    if stage in ("e9", "all"):
        raw = {n: {m: [] for m in METRICS} for n in SYSTEMS}
        for sb in SEED_BASES:
            for name in SYSTEMS:
                agg, _, _, _ = run_system(runner, name.lower(), scen, fv, sb)
                for m in METRICS:
                    raw[name][m].append(agg.get(m))
            print(f"  seed {sb} done  {time.time()-t0:.0f}s", flush=True)
        out["E9_seed_spread"] = dict(
            seed_bases=SEED_BASES,
            systems={n: {m: spread(raw[n][m]) for m in METRICS} for n in SYSTEMS},
            raw={n: {m: raw[n][m] for m in METRICS} for n in SYSTEMS})
        json.dump(out, open(out_path, "w"), indent=1)
        print("E9 written", flush=True)

    if stage in ("e10", "all"):
        raw = {lab: {m: [] for m in METRICS} for lab, _ in ABLATIONS}
        for sb in ABL_SEEDS:
            for lab, flags in ABLATIONS:
                agg, _, _, _ = run_system(runner, "b5", scen, fv, sb, rules_enabled=flags)
                for m in METRICS:
                    raw[lab][m].append(agg.get(m))
            print(f"  abl seed {sb} done  {time.time()-t0:.0f}s", flush=True)
        out["E10_ablation_noise"] = dict(
            seed_bases=ABL_SEEDS,
            ablations={lab: {m: spread(raw[lab][m]) for m in METRICS} for lab, _ in ABLATIONS},
            raw={lab: raw[lab] for lab, _ in ABLATIONS})
        json.dump(out, open(out_path, "w"), indent=1)
        print("E10 written", flush=True)

    if stage in ("e11", "all"):
        bound = 0.259           # Wilson 95 upper bound on modality drift
        need = bound / lam      # base rate required for lam*base >= bound
        raised = round(need + 0.005, 3)
        res = {}
        for tag, base in [("standard", None),
                          ("modality_at_bound", dict(BASE_FAILURE, modality=raised))]:
            fvx = failure_vector(lam, base)
            for name in ["B5", "B3P"]:
                agg, _, det, _ = run_system(runner, name.lower(), scen, fvx, 9000)
                by = merge_detection([det]) if isinstance(det, list) else det
                res[f"{tag}|{name}"] = dict(
                    modality_rate=round(fvx["modality"], 4),
                    **{m: agg.get(m) for m in METRICS},
                    detection=by.get("by_class") if isinstance(by, dict) else None)
            print(f"  {tag} done  {time.time()-t0:.0f}s", flush=True)
        out["E11_modality_sensitivity"] = dict(
            wilson_upper_bound=bound, lambda_star=lam,
            base_rate_required=round(need, 4), base_rate_used=raised,
            note="the standard base rate is 0.15, giving a simulated rate of "
                 "0.090 at lambda star, which is below the bound; the raised "
                 "base rate brings the simulated rate to or above it",
            runs=res)
        json.dump(out, open(out_path, "w"), indent=1)
        print("E11 written", flush=True)
    print(f"stage {stage} complete in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")


def stage_e12():
    """The two review baselines, over three noise realisations."""
    import random, statistics
    import extra_systems
    from metrics import score_scenario, aggregate, detection_scores, merge_detection
    t0 = time.time()
    lam, _ = lambda_star()
    fv = failure_vector(lam)
    corpus, _, _, _, runner = build(seed=SEED, n_scenarios=N_SCENARIOS, k=K)
    scen = corpus.scenarios
    out_path = os.path.join(RESULTS, "robustness.json")
    out = json.load(open(out_path))
    raw = {n: {m: [] for m in METRICS} for n in ["B2F", "B4A"]}
    for sb in [5000, 5100, 5200]:
        for nm, fn in [("B2F", extra_systems.b2f), ("B4A", extra_systems.b4a)]:
            rows = [score_scenario(sc, fn(runner, sc, fv, random.Random(sb + i)))
                    for i, sc in enumerate(scen)]
            agg = aggregate(rows)
            for m in METRICS:
                raw[nm][m].append(agg.get(m))
        print(f"  e12 seed {sb} done {time.time()-t0:.0f}s", flush=True)
    out["E12_review_baselines"] = dict(
        seed_bases=[5000, 5100, 5200],
        note="B2F is a pooled index with department labels plus an effective "
             "window currency filter and an exact metadata lookup, and no "
             "lattice. B4A is the referee of B4 given an abstention state on "
             "subjects where two departments assert incompatible modalities.",
        systems={n: {m: spread(raw[n][m]) for m in METRICS} for n in ["B2F", "B4A"]},
        raw=raw)
    json.dump(out, open(out_path, "w"), indent=1)
    print("E12 written", flush=True)
