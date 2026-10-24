# When Departments Disagree: BRAIN artefact

Reference implementation, corpus generator, model returns and results for the paper

**When Departments Disagree: Mandate-Aware Reconciliation of Agentic AI Guidance over a Permissioned Ledger**

Khaled Almi'ani, Nedal Ababneh and Camille Zufferey

BRAIN stands for Blockchain Reconciled Agentic Institutional Network. All results use the global seed 20260902.

## Reproduce

    cd code
    python run_experiments.py     # writes ../results/results.json  (~200 s)
    python make_figures.py        # writes ../../figures/*.pdf and ../figures_png/*.png

`score_llm_batches.py` recomputes `results/llm_calibration.json` from the
stored model returns; `make_llm_batches.py` regenerates the prompts.
Requires python3 with numpy-free stdlib only, plus matplotlib for figures and
`cryptography` for Ed25519 (an HMAC fallback is used if it is absent).

## Layout

    code/vocab.py          closed vocabularies, departments, claim types, lattice inputs
    code/corpus.py         corpus and scenario generator, ground truth
    code/ledger.py         canonical JSON, Ed25519, Merkle batching, two stage anchoring
    code/lattice.py        the authority lattice, registration conditions, attacks
    code/retrieval.py      BM25 over partitions and over a pooled index
    code/agents.py         departmental agents, six failure modes, completeness probe
    code/reconcile.py      rules R0 to R7 and the escalation terminal
    code/systems.py        baselines B0 to B5 and the B3P probe-without-lattice variant
    code/metrics.py        deterministic scoring, no model judge
    code/build.py          corpus construction and ledger anchoring
    code/run_experiments.py  experiments E1 to E8
    code/make_figures.py     all twelve figures
    code/make_llm_batches.py, code/score_llm_batches.py   model in the loop
    code/contracts/        AuthorityLattice.sol, SettlementRegistry.sol (unaudited)
    results/results.json   every number in the paper
    results/DATA_CARD.md   what is measured, constructed, or analytical
    results/llm_returns/   prompts and verbatim model returns
    figures/               the twelve figures as PDF
    figures_png/           the same figures as PNG

## Read this first

`results/DATA_CARD.md` states which numbers are measurements, which follow from
the construction of the corpus, and which are analytical. The corpus is
synthetic, the gas figures are analytical, the contracts are unaudited, and the
drafting model and the model that built the harness are the same model.

## Earlier version

`paper_preprint.tex` and `paper_preprint.pdf` hold an earlier preprint of the manuscript under its previous title.

## Citation

If you use this artefact, please cite:

K. Almi'ani, N. Ababneh, C. Zufferey, When Departments Disagree: Mandate-Aware Reconciliation of Agentic AI Guidance over a Permissioned Ledger, manuscript submitted for publication, 2026.
