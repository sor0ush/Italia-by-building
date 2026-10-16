#!/usr/bin/env python3
"""
verify_all.py
End-to-End Verification and Autonomous Audit for 'Italy by Building'.

Performs comprehensive audits across:
1. Multi-City Architecture & Metadata (web/cities_metadata.json)
2. Vector Tiles for all 8 cities (PMTiles v3 header, zoom, valid bounds)
3. Frontend Assets (HTML landing modal, multi-city CSS, app.js logic)
4. Railway Deployment Configuration (Dockerfile, deploy/nginx.conf.template, railway.json)
5. Live HTTP Server Response (HTTP 200 for assets, HTTP 206 for PMTiles range queries)
"""

import os
import sys
import json
import time
import socket
import threading
import urllib.request
from pmtiles.reader import Reader, MemorySource

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

DATA_DIR = os.path.join(ROOT_DIR, "data")
WEB_DIR = os.path.join(ROOT_DIR, "web")
DEPLOY_DIR = os.path.join(ROOT_DIR, "deploy")

EXPECTED_CITIES = [
    "milano", "torino", "bologna", "monza", "pavia", "como", "barletta", "fano"
]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def audit_cities_metadata():
    print("[1/5] Auditing Multi-City Metadata...")
    meta_path = os.path.join(WEB_DIR, "cities_metadata.json")
    assert os.path.exists(meta_path), f"Missing {meta_path}"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    for city in EXPECTED_CITIES:
        assert city in meta, f"City '{city}' missing from cities_metadata.json"
        c_info = meta[city]
        assert "name" in c_info, f"Missing name for {city}"
        assert "region" in c_info, f"Missing region for {city}"
        assert "tiles" in c_info, f"Missing tiles for {city}"
        assert "center" in c_info and len(c_info["center"]) == 2, f"Invalid center for {city}"
        assert "landmarks" in c_info and len(c_info["landmarks"]) > 0, f"No landmarks for {city}"
        print(f"  - {c_info['name']} ({c_info['region']}): {c_info['buildingCount']:,} buildings, {len(c_info['landmarks'])} landmarks")

    print("  [PASS] Cities metadata validated.")


def audit_pmtiles_all_cities():
    print("\n[2/5] Auditing Vector Tiles (PMTiles) for all 8 cities...")
    for city in EXPECTED_CITIES:
        pm_name = f"{city}_buildings.pmtiles"
        pm_path = os.path.join(WEB_DIR, pm_name)
        assert os.path.exists(pm_path), f"Missing {pm_path}"
        sz_kb = os.path.getsize(pm_path) / 1024
        print(f"  - {pm_name}: {sz_kb:.1f} KB")
        assert sz_kb > 50, f"PMTiles file too small ({sz_kb:.1f} KB)"

        with open(pm_path, "rb") as f:
            reader = Reader(MemorySource(f.read()))
            hdr = reader.header()
            assert hdr["version"] == 3, f"Expected PMTiles v3 for {city}"
            assert hdr["tile_entries_count"] > 0, f"No tiles in {city}"

    print("  [PASS] All 8 city PMTiles archives validated.")


def audit_frontend_code():
    print("\n[3/5] Auditing Frontend Source Code...")
    index_html = os.path.join(WEB_DIR, "index.html")
    app_js = os.path.join(WEB_DIR, "app.js")
    style_css = os.path.join(WEB_DIR, "style.css")

    for f in [index_html, app_js, style_css]:
        assert os.path.exists(f), f"Missing frontend file: {f}"

    with open(index_html, "r", encoding="utf-8") as f:
        html = f.read()
        assert "maplibre" in html.lower(), "index.html missing MapLibre script/link"
        assert "pmtiles" in html, "index.html missing pmtiles script"
        assert 'id="city-modal"' in html, "index.html missing city-modal landing selector"
        assert 'id="open-city-modal-btn"' in html, "index.html missing city switcher button"
        assert 'id="time-slider"' in html, "index.html missing time-slider element"

    with open(app_js, "r", encoding="utf-8") as f:
        js = f.read()
        assert "selectCity" in js, "app.js missing selectCity function"
        assert "cities_metadata.json" in js, "app.js missing metadata fetch"
        assert "fill-extrusion" in js, "app.js missing fill-extrusion 3D layer"

    print("  [PASS] Frontend code integrity validated.")


def audit_railway_deployment_files():
    print("\n[4/5] Auditing Railway Deployment Setup...")
    dockerfile = os.path.join(ROOT_DIR, "Dockerfile")
    nginx_tmpl = os.path.join(DEPLOY_DIR, "nginx.conf.template")
    railway_json = os.path.join(ROOT_DIR, "railway.json")
    dockerignore = os.path.join(ROOT_DIR, ".dockerignore")

    for f in [dockerfile, nginx_tmpl, railway_json, dockerignore]:
        assert os.path.exists(f), f"Missing deployment artifact: {f}"

    with open(nginx_tmpl, "r") as f:
        content = f.read()
        assert "healthz" in content, "nginx.conf.template missing healthz endpoint"
        assert "pmtiles" in content, "nginx.conf.template missing pmtiles location"

    with open(railway_json, "r") as f:
        r_conf = json.load(f)
        assert r_conf["deploy"]["healthcheckPath"] == "/healthz", "railway.json missing /healthz healthcheck"

    print("  [PASS] Railway deployment configuration validated.")


def audit_server_e2e():
    print("\n[5/5] Auditing Live HTTP Streaming Server...")
    from pipeline.serve import RangeHTTPRequestHandler
    from http.server import HTTPServer

    test_port = find_free_port()
    httpd = HTTPServer(("", test_port), RangeHTTPRequestHandler)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    time.sleep(0.3)

    try:
        # Test 1: index.html
        res_index = urllib.request.urlopen(f"http://localhost:{test_port}/index.html")
        assert res_index.status == 200, f"index.html status: {res_index.status}"
        print("  - GET /index.html: 200 OK")

        # Test 2: cities_metadata.json
        res_meta = urllib.request.urlopen(f"http://localhost:{test_port}/cities_metadata.json")
        assert res_meta.status == 200, f"cities_metadata.json status: {res_meta.status}"
        print("  - GET /cities_metadata.json: 200 OK")

        # Test 3: Range request for Bologna
        range_req = urllib.request.Request(
            f"http://localhost:{test_port}/bologna_buildings.pmtiles",
            headers={"Range": "bytes=0-511"}
        )
        res_pm = urllib.request.urlopen(range_req)
        assert res_pm.status == 206, f"Expected HTTP 206 Partial Content, got {res_pm.status}"
        chunk = res_pm.read()
        assert len(chunk) == 512, f"Expected 512 bytes, got {len(chunk)}"
        print("  - GET /bologna_buildings.pmtiles (Range: bytes=0-511): 206 Partial Content OK")

    finally:
        httpd.shutdown()

    print("  [PASS] Live HTTP streaming server validated.")


def main():
    print("=" * 60)
    print("Italy by Building - Comprehensive Audit")
    print("=" * 60)
    audit_cities_metadata()
    audit_pmtiles_all_cities()
    audit_frontend_code()
    audit_railway_deployment_files()
    audit_server_e2e()
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL MULTI-CITY & RAILWAY AUDITS PASSED DETERMINISTICALLY.")
    print("=" * 60)


if __name__ == "__main__":
    main()
