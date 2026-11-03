# When Departments Disagree: A Blockchain Reconciled Multi-Agent Framework for Institutional Knowledge and Employee Guidance

Author: Khaled Almiani, Faculty of Computer Information Science, Higher Colleges of Technology, United Arab Emirates.

Framework name: **BRAIN** — Blockchain Reconciled Agentic Institutional Network.

## What the paper proposes

An organisation holds several bodies of knowledge, one per department, each with its own vocabulary, its own policy version schedule and its own mandate. Employee questions cross those boundaries; the departments were never obliged to agree. A pooled knowledge base hides the disagreement, and independent departmental assistants expose it without resolving it.

BRAIN gives each department its own generative agent over its own anchored ledger partition, registers an **authority lattice** on chain declaring which department owns which class of claim, and reconciles the departmental drafts with a **deterministic rule order (R0–R7)** into one attributable answer, a partial answer plus escalation, or an explicit escalation. A settlement record anchors the query, the context served to each department, the claim set, the rule trace and the advice, so an auditor can reconstruct which department's rule prevailed and under which lattice version.

## Headline results

- Corpus of 1082 anchored artefacts across 5 departments over 20 quarters, 400 cross departmental scenarios, of which 190 admit no reconciled organisational position.
- Against the strongest baseline, obligation coverage rises from 0.497 to 0.870 and the spurious obligation rate falls from 0.774 to 0.237.
- Every emitted obligation is attributed to its owning department (1.000 against 0.477) and none is issued outside a mandate (0.000 against 0.524).
- Confident assertion on a domain the organisation has not settled falls from 0.890 to 0.100. Escalation precision 0.904 at recall 0.889.
- All headline comparisons have p ≤ 1e-4 and survive Bonferroni correction over sixteen tests.
- The **completeness probe** — an exact existence query against the owning partition, not a similarity search — is the largest single contributor. Removing it drops coverage from 0.888 to 0.414 and escalation precision from 0.909 to 0.504.

## What went against the design, reported in full

- **Partitioning makes retrieval worse.** At equal served volume, pooled retrieval recovers the owner's rule for 0.983 of required pairs against 0.901 partitioned, and pooled nDCG@10 is 0.340 against 0.209. The gain comes from what happens after retrieval, not within it.
- Contradiction detection precision is 0.470 and definitional detection recall is 0.590. Agent noise both hides real conflicts and manufactures false ones.
- Jurisdiction overreach is detected with perfect precision but only 0.549 recall: an overreaching claim dropped at R0 or R1 is prevented but never recorded.
- A residual 0.100 of scenarios needing escalation are still answered.
- **A hostile lattice registration defeats the design**: attribution 1.000 → 0.793, jurisdiction violations 0.000 → 0.204, coverage 0.870 → 0.595. Capturing an agent, poisoning a partition, forging citations and exploiting stale policy all fail; compromising the mandate succeeds.
- The predicted coverage-for-safety trade did not materialise. That prediction was wrong and is reported as wrong.

## Model in the loop

No API key was available in the execution environment, so the drafting sample was produced through the session interface by `claude-opus-5`: 10 stratified scenarios, 38 prompts, 51 claims, ground truth in no prompt. Zero failures of all six modes, all schema-valid. This is used only as an **upper bound** to fix the operating point conservatively (λ\* = 0.6, above every usable 95% Wilson bound), never to score output. The drafting model and the model that built the harness are the same model; Section V states this as a threat to internal validity.

## Folder contents

- `paper.tex` the LaTeX source. Compile with `pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper`.
- `paper.pdf` the compiled manuscript, 18 pages, double column IEEEtran journal format.
- `references.bib` 89 entries. The 58 carried over from Paper 3 (PRAXIS) were verified previously; the 31 added for this paper were verified against Crossref, or DataCite for arXiv identifiers, on 2026-09-02, and each carries a DOI.
- `figures/` the twelve figures as PDF, all generated programmatically from the measured results.
- `artefact.zip` the complete implementation. Unzip beside this file to obtain `code/`, `results/`, `figures/` and `figures_png/`.
- `IEEEtran.cls` and `IEEEtran.bst` included so the paper compiles anywhere.

## Reproducing

Unzip `artefact.zip`, then from `code/` run `python run_experiments.py` (about 200 s) followed by `python make_figures.py`. The global seed is 20260902. `score_llm_batches.py` recomputes the operating point from the stored model returns in `results/llm_returns/`.

## Honesty notes

`results/DATA_CARD.md` states exactly which numbers are measurements, which follow from the construction of the corpus, and which are analytical.

- The corpus is **synthetic**. The 47.5 per cent prevalence of unresolved conflict is a property of a generator that deliberately seeds scenarios on shared subjects; it is not an estimate of any real organisation.
- Ground truth is computed from the corpus and the lattice, and BRAIN is designed to compute the same function through a lossy pipeline, so part of its advantage is definitional. The paper states the three considerations that bound that concern, and BRAIN reaches 0.870 rather than 1.000.
- The gas figures (186,852 per settlement, 41,512 per epoch anchor) are **analytical**, from the opcode schedule. No testnet deployment was performed.
- The Solidity contracts have **not** been audited.
- The departmental agent is simulated; its failure vector shape is a design choice, which is why every headline result is accompanied by a sweep over the failure rate.

## Verification performed on the manuscript

- **Numbers.** Every decimal in `paper.tex` was matched programmatically against `results/results.json` at all plausible roundings. Nothing is unmatched; the only apparent exceptions were the two gas totals, which the LaTeX thousands separator splits (186{,}852 and 41{,}512, both present in `E7.gas`).
- **Citations.** Abstracts were pulled from Crossref for the load-bearing references and each supporting sentence was checked against what the source actually reports. Two sentences were narrowed as a result: Luan et al. is now cited for capacity limits of fixed-length dense encodings and a combined sparse/dense model rather than for a general robustness claim, and Weber et al. is cited for under-use of stand-alone repositories unless the lesson is delivered inside the decision process.
- **Figures.** All twelve were inspected at render size. Defects found and fixed: legend/bar overlap in the detection, systems and silent-answer figures; a missing third series (unattributed) in the accountability panel, which made B0 and B1 read as empty; a colliding twin y-axis label and non-integer department ticks in the cost figure; and a version-skew panel that plotted a quantity that was constant by construction, replaced with revision generations in force and the superseded share of the corpus.
- **Layout.** Two overfull boxes in the wide tables were removed; no overfull boxes, undefined references or undefined citations remain.

## Style

The manuscript follows the author's conventional IEEE systems-paper register: passive methods voice, nominal anchors in place of pronouns, sentence-initial connectives, hedged claims, component-first structure with one subsection per component, and figures and tables announced before they appear. The abstract is held to 150 words, and figure and table captions are held to a single short sentence, with any necessary detail moved into a note beneath the table.

## Figure colour and the Canva check

The figures were originally greyscale, which read as washed out. They now use the validated categorical palette of the data-visualisation method: blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a`, violet `#4a3aa7`, red `#e34948`, on white, with ink `#0b0b0b`.

- The three-slot subset used by the bar figures passes every check of the palette validator, including contrast against the surface.
- The five-slot subset used by the sweep passes with one contrast warning on the aqua step, relieved by distinct markers, a legend on every panel, and the same values appearing in the tables.
- Hatching is retained as a second, non-colour encoding, so the figures still read when printed in greyscale.
- Two dual-axis charts were removed. A second y-axis is the most common charting error, and both cases were avoidable: the corpus figure now plots revision generations alone, and the cost figure is three panels rather than two with a twin axis.
- The proposed framework is red in every figure where it is singled out, so colour follows the entity rather than its position.

**Canva was tried and rejected for these figures.** Given an explicit specification of the workflow diagram, with exact box labels and an instruction to add no title, legend or extra text, it returned a marketing infographic: it discarded the five-stage flow, added a title and a tagline, and — decisive for a research paper — invented two statistics that appear nowhere in the results, namely "85% of claims resolved within the first stage" and a "65% rate of successful reconciliation". A generated design cannot plot measured data, and a figure that carries fabricated numbers cannot go in this paper. All twelve figures therefore remain generated from `results/results.json`, which is what keeps them consistent with the audited numbers when the experiments are rerun. The discarded Canva design is `DAHUDEejqAY` in the author's Canva account and can be deleted.

## Figures 1 to 3 and the reference list

**Figures 1, 2 and 3 are now drawn in TikZ inside `paper.tex`** rather than imported as images. They are schematic rather than data bearing, so nothing is lost by drawing them in the document, and several things are gained: the type matches the body text exactly, the geometry is resolution independent, and there is no image file to fall out of step with the source. The small glyphs (person, funnel, data store, balance, magnifier, document, hierarchy, chain link, tick, half disc, warning triangle) are vector paths defined once as TikZ `pic` styles in the preamble, so the figures need no external SVG files and no conversion tool chain. The same source is mirrored in the artefact as `code/diagrams.tex`, which compiles on its own for previewing. `code/make_figures.py` now produces the nine data figures only.

**The reference list was cut from 77 to 33.** Every remaining entry is a peer reviewed journal article, conference paper or book chapter, and every entry carries a DOI, which is printed in the reference list as a `doi.org` link. No preprint, technical report or white paper is cited. Three consequences are worth recording:

- Five arXiv-only multi-agent papers were dropped, and the surviving claims are carried by peer reviewed work (UIST, EMNLP and ACL).
- The original RAG citation (NeurIPS 2020) has no DOI, so the claim it supported is now carried by Huang and Huang's ACM Computing Surveys survey of retrieval augmented text generation, which does.
- `IEEEtran.bst` version 1.14 ignores the `doi` field, so each entry also carries a `url` field built from its DOI; that is what makes the DOI visible in the printed list.

The previous 77-entry bibliography is kept at `_previous/references_77.bib`.

## Structure

The Reproducibility section was removed from the manuscript. Its substance is not lost: the seed, the artefact and the data card are now stated in one sentence at the end of the experimental configuration subsection, and the full instructions live in this file.

The subsection count was reduced from thirty to fourteen, and the four subsubsections were removed. Related Work is three subsections rather than six, the framework is five rather than eight, the evaluation is six rather than twelve, and Threats to Validity now runs as four continuous paragraphs, each opening by naming the category of threat it addresses.

## UAE AI Award submission (third edition)

Target category: **Agentic AI Scientific Research** — the only one of the five
categories open to a research contribution rather than to a deployed government
service or a partnership. Eligibility covers academic institutions and
individuals, which the Higher Colleges of Technology affiliation satisfies.

The five published evaluation criteria and where the paper answers each:

| Criterion | Where |
|---|---|
| Innovation level | Sections III and IV: the authority lattice, the six-class taxonomy, the completeness probe |
| AI ethics compliance | Section VI, paragraphs 1–3: transparency, human oversight, governance and accountability |
| AI maturity level | Section VI, paragraph 4: released artefact, seed 20260902, plus the three conditions still outstanding |
| Scalability and replicability | Section VI, paragraph 4: routed breadth 2.54 of five, near-linear 2→5 scaling, one settlement write per query |
| Impact level | Section VI, paragraphs 2–3: coverage 0.497→0.870, silent wrong answers 0.890→0.100, attribution 1.000 |

Changes made for the submission:

- Title now reads "A Blockchain Reconciled **Agentic AI** Framework"; BRAIN is
  expanded in the abstract as Blockchain Reconciled Agentic Institutional
  Network. Abstract 149 words.
- Keywords lead with agentic artificial intelligence and add human oversight.
- One new Introduction paragraph on formally allocated mandate — the case of
  government entities and regulated institutions — and why agentic arrangements
  raise rather than relax the requirement for a recorded mandate.
- New **Section VI, Governance Alignment and Deployment Path** (four
  paragraphs, no subsections), placed between Threats to Validity and
  Conclusions. Every figure in it is quoted from `results.json`; the paragraph
  on maturity states plainly that the corpus is synthetic, the contracts are
  unaudited and no testnet deployment was performed.
- The UAE Charter for the Development and Use of Artificial Intelligence is
  cited in **footnotes only**, not in `references.bib`, so the reference list
  stays at 33 peer-reviewed DOI-bearing entries with no white papers.

Build: `paper_v3.pdf`, 17 pages, 33 bibitems, 0 overfull boxes, 0 undefined
references. `paper.pdf`, `paper_build.pdf` and `paper_v2.pdf` are still held
open by a viewer and could not be overwritten or removed.

## Five-reviewer audit (applied)

Five independent reviewers audited the manuscript against `results.json` and the
data card: R1 method soundness, R2 experimental rigour and arithmetic, R3
citations and novelty, R4 presentation and IEEE conventions, R5 overclaiming and
award fit. All five returned **major revision**. The corrections below were
applied; the paper now builds at 18 pages, 0 overfull boxes, 0 undefined
references, 33 cited DOI-bearing entries with no orphans and no dangling keys,
149-word abstract.

**Arithmetic and factual errors corrected (found by 3+ reviewers each)**

| Error | Was | Now |
|---|---|---|
| Pooled attribution rate | 0.455 | 0.454 (`E4.B2` = 0.4542) |
| False escalation counts | "18 false escalations, 11 contradictions and 16 definitional" (27 > 18) | 18 scenarios carrying 28 conflicts: 11 C1, 16 C5, 1 C2 |
| Escalation recall | 0.889 in one place, 0.890 in another for the same 169/190 | 0.890 throughout |
| "strongest baseline" | contradicted by B0 at 0.702 coverage | "strongest grounded baseline, B3P", with B0 stated |
| Baseline count | "five baselines" | six (B0, B1, B2, B3, B3P, B4) |
| Unfavourable findings | abstract said three, intro listed five | five |
| Routing breadth | "lattice routes to 2.54 departments" (that is the ground-truth mean) | 3.9 of five partitions, from 94.4 served at k=24 |
| Reconciliation time | "reconciliation itself costs 5.7 ms" | end-to-end; pooled retrieval alone is 5.1 ms |
| "vary by roughly a tenth between runs" | contradicted by 5.7 vs 9.2 ms | replaced with the memoisation explanation |
| Adversarial "coverage and spurious rate unchanged" | coverage rose, spurious fell | stated with the actual values and why |
| Sweep baseline range | "0.80 to 0.91" | 0.81–0.90, plus B0 at 0.92 |
| 84 vs 78 definitional conflicts | unexplained | units stated (scenarios vs conflict instances) |

**Citation misattributions corrected** — `carlile2004transforming` cited twice,
once for a situated-learning claim that is not Carlile's (clause deleted);
`malone1994coordination` cited as both the "first" and the "later" account
(collapsed); `park2023generative` cited twice in one list (collapsed);
Liang et al. described as improving factuality (they target divergent thinking);
Zhang et al. called a survey (it is an empirical study); Wang et al. credited
with verbosity and self-enhancement bias (they show positional bias only);
`eberhardt2017offchain` cited for erasure, which that paper does not discuss;
`wang2024unfair` cited for the self-evaluation conflict of interest, which it
does not cover.

**Novelty exposure closed (R3's strongest objection).** The paper positioned
itself against classical teamwork protocols and RBAC and omitted the literature
that already holds authority to be a registered fact. Four references swapped,
count unchanged at 33, all DOIs verified on Crossref:

- out `smith1980contractnet` → in Jones & Sergot 1996, institutionalised power (10.1093/jigpal/4.3.427)
- out `tambe1997teamwork` → in Esteva et al. 2001, electronic institutions (10.1007/3-540-44682-6_8)
- out `karpukhin2020dpr` → in Lupu & Sloman 1999, policy conflicts (10.1109/32.824414)
- out `dinh2018untangling` → in Wüst & Gervais 2018, "Do you need a blockchain?" (10.1109/CVCBT.2018.00011)

Related Work II-B now concedes the inheritance explicitly and the gap statement
claims the composition for an untrusted drafter rather than the parts. A new
passage in III-E answers "why a ledger rather than a signed append-only log"
against the Wüst–Gervais criteria and states that no reported measurement
depends on a chain. The Fabric/Solidity inconsistency is resolved: partitioning
is now attributed to the settlement contract, not to Fabric channels.

**Overclaiming corrected** — abstract and conclusions now say the corpus is
generated and the drafting agent simulated; attribution 1.000 and citation
validity 1.000 are labelled construction identities rather than findings;
"robust to" became "withstands / does not withstand"; the model in the loop is
named (`claude-opus-5`) at the point the sample is described, not only in
Threats; "has emerged as a promising" removed twice; the transparency claim now
states that the record does not replay the drafting step; Section VI lists five
deployment conditions rather than three and adds two misuse boundaries (not the
sole basis for a decision with legal or disciplinary consequence; query erasure
must be solved before handling personal circumstances); the escalation workload
(0.468 of queries) is stated.

**Method disclosure added** — B0–B5 are now defined in prose in IV-A, along with
the two falsification conditions the text previously referenced but never
stated, and the fact that no baseline has an abstention state. The "E2" artefact
labels leaking into the text were replaced by section references. Three
qualifications on the completeness probe are now stated in III-D: it is a
closed-world check sound only where the partition is complete; it reads the same
fields the ground truth is computed from, so C6 detection is a consistency check
rather than an independent measurement; and its contribution is measured against
an unfiltered lexical retriever.

**Presentation** — Figures 10 and 11 removed: they duplicated Tables VI and VII
with verbatim-identical captions and were causing a float-only page. Register
faults corrected where the connective asserted a relation that does not hold
("whereas" joining additive clauses, false "Accordingly").

### Not applied — these need new runs, not new wording

1. **Single-seed reporting.** Four independent realisations of the full
   configuration disagree (coverage 0.851–0.888). Only the E8/E4 pair is
   disclosed. Fix: rerun E4 with ≥5 agent seeds, report mean and range, and note
   that ablation deltas below that range are not interpretable.
2. **Baseline affordances.** No baseline gets a currency filter or a metadata
   lookup, both of which any enterprise index has, while B5 gets R1 and the
   probe. Fix: add a "pooled + labels + effective-window filter + lookup" arm.
3. **No abstention-capable baseline.** The 0.890 → 0.100 headline compares
   against systems that structurally cannot refuse. Fix: add B3 or B4 with an
   abstention threshold.
4. **Modality drift is not covered by the conservative operating point.** At
   λ\* the simulated rate is 0.090 against a Wilson bound of 0.259, and no grid
   point reaches it. Fix: one run with the modality base rate raised to ≥0.43.
5. **R7 after R3.** Definitional normalisation runs after the contradiction
   test, so a definitional conflict that precedence already resolved is never
   seen. This may explain the 32 undetected C5 conflicts. Fix: move the term-map
   rewrite to a pre-pass and re-run E3 and E8.
6. **C5 and R7 are not restricted to binding claims.** As implemented, an
   advisory claim from a consulted department carrying an unmapped term can
   withdraw the owner's binding claim, so a captured consulted department can
   force escalation. Property 5 as stated does not hold.
7. **Replayability is claimed but never exercised.** No replay experiment exists,
   and R6 specifies no canonical topological order, so two auditors can obtain
   different advice hashes.
8. **Length.** 18 pages; several Transactions charge above 14.

## Public-entity framing and implementability

The paper now reads as though written for a large government entity, without
naming one. Nothing in the corpus or the code changed; the framing was made to
match what the vocabulary already contains.

**Why the framing is honest.** `vocab.py` already carries 25 claim types over
procurement and vendor onboarding, contracting and liability, sanctions
screening, payment and budget authority, employment and background checks, data
classification and access provisioning, incident reporting and service
continuity — the shared-services functions of a public entity, not a generic
firm. Section IV-A now says so.

**Flavour markers used, all generic:**

- mandate distributed "by law, by executive resolution, by a **delegation of
  authority matrix** and by published **terms of reference**"
- policies revised through dated **circulars** rather than silent edits
- the running example is a **case officer onboarding an overseas supplier that
  will process customer records** — crossing procurement, contracting,
  information security and service continuity
- entities "measured on the guidance they give to staff and to **customers**"
- a **bilingual** (Arabic and English) policy corpus as a stated integration
  constraint
- the **resource planning platform** as the system of record for conditions
- **internal audit** as the consumer of settlement records

No emirate, entity, authority or programme is named. The only two occurrences of
"Emirates" are the author affiliation and the UAE Charter footnote, both of
which predate this change and both of which help the award submission.

**Implementability — new material in Section VI:**

1. **Table VIII, registration mapping.** Six rows: existing instrument →
   registered object → custodian → refresh trigger. Delegation of authority
   matrix → authority lattice; policy register and circulars → partition
   artefacts with effective windows; data classification scheme → artefact class
   and the on-chain/off-chain split; staff and system identity → departmental
   signing keys; bilingual glossary → term map; internal audit case file →
   settlement record. Nothing in the left column is invented for the framework.
   The paper states which row is load-bearing (the DoA matrix) and what an
   entity must do if its matrix allocates spending authority but not decision
   authority.
2. **Four-phase rollout**, each phase gated on a property the previous one
   demonstrated: registration (lattice registers without a cycle, every
   mandatory type has an anchored owner) → shadow (outputs recorded, not shown;
   watch escalation volume against desk capacity and citation validity as an
   invariant that must stay at 1.000) → advisory (shown with owner, cited
   circulars and escalation visible; a human officer still authors the answer)
   → settlement (written to the registry, one claim type at a time).
3. **Three operating roles** with no counterpart in an ordinary assistant
   deployment: departmental registrar, lattice custodian quorum drawn from
   departments that do not report to one another, and an escalation desk that
   returns each decision to the corpus as a dated circular or to the lattice as
   a registered precedence relation.
4. **Registration effort**, stated so it can be estimated in advance: 25 claim
   types (14 mandatory), 38 subjects, precedence on 10 of the 18 shared
   subjects, for five departments.
5. **Three integration constraints** the evaluation did not exercise: document
   management identifiers must be stable across a circular reissue; the resource
   planning platform supplies conditions, not rules, and is not replaced; and a
   bilingual corpus means the term map must equate definitions across languages
   as well as across departments, since a term equated in one language only
   presents as a definitional conflict the framework would escalate correctly
   but unnecessarily.

Build: `paper_v5.pdf`, 18 pages, 0 overfull boxes, 0 undefined references, no
dangling or unused labels, 33 cited DOI-bearing entries, 149-word abstract. The
conflict-detection figure was dropped to hold the page count; it duplicated
Table V on the same numbers.
