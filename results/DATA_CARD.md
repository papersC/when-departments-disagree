# Data card

This card states, for every quantity reported in the paper, whether it is a
measurement, a construction, or an analytical calculation. Read it before
citing any number from `results.json`.

Global seed: **20260902**. Signature scheme: **Ed25519**. Runtime for a full
run of `run_experiments.py`: about 200 seconds on one core.

## The corpus is synthetic

No organisation has published five years of departmental policy conflict, so
the corpus is generated. That is the single largest limitation of this work.
Everything below that depends on the corpus is therefore a measurement *of a
constructed distribution*, not an estimate of any real organisation.

**Constructed, not measured:**

- The number of departments (5), claim types (25), subjects (38), predicates
  (20) and defined terms (6).
- The revision cadences (2, 3, 4, 5, 6 quarters per department) and hence the
  version skew reported in E1. The *consequence* of those cadences — 58 to 84
  distinct policy versions in force at once — is computed from the corpus, but
  the cadences themselves were chosen.
- The **47.5 per cent** prevalence of scenarios that admit no reconciled
  organisational position. Scenarios are deliberately seeded on subjects that
  two owners speak about, so this figure is a property of the generator. It is
  not an estimate of how often real departments disagree.
- Which subjects carry a registered precedence chain (10 of 18). The eight
  without one exist so that the framework has something it must escalate.
- The authority lattice itself: ownership, consultation and mandatory flags.

**Measured over the constructed corpus:**

- Everything in E2 to E8: coverage, spurious rate, attribution, jurisdiction
  violation, citation validity, staleness, silent wrong answers, escalation
  precision and recall, detection by class, adversarial degradation, ablation
  effects, timings.

## Ground truth and the circularity it creates

Ground truth is computed in `corpus.ground_truth` from the corpus and the
lattice alone — no retrieval, no agent, no system under test. BRAIN is designed
to compute the same function through a lossy pipeline, so part of its advantage
is definitional. Three facts bound that concern and are stated in the paper:

1. Every baseline is scored against the same organisational truth.
2. BRAIN does not reach it (0.870, not 1.000).
3. The comparisons that matter — B2 vs B5 (provenance visibility vs
   projection) and B4 vs B5 (model referee vs registered mandate) — are between
   architectures with identical evidence.

Precedence cycles (C2) are generated from a fixed list of interacting rules
rather than from the conflict taxonomy, so their detection recall (0.739) is
the least self-consistent detection number in the paper.

## The departmental agent is simulated

The agent is a parameterised generator with six failure modes scaled by a
single parameter λ. The **shape** of the failure vector (base rates 0.25 omit,
0.20 spurious, 0.15 modality, 0.30 stale, 0.12 fabricate, 0.25 overreach) is a
design choice, not a measurement. Every headline result is therefore
accompanied by a sweep over λ from 0.0 to 1.0.

## The model in the loop

- 10 scenarios, stratified by conflict class; 38 prompts; **51 claims**.
- The drafting model is `claude-opus-5`, reached through the session interface
  (no API key was available in the execution environment).
- Prompts contain the situation, the routed claim types with owned/consulted
  role, and the served artefacts. **Ground truth appears in no prompt.**
- Result: **zero** instances of all six failure modes, all claims schema-valid.
- This is a *bound*, not a point estimate. 95% Wilson upper bounds: 0.070 on
  the four rates estimated over all 51 claims, 0.088 on overreach (40
  opportunities), 0.259 on modality drift (11 opportunities — excluded as
  uninformative).
- λ\* = 0.6 is the smallest grid value whose failure vector lies at or above
  every usable upper bound (binding constraint: citation fabrication, which
  requires λ ≥ 0.583). The headline table is therefore reported with a
  simulated agent **substantially worse** than the model measured.
- **Conflict of interest:** the drafting model and the model that wrote the
  harness, the generator and the analysis are the same model. Mitigations
  (programmatic prompts, no ground truth in prompts, deterministic scoring,
  sample used only to fix an operating point) are partial. Section V of the
  paper states this.

Returns are in `results/llm_returns/returns_part1.json` and
`returns_part2.json`, verbatim. Prompts are in `prompts.json`.

## Analytical, not measured

- **All gas figures.** 186,852 gas per settlement and 41,512 per epoch anchor
  are computed from the standard opcode schedule (21,000 tx base + 16 gas per
  calldata byte + 20,000 per new storage slot + log costs). No chain or testnet
  deployment was performed.
- The Solidity contracts in `code/contracts/` **have not been audited**. They
  are a specification of the on-chain interface, not production code.

## Known measurement artefacts

- The `full` row of the ablation table (E8) uses its own seed stream and so
  differs slightly from the B5 row of the system table (E4): 0.888 vs 0.870
  coverage. Both are correct; neither is a tuned figure.
- `E5.coverage_surrendered` is negative (−0.449) because coverage *rose* rather
  than fell. The field name records the hypothesis, not the result.
- nDCG@10 values in E2 are low in absolute terms (0.209 partitioned, 0.340
  pooled) because most served artefacts have graded relevance 0. Only the
  comparison between the two is meaningful.
- Retrieval is memoised in `retrieval.py`. The cache changes nothing about what
  is retrieved; it only avoids repeating identical searches across the λ sweep.

## What would falsify the design

Stated before the experiments were run, and reported either way:

- If B2 had matched B5 on jurisdiction violations, provenance visibility alone
  would suffice and the lattice would be unnecessary. It did not: 0.546 vs
  0.000.
- If B4 had matched B5 on attribution and escalation, a model referee would
  suffice. It did not: 0.481 vs 1.000, and it never escalates.
- If B5's silent wrong answer rate had not fallen materially below B1 and B3,
  the central safety claim would fail. It fell from 0.890 to 0.100.
- The anticipated coverage loss did **not** materialise, because the
  completeness probe more than offsets the retrieval loss. That prediction was
  wrong and is reported as wrong.


## Post-review runs (`results/robustness.json`)

Added after a five-reviewer audit. `results.json` is unchanged and still
reproduces byte for byte; everything below lives in `robustness.json` and is
produced by `code/robustness.py` and `code/extra_systems.py`.

- **E9 seed spread.** The headline comparison over five independent agent noise
  realisations on the same corpus and scenarios. B5 coverage mean 0.877, range
  0.017; B3P 0.497, range 0.047. Attribution, citation validity, jurisdiction
  violation and stale obligation have range **exactly 0.000** across all five,
  which is the empirical form of their being construction identities.
  Escalation precision is the least stable quantity in the paper: mean 0.913,
  range 0.061.
- **E10 ablation noise floor.** The ablation set over three seeds. Widest range
  for any single configuration: 0.038 coverage, 0.084 silent wrong answers.
  Coverage effects above that floor: R1, R2, R3, probe. Below it, and therefore
  not interpretable: R0, R4, R5, R6.
- **E11 modality drift sensitivity.** λ\* does not bound modality drift (11
  opportunities, Wilson upper bound 0.259; simulated rate 0.090). Raising the
  base rate from 0.15 to 0.437 brings it to 0.262. B5 coverage falls 0.892 →
  0.710, spurious 0.221 → 0.395, silent 0.095 → 0.137, C1 precision 0.500 →
  0.465. B3P moves 0.501 → 0.474. **This is the framework's largest measured
  exposure apart from a compromised registry.**
- **E12 affordance-matched baselines.** B2F = pooled + labels + effective-window
  filter + exact metadata lookup, no lattice. B4A = referee with an abstention
  state. B2F reaches 0.706 coverage — more than half the coverage separation
  previously credited to the framework — at 0.651 attribution and 0.774 silent
  wrong answers. B4A reaches 0.126 silent wrong answers, close to B5's 0.100,
  at 0.343 coverage and 0.482 escalation precision. **The coverage advantage
  falls from 0.373 to 0.164 once the affordances are granted; the attribution
  advantage is unaffected.**
- **E13 rule-order variants.** Two reviewer-proposed corrections implemented and
  measured. Restricting the definitional test to a shared subject: precision
  1.000, recall 0.590 → 0.077, silent 0.100 → 0.232. Evaluating it before the
  contradiction test: recall → 0.192, silent → 0.211. Both degrade the system;
  the implemented order is retained on evidence. Also verified by reading the
  code: the definitional test operates on the post-R2 binding set, so an
  advisory claim cannot withdraw an owner's claim.
- **E14 replay.** All 400 settlements recomputed from the same committed inputs
  and compared on obligations, attribution, support, escalations and rule
  trace: 400/400 identical. Advice-set hash stable across an independent
  rebuild from the global seed. R6 tests for a cycle and emits no order, so no
  ordering convention is needed for replay.

`reconcile.py` gained two flags (`c5_subject_scoped`, `c5_prepass`), both
defaulting to the behaviour as first implemented. The refactor was verified
behaviour-preserving: coverage 0.8695, silent 0.100, escalation precision
0.9037, C5 0.742/0.590 — identical to the released results.
