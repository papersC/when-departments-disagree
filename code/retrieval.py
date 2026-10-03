"""Lexical retrieval over departmental partitions and over a pooled index.

BM25 with the standard parameterisation. The retriever is deliberately
identical for every system under comparison, so that differences in the
measured outcome are attributable to what happens after retrieval rather than
to the retriever itself.
"""

import math
from collections import Counter, defaultdict


def tokenise(text):
    return [w for w in text.lower().replace("_", " ").split() if w]


class BM25:
    def __init__(self, artefacts, k1=1.2, b=0.75):
        self.artefacts = list(artefacts)
        self.k1, self.b = k1, b
        self.docs = [tokenise(a["text"]) for a in self.artefacts]
        self.len = [len(d) for d in self.docs]
        self.avgdl = (sum(self.len) / len(self.len)) if self.len else 0.0
        self.tf = [Counter(d) for d in self.docs]
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query, k=8):
        q = tokenise(query)
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            dl = self.len[i] or 1
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                s += self.idf.get(term, 0.0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scores.append((s, i))
        scores.sort(key=lambda x: (-x[0], x[1]))
        return [(self.artefacts[i], s) for s, i in scores[:k]]


class Indexes:
    """Retrieval is deterministic in the query, so results are memoised. The
    cache changes nothing about what is retrieved; it only avoids repeating the
    same search across the failure rate sweep."""

    def __init__(self, corpus):
        self.per_dept = {d: BM25(v) for d, v in corpus.by_dept.items()}
        self.pooled = BM25(corpus.artefacts)
        self._cache = {}

    def dept(self, d, query, k):
        key = (d, query, k)
        if d not in self.per_dept:
            return []          # a department with no anchored partition yet
        hit = self._cache.get(key)
        if hit is None:
            hit = self.per_dept[d].search(query, k)
            self._cache[key] = hit
        return hit

    def pool(self, query, k):
        key = ("__POOL__", query, k)
        hit = self._cache.get(key)
        if hit is None:
            hit = self.pooled.search(query, k)
            self._cache[key] = hit
        return hit


def type_focus(situation, types):
    """The query issued to a partition names the situation and the claim types
    the lattice routed to that partition."""
    return situation + " " + " ".join(t.replace("_", " ") for t in types)
