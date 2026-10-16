#!/usr/bin/env python3
"""
verify_pipeline.py
Deterministic Sanity & Quality Checks for Processed Spatial Data.
"""

import os
import sys
import json
import pyogrio

PROCESSED_GEOJSON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "milano_buildings.geojson"))


def verify():
    print("=" * 60)
    print("Milano by Building - Pipeline Verification")
    print("=" * 60)

    # 1. File existence and size check
    if not os.path.exists(PROCESSED_GEOJSON):
        print(f"[FAIL] Missing {PROCESSED_GEOJSON}")
        sys.exit(1)

    file_size_mb = os.path.getsize(PROCESSED_GEOJSON) / (1024 * 1024)
    print(f"[OK] Found processed GeoJSON: {file_size_mb:.2f} MB")
    if file_size_mb < 20:
        print(f"[FAIL] File too small ({file_size_mb:.2f} MB), expected > 20 MB")
        sys.exit(1)

    # 2. Inspect with pyogrio
    info = pyogrio.read_info(PROCESSED_GEOJSON)
    features_count = info["features"]
    print(f"[OK] Total features: {features_count:,}")
    if features_count < 50000:
        print(f"[FAIL] Feature count ({features_count}) lower than expected 50,000")
        sys.exit(1)

    fields = info["fields"]
    print(f"[OK] Field schema: {fields}")
    for required_field in ["height", "year", "id"]:
        if required_field not in fields:
            print(f"[FAIL] Required field '{required_field}' missing from dataset")
            sys.exit(1)

    # 3. Sample attribute checks
    sample = pyogrio.read_dataframe(PROCESSED_GEOJSON, max_features=1000)
    if (sample["height"] <= 0).any():
        print("[FAIL] Found negative or zero heights")
        sys.exit(1)
    if (sample["year"] < 300).any() or (sample["year"] > 2026).any():
        print("[FAIL] Found invalid years outside range [300, 2026]")
        sys.exit(1)

    print(f"[OK] Sample heights: min={sample['height'].min():.1f}m, max={sample['height'].max():.1f}m, mean={sample['height'].mean():.1f}m")
    print(f"[OK] Sample years: min={sample['year'].min()}, max={sample['year'].max()}, median={sample['year'].median():.0f}")
    print("\n[SUCCESS] Pipeline spatial data verification passed deterministically.")


if __name__ == "__main__":
    verify()
