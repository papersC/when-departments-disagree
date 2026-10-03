"""Builds the prompts for the model in the loop sample.

Each prompt gives one department the claim types it has been routed, the
artefacts served to it from its own partition, and the schema it must answer
in. Ground truth is never written into a prompt, and the prompt files are the
only input the drafting model is given.
"""

import json
import os
import random

from build import build
from corpus import SEED
from vocab import SUBJECTS, CLAIM_TYPES, owner
from agents import route
from retrieval import type_focus

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")
OUT = os.path.join(RESULTS, "llm_returns")
os.makedirs(OUT, exist_ok=True)

K_SAMPLE = 10          # served artefacts per partition in the sample
N_SAMPLE = 10          # scenarios in the sample

SCHEMA = {
    "claims": [{
        "claim_type": "one of the claim types you were asked about",
        "subject": "one of the subjects raised by the situation",
        "modality": "must | must_not | should | should_not | may | fact",
        "conditions": ["condition terms taken from the artefact you rely on"],
        "citations": ["artefact ids from the served context"],
        "confidence": "number between 0 and 1"}]
}

INSTRUCTION = (
    "You are the drafting agent of one department of an organisation. You are "
    "given the situation an employee has raised, the claim types your "
    "department has been asked about, and the artefacts served to you from "
    "your own department's store. Emit one claim per claim type and subject "
    "that your served artefacts support. Draw modality, conditions and "
    "citations from the served artefacts only. You own a claim type when the "
    "prompt marks it owned; for a claim type marked consulted you may report "
    "your department's position but the modality you emit should be fact "
    "unless your own material genuinely obliges the organisation. Answer with "
    "JSON matching the schema and nothing else.")


def build_batches():
    corpus, ledger, lattice, indexes, runner = build(seed=SEED, n_scenarios=400, k=24)
    rng = random.Random(31337)
    # stratify by the conflict classes present in the scenario
    buckets = {}
    for sc in corpus.scenarios:
        classes = tuple(sorted({c for c, _, _ in sc["truth"]["escalations"]})) or ("none",)
        buckets.setdefault(classes, []).append(sc)
    chosen = []
    for key in sorted(buckets):
        chosen.append(rng.choice(buckets[key]))
    rng.shuffle(chosen)
    chosen = chosen[:N_SAMPLE]

    batches = []
    for sc in chosen:
        plan = route(lattice, sc["types"])
        for dept, types in plan.items():
            hits = indexes.dept(dept, type_focus(sc["situation"], types), K_SAMPLE)
            served = [a for a, _ in hits if ledger.verify_artefact(a)]
            batches.append(dict(
                batch_id=f"{sc['scenario_id']}-{dept}",
                scenario_id=sc["scenario_id"], department=dept,
                quarter=sc["quarter"],
                situation=sc["situation"],
                subjects_raised=sc["subjects"],
                claim_types=[dict(claim_type=t,
                                  role=("owned" if lattice.owner(t) == dept else "consulted"),
                                  subjects=[s for s in sc["subjects"] if t in SUBJECTS[s]])
                             for t in types],
                served=[dict(artefact_id=a["artefact_id"], cls=a["cls"],
                             policy_family=a["policy_family"],
                             policy_version=a["policy_version"],
                             effective_from=a["effective_from"],
                             effective_to=a["effective_to"],
                             claim_type=a["claim_type"], subject=a["subject"],
                             modality=a["modality"], conditions=a["conditions"])
                        for a in served]))
    payload = dict(instruction=INSTRUCTION, schema=SCHEMA,
                   note=("the quarter is the date at which the question is "
                         "asked; an artefact whose effective window does not "
                         "contain it has been superseded"),
                   batches=batches)
    with open(os.path.join(OUT, "prompts.json"), "w") as f:
        json.dump(payload, f, indent=1)
    print(f"wrote {len(batches)} prompts for {len(chosen)} scenarios")
    return payload


if __name__ == "__main__":
    build_batches()
