"""Generate a single user profile end-to-end as a smoke test.

Run from repo root:
    .venv/bin/python scripts/test_single_profile.py
"""
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "generate_user_profile"))

from generate_profile import generate_single_profile  # noqa: E402

ATTRIBUTE_COUNT = 100  # smallest count in the canonical sweep

if __name__ == "__main__":
    t0 = time.time()
    print(f"Generating one profile with {ATTRIBUTE_COUNT} attributes...")
    profile = generate_single_profile(template=None, profile_index=0, attribute_count=ATTRIBUTE_COUNT)
    elapsed = time.time() - t0

    if not profile:
        print("FAILED: generator returned empty profile")
        sys.exit(1)

    out_dir = REPO_ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "smoke_test_profile.json"
    out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK ({elapsed:.1f}s) — saved to {out_path}")
    print(f"  top-level keys: {list(profile.keys())[:10]}...")
    print(f"  size: {out_path.stat().st_size:,} bytes")
