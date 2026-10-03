"""Scores the model in the loop returns and writes results/llm_calibration.json.

The six failure rates are measured against what the served context actually
supported, not against ground truth, so the measurement is of the drafting step
alone. Wilson intervals are reported because the sample is small.
"""

import glob
import json
import math
import os

from build import build
from corpus import SEED
from vocab import DEONTIC, SUBJECTS
from make_llm_batches import K_SAMPLE

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")
OUT = os.path.join(RESULTS, "llm_returns")


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def main():
    prompts = json.load(open(os.path.join(OUT, "prompts.json")))
    by_id = {b["batch_id"]: b for b in prompts["batches"]}
    returns = {}
    files = sorted(glob.glob(os.path.join(OUT, "returns_part*.json")))
    for f in files:
        returns.update(json.load(open(f))["returns"])

    corpus, ledger, lattice, indexes, runner = build(seed=SEED, n_scenarios=400, k=24)
    lat = lattice

    counts = dict(omit=[0, 0], spurious=[0, 0], modality=[0, 0], stale=[0, 0],
                  fabricate=[0, 0], overreach=[0, 0])
    schema_invalid = 0
    n_claims = 0

    for bid, batch in by_id.items():
        if bid not in returns:
            continue
        served = {a["artefact_id"]: a for a in batch["served"]}
        q = batch["quarter"]

        def current(a):
            hi = a["effective_to"]
            return a["effective_from"] <= q and (hi is None or q <= hi)

        # what the served context supports: for each (claim type, subject) the
        # agent was asked about, the newest served artefact in window
        supported = {}
        for a in batch["served"]:
            if a["cls"] not in ("policy", "position") or not a["claim_type"]:
                continue
            asked = {c["claim_type"]: c for c in batch["claim_types"]}
            if a["claim_type"] not in asked:
                continue
            if a["subject"] not in batch["subjects_raised"]:
                continue
            if not current(a):
                continue
            key = (a["claim_type"], a["subject"])
            if key not in supported or a["policy_version"] > supported[key]["policy_version"]:
                supported[key] = a

        claims = returns[bid].get("claims", [])
        emitted = set()
        roles = {c["claim_type"]: c["role"] for c in batch["claim_types"]}
        for cl in claims:
            n_claims += 1
            if not all(k in cl for k in ("claim_type", "subject", "modality",
                                         "conditions", "citations")):
                schema_invalid += 1
                continue
            key = (cl["claim_type"], cl["subject"])
            emitted.add(key)
            # unsupported assertion
            counts["spurious"][1] += 1
            if key not in supported:
                counts["spurious"][0] += 1
            # citation fabrication
            counts["fabricate"][1] += 1
            if any(c not in served for c in cl["citations"]):
                counts["fabricate"][0] += 1
            # reliance on superseded material when a current artefact was served
            cited = [served[c] for c in cl["citations"] if c in served]
            if cited:
                counts["stale"][1] += 1
                if all(not current(a) for a in cited) and key in supported:
                    counts["stale"][0] += 1
            # modality drift against the artefact relied on
            if key in supported and roles.get(cl["claim_type"]) == "owned":
                counts["modality"][1] += 1
                if cl["modality"] != supported[key]["modality"]:
                    counts["modality"][0] += 1
            # assertion outside mandate
            if roles.get(cl["claim_type"]) == "consulted":
                counts["overreach"][1] += 1
                if cl["modality"] in DEONTIC:
                    counts["overreach"][0] += 1
        # omission of supported content
        for key in supported:
            counts["omit"][1] += 1
            if key not in emitted:
                counts["omit"][0] += 1

    rates = {k: (v[0] / v[1] if v[1] else 0.0) for k, v in counts.items()}
    cal = dict(
        model="claude-opus-5",
        n_batches=len([b for b in by_id if b in returns]),
        n_scenarios=len({by_id[b]["scenario_id"] for b in by_id if b in returns}),
        n_claims=n_claims,
        schema_invalid=schema_invalid,
        k_served_per_partition=K_SAMPLE,
        counts={k: dict(events=v[0], trials=v[1]) for k, v in counts.items()},
        measured_rates={k: round(v, 4) for k, v in rates.items()},
        wilson_95={k: wilson(v[0], v[1]) for k, v in counts.items()},
        note=("rates are measured against the served context alone; ground "
              "truth was never shown to the drafting model. The drafting "
              "model and the model that built the harness are the same model, "
              "which Section V states as a threat to internal validity."))
    with open(os.path.join(RESULTS, "llm_calibration.json"), "w") as f:
        json.dump(cal, f, indent=1)
    print(json.dumps(cal["measured_rates"], indent=1))
    print("claims", n_claims, "batches", cal["n_batches"])
    return cal


if __name__ == "__main__":
    main()
