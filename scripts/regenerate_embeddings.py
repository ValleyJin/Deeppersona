"""Regenerate data/attribute_embeddings.pkl from data/large_attributes.json.

The shipped pickle (both in this fork and upstream thzva/Deeppersona) is
truncated to exactly 6,815,744 bytes (~76% of its real size), causing
`pickle data was truncated`. Forensic analysis (see study.md §6.3) confirmed
the original was a {paths, embeddings} dict with `text-embedding-ada-002`
vectors (1,536-dim float64) for ~2,297 leaf paths.

This script recreates it from the source taxonomy. Pure caching artifact —
no API call is wasted on something we didn't already have the inputs for.

Run from repo root:
    .venv/bin/python scripts/regenerate_embeddings.py
"""
import json
import os
import pickle
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = REPO_ROOT / "data" / "large_attributes.json"
OUT_PATH = REPO_ROOT / "data" / "attribute_embeddings.pkl"
BACKUP_PATH = REPO_ROOT / "data" / "attribute_embeddings.pkl.broken"

MODEL = "text-embedding-ada-002"
BATCH_SIZE = 256


def flatten_paths(node, prefix=""):
    """Mirror of select_attributes.AttributeSelector._flatten_attributes.

    Leaf = empty dict or non-dict value. Path is dot-joined.
    """
    out = []
    if isinstance(node, dict):
        if not node:
            out.append(prefix)
        else:
            for k, v in node.items():
                child = f"{prefix}.{k}" if prefix else k
                out.extend(flatten_paths(v, child))
    else:
        out.append(prefix)
    return out


def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set in .env")

    print(f"Loading taxonomy from {TAXONOMY_PATH.relative_to(REPO_ROOT)}")
    with open(TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)

    paths = flatten_paths(taxonomy)
    print(f"Extracted {len(paths):,} leaf paths")

    if OUT_PATH.exists() and not BACKUP_PATH.exists():
        shutil.copy2(OUT_PATH, BACKUP_PATH)
        print(f"Backed up broken pickle → {BACKUP_PATH.relative_to(REPO_ROOT)}")

    client = OpenAI()
    all_embeddings = []
    t0 = time.time()

    for i in range(0, len(paths), BATCH_SIZE):
        batch = paths[i : i + BATCH_SIZE]
        resp = client.embeddings.create(model=MODEL, input=batch)
        all_embeddings.extend([d.embedding for d in resp.data])
        done = min(i + BATCH_SIZE, len(paths))
        print(f"  {done:,}/{len(paths):,} embedded  ({time.time()-t0:.1f}s)")

    embeddings = np.asarray(all_embeddings, dtype=np.float64)
    assert embeddings.shape == (len(paths), 1536), f"unexpected shape {embeddings.shape}"

    payload = {"attribute_paths": paths, "embeddings": embeddings}
    with open(OUT_PATH, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nWrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  paths: {len(paths):,}")
    print(f"  embedding shape: {embeddings.shape}, dtype: {embeddings.dtype}")
    print(f"  file size: {size_mb:.2f} MB")
    print(f"  total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
