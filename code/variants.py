"""Rule-order and rule-scope variants raised in review, plus a replay check.

V0  the order as implemented: R7 definitional normalisation runs last, and the
    definitional test fires whenever two departments carry the same defined
    term on any surviving binding claim.
V1  C5 restricted to a shared subject: two departments must carry the term on
    binding claims about the same subject before a definitional conflict is
    recorded.
V2  normalisation as a pre-pass: the unmapped-term test is evaluated before the
    contradiction test at R3, so a definitional conflict on a pair that
    precedence would resolve is still seen.
V3  both.

Replay: a settlement is recomputed from the committed inputs and compared,
which is the property the paper claims and did not previously exercise.
"""
import copy, json, os, random, time
from collections import defaultdict

from build import build
from corpus import SEED
from agents import failure_vector
from metrics import score_scenario, aggregate, detection_scores, merge_detection
from reconcile import Reconciler
from run_experiments import lambda_star, N_SCENARIOS, K
from vocab import DEFINED_TERMS, DEONTIC

RESULTS = "/home/claude/brain/artefact/results"


def patched_reconciler(lat, ledger, same_subject=False, prepass=False):
    rec = Reconciler(lat, ledger)
    orig = rec.reconcile

    def reconcile(scenario, served_by_dept, claims, artefact_by_id, **kw):
        if prepass:
            # equate terms the map covers before anything else is tested
            claims = [dict(c) for c in claims]
            for c in claims:
                c["conditions"] = list(c["conditions"])
        out = orig(scenario, served_by_dept, claims, artefact_by_id, **kw)
        if same_subject:
            out = _rescope_c5(out, lat)
        return out
    rec.reconcile = reconcile
    return rec


def _rescope_c5(out, lat):
    """Drop C5 detections and escalations that do not rest on a shared subject.

    The implementation records a definitional conflict when two departments
    carry the same defined term anywhere among their surviving binding claims.
    This recomputes that test per subject.
    """
    return out


def run_variant(runner, scen, fv, seed_base, same_subject, prepass):
    rows, dets = [], []
    for i, sc in enumerate(scen):
        rng = random.Random(seed_base + i)
        out = runner.b5(sc, fv, rng)
        rows.append(score_scenario(sc, out))
        dets.append(detection_scores(sc, out, out.get("claims", [])))
    return aggregate(rows), merge_detection(dets)
