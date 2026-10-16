#!/usr/bin/env python3
"""
01_fetch_data.py
Automated Open Data Acquisition for 'Milano by Building'.

Fetches:
1. Milano DBT 2020 3D volumetric buildings ('UN_VOL') via Range-request extraction.
2. Milano ISTAT Census tracts 2011 ('sezioni_censimento_2011.geojson').
3. Milano ISTAT Building construction epoch distribution ('ds384_edifici_censimento_2011.csv').
4. Regione Lombardia / Comune di Milano CENED+2 Energy Certificates dataset.
"""

import os
import sys
import io
import zipfile
import urllib.request
import requests

DATA_RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
DBT_ZIP_URL = "https://gisportal.comune.milano.it/download/area_download/SIT/DBT2020/DBT_2020.zip"
DBT_ZIP_SIZE = 596533009

SEZIONI_GEOJSON_URL = "https://dati.comune.milano.it/dataset/fc445f33-c94a-4332-9555-5b7568a44192/resource/d75587b9-2d4d-4a32-b297-d08635a88b79/download/sezioni_censimento_2011.geojson"
CENSUS_EPOCH_CSV_URL = "https://dati.comune.milano.it/dataset/a85c84f8-8ca3-49ab-ac3c-b0bb86e0af18/resource/44b322c5-11af-4111-ac99-100d09b754f1/download/ds384_popolazione_alloggi_edifici_caratteristiche_sezione_censimento_2011_.csv"
CENED_ZIP_URL = "https://dati.comune.milano.it/dataset/bad3edcf-18ca-49af-9396-1422f70d3f68/resource/23843535-0b22-4f33-b2de-ea06a3216da3/download/ds623_database_cened2__certifi_xzax-ddqm_csv.zip"


class RemoteZipFile(io.RawIOBase):
    """File-like reader that streams only requested slices of a large remote zip."""
    def __init__(self, url, size):
        self.url = url
        self.size = size
        self.pos = 0

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        return self.pos

    def tell(self):
        return self.pos

    def seekable(self):
        return True

    def read(self, size=-1):
        if size == -1 or self.pos + size > self.size:
            size = self.size - self.pos
        if size <= 0:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + size - 1}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        self.pos += len(data)
        return data


def download_file(url: str, dest_path: str):
    """Downloads a file if not already present."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        print(f"[SKIP] Already exists: {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return
    print(f"[FETCH] Downloading {url} -> {os.path.basename(dest_path)}...")
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"[DONE] Saved {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")


def fetch_dbt_layers():
    """Extracts required UN_VOL and EDIFC shapefiles directly from the DBT zip using HTTP Range."""
    required = ["UN_VOL.shp", "UN_VOL.dbf", "UN_VOL.prj", "UN_VOL.shx"]
    missing = [f for f in required if not os.path.exists(os.path.join(DATA_RAW_DIR, f)) or os.path.getsize(os.path.join(DATA_RAW_DIR, f)) < 1000]

    if not missing:
        print(f"[SKIP] All DBT volumetric layers already present in {DATA_RAW_DIR}")
        return

    print(f"[FETCH] Extracting DBT layers {missing} from remote zip...")
    rzf = RemoteZipFile(DBT_ZIP_URL, DBT_ZIP_SIZE)
    zf = zipfile.ZipFile(rzf)

    for member in zf.namelist():
        base = os.path.basename(member)
        if base in missing or any(base.startswith(m) for m in ["UN_VOL", "EDIFC_CR_EDF_IS"]):
            target = os.path.join(DATA_RAW_DIR, base)
            print(f"  Extracting {base} -> {target}...")
            with zf.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
            print(f"  Extracted {base} ({os.path.getsize(target)} bytes)")


def main():
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    print("=" * 60)
    print("Milano by Building - Step 01: Data Ingestion")
    print("=" * 60)

    # 1. DBT 2020 Building Volumes
    fetch_dbt_layers()

    # 2. Census Sections Spatial Boundaries
    download_file(SEZIONI_GEOJSON_URL, os.path.join(DATA_RAW_DIR, "sezioni_censimento_2011.geojson"))

    # 3. Census Epoch Distribution Data
    download_file(CENSUS_EPOCH_CSV_URL, os.path.join(DATA_RAW_DIR, "ds384_edifici_censimento_2011.csv"))

    # 4. CENED+2 Energy Certificates
    download_file(CENED_ZIP_URL, os.path.join(DATA_RAW_DIR, "cened_milano.zip"))

    # Verification
    print("\n--- Verifying Ingestion Artifacts ---")
    essential_files = [
        "UN_VOL.shp",
        "UN_VOL.dbf",
        "UN_VOL.prj",
        "sezioni_censimento_2011.geojson",
        "ds384_edifici_censimento_2011.csv",
        "cened_milano.zip"
    ]
    for filename in essential_files:
        path = os.path.join(DATA_RAW_DIR, filename)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print(f"[FAIL] Missing or empty: {filename}")
            sys.exit(1)
        print(f"[OK] {filename} ({os.path.getsize(path):,} bytes)")

    print("\n[SUCCESS] Node 02 Data Ingestion verified.")


if __name__ == "__main__":
    main()
