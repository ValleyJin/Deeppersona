"""Sweep attribute_count to verify README's "~1MB per persona" claim.

Generates one profile each at counts [200, 300, 350] and reports sizes.
The canonical sweep in generate_multiple_profiles is [100, 150, 200, 250,
300, 350]; we skip the lower bands (already covered by the smoke test) to
keep API spend tight.

Run from repo root:
    .venv/bin/python scripts/test_attribute_count_sweep.py
"""
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "generate_user_profile"))

from generate_profile import generate_single_profile  # noqa: E402

COUNTS = [200, 300, 350]


def _count_filled_attrs(profile: dict) -> int:
    """Count leaf values (excluding metadata keys)."""
    skip = {"Generated At", "Profile Index", "Summary"}
    n = 0
    for k, v in profile.items():
        if k in skip:
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, dict):
                    n += len(v2)
                else:
                    n += 1
        else:
            n += 1
    return n


def main():
    out_dir = REPO_ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    results = []

    for i, count in enumerate(COUNTS):
        print(f"\n=== Generating profile with attribute_count={count} ===")
        t0 = time.time()
        profile = generate_single_profile(template=None, profile_index=i, attribute_count=count)
        elapsed = time.time() - t0

        if not profile:
            print(f"  FAILED")
            results.append((count, None, None, None, None))
            continue

        out_path = out_dir / f"sweep_profile_{count}.json"
        out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        size_kb = out_path.stat().st_size / 1024
        filled = _count_filled_attrs(profile)
        results.append((count, elapsed, size_kb, filled, len(profile)))
        print(f"  OK ({elapsed:.1f}s) — size {size_kb:.1f} KB, {filled} attrs across {len(profile)} sections")

    print("\n" + "=" * 70)
    print(f"{'count':>6} {'time(s)':>10} {'size(KB)':>10} {'attrs':>8} {'sections':>10} {'KB/attr':>10}")
    print("-" * 70)
    for count, elapsed, size_kb, filled, sections in results:
        if size_kb is None:
            print(f"{count:>6} FAILED")
            continue
        kb_per_attr = size_kb / filled if filled else 0
        print(f"{count:>6} {elapsed:>10.1f} {size_kb:>10.1f} {filled:>8} {sections:>10} {kb_per_attr:>10.2f}")
    print()
    print("README claim: ~1 MB (~1024 KB) per persona at the highest attribute counts")


if __name__ == "__main__":
    main()
