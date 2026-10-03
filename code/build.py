"""Corpus construction and ledger anchoring, shared by every experiment."""

import random
from collections import defaultdict

from corpus import Corpus, SEED
from ledger import Keyring, Ledger
from lattice import default_lattice
from retrieval import Indexes
from systems import Runner


def build(seed=SEED, n_scenarios=400, departments=None, k=8):
    corpus = Corpus(seed=seed, n_scenarios=n_scenarios, departments=departments)
    keyring = Keyring(corpus.departments)
    ledger = Ledger(keyring)
    epochs = defaultdict(lambda: defaultdict(list))
    for a in corpus.artefacts:
        epochs[a["effective_from"]][a["dept"]].append(a)
    for epoch in sorted(epochs):
        for dept, arts in sorted(epochs[epoch].items()):
            ledger.anchor(dept, epoch, arts)
        ledger.commit_epoch(epoch, corpus.departments)
    lattice = default_lattice()
    ledger.register_lattice(lattice.snapshot())
    indexes = Indexes(corpus)
    runner = Runner(corpus, ledger, indexes, lattice, k=k)
    return corpus, ledger, lattice, indexes, runner
