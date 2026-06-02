"""Post-hoc clustering of Tier 3 free-text findings.

Greedy single-link clustering over TF-IDF cosine similarity on a
character-3-gram representation. Pure-Python — no sklearn / sentence-
transformers dependency. Good enough for ~250 short strings: that's the
target sample size for the Tier 3 discovery pass and the corpus is too
small for embeddings to dominate.

Outputs a Markdown digest:

    # Tier 3 Discovery Clusters

    ## Cluster 1 — n findings
    Representative: "year column has 4-digit and 2-digit values mixed"
      - file_001.csv: "year column has 4-digit and 2-digit values mixed"
      - file_023.csv: "mixed 2- and 4-digit year format"
      ...

This file feeds v2 taxonomy decisions; the human reviewer decides which
clusters become new flags.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


_TOK_RE = re.compile(r"[a-zA-Z]+")
_NGRAM_N = 3
_SIMILARITY_THRESHOLD = 0.30  # cosine similarity for single-link clustering
_TOP_CLUSTERS = 20


def _normalise(text: str) -> str:
    return " ".join(_TOK_RE.findall(text.lower()))


def _ngrams(text: str, n: int = _NGRAM_N) -> Counter:
    text = _normalise(text)
    if len(text) < n:
        return Counter([text])
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


def _tfidf(documents: list[Counter]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """Return per-doc TF·IDF vectors plus the IDF table."""
    df: Counter = Counter()
    for doc in documents:
        for term in doc:
            df[term] += 1
    n_docs = max(len(documents), 1)
    idf = {term: math.log((n_docs + 1) / (1 + df_t)) + 1.0 for term, df_t in df.items()}
    vectors: list[dict[str, float]] = []
    for doc in documents:
        total = sum(doc.values()) or 1
        vec = {term: (cnt / total) * idf.get(term, 0.0) for term, cnt in doc.items()}
        vectors.append(vec)
    return vectors, idf


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _greedy_cluster(items: list[tuple[str, str]]) -> list[list[int]]:
    """Greedy single-link clustering. Returns list of clusters of indices."""
    if not items:
        return []
    docs = [_ngrams(text) for _, text in items]
    vectors, _ = _tfidf(docs)

    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _cosine(vectors[i], vectors[j]) >= _SIMILARITY_THRESHOLD:
                union(i, j)

    clusters_map: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        clusters_map[find(i)].append(i)
    return [c for c in clusters_map.values()]


def _representative(cluster: list[int], items: list[tuple[str, str]]) -> str:
    """Choose the medoid: shortest text whose ngrams are most central."""
    if not cluster:
        return ""
    if len(cluster) == 1:
        return items[cluster[0]][1]
    docs = [_ngrams(items[i][1]) for i in cluster]
    vectors, _ = _tfidf(docs)
    best_idx = cluster[0]
    best_score = -1.0
    for k, doc_idx in enumerate(cluster):
        score = sum(_cosine(vectors[k], vectors[m]) for m in range(len(cluster)) if m != k)
        if score > best_score:
            best_score = score
            best_idx = doc_idx
    return items[best_idx][1]


def run_clustering(discovery_dir: Path, out_md: Path) -> Path | None:
    """Read all ``*_discovery.json`` and write the markdown digest."""
    if not discovery_dir.is_dir():
        return None
    items: list[tuple[str, str]] = []  # (source_filename, finding)
    for path in sorted(discovery_dir.glob("*_discovery.json")):
        try:
            with open(path) as f:
                rec = json.load(f)
        except Exception:
            continue
        src = rec.get("source_filename") or path.stem
        for finding in rec.get("findings") or []:
            text = str(finding).strip()
            if text:
                items.append((src, text))

    if not items:
        return None

    clusters = _greedy_cluster(items)
    clusters.sort(key=len, reverse=True)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w") as f:
        f.write(
            f"# Tier 3 Discovery Clusters\n\n"
            f"Total findings: {len(items)} across "
            f"{len(set(s for s, _ in items))} files. "
            f"Cluster threshold (cosine, 3-grams): "
            f"{_SIMILARITY_THRESHOLD}.\n\n"
        )
        for idx, cluster in enumerate(clusters[:_TOP_CLUSTERS], start=1):
            rep = _representative(cluster, items)
            f.write(f"## Cluster {idx} — {len(cluster)} findings\n\n")
            f.write(f"**Representative:** {rep}\n\n")
            for member in cluster:
                src, text = items[member]
                f.write(f"  - `{src}`: {text}\n")
            f.write("\n")

        if len(clusters) > _TOP_CLUSTERS:
            f.write(
                f"…and {len(clusters) - _TOP_CLUSTERS} more singleton/small "
                "clusters omitted.\n"
            )

    return out_md
