#!/usr/bin/env python3
"""
build_italian_cities.py
Fetches and builds 3D building PMTiles datasets for requested Italian cities:
- Monza (Lombardia)
- Pavia (Lombardia)
- Como (Lombardia)
- Torino (Piemonte)
- Bologna (Emilia-Romagna)
- Barletta (Puglia)
- Fano (Marche)
"""

import os
import sys
import math
import shutil
import subprocess
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import numpy as np
import pyogrio
import geopandas as gpd
from shapely.geometry import Polygon, Point

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
TILES_DIR = os.path.join(DATA_DIR, "tiles")
WEB_DIR = os.path.join(ROOT_DIR, "web")

CITIES_CONFIG = {
    "monza": {
        "title": "Monza",
        "region": "Lombardia",
        "center": [9.2744, 45.5845],
        "zoom": 15.2,
        "pitch": 58,
        "bearing": -20,
        "bboxes": [
            (9.250, 45.565, 9.280, 45.585), # San Fruttuoso, Triante, Centro Ovest
            (9.250, 45.585, 9.280, 45.605), # San Biagio, Villa Reale
            (9.280, 45.565, 9.310, 45.585), # Cederna, Sobborghi
            (9.280, 45.585, 9.310, 45.605), # Parco di Monza Sud
        ],
        "landmarks": [
            (9.2747, 45.5833, 80, 1300, "Duomo di Monza"),
            (9.2736, 45.5839, 60, 1293, "Arengario di Monza"),
            (9.2764, 45.5925, 120, 1777, "Villa Reale di Monza"),
            (9.2740, 45.5855, 60, 1840, "Ponte dei Leoni"),
            (9.2800, 45.6150, 150, 1922, "Autodromo Nazionale Monza")
        ]
    },
    "pavia": {
        "title": "Pavia",
        "region": "Lombardia",
        "center": [9.1580, 45.1890],
        "zoom": 15.2,
        "pitch": 56,
        "bearing": 15,
        "bboxes": [
            (9.120, 45.165, 9.150, 45.185), # San Lanfranco, Borgo Ovest
            (9.120, 45.185, 9.150, 45.205), # Città Giardino, Policlinico San Matteo, Polo Cravino
            (9.120, 45.205, 9.150, 45.225), # Mirabello Ovest
            (9.150, 45.165, 9.180, 45.185), # Centro Storico, Borgo Ticino, San Michele
            (9.150, 45.185, 9.180, 45.205), # Castello Visconteo, San Pietro in Ciel d'Oro, Torretta Ovest
            (9.150, 45.205, 9.180, 45.225), # Mirabello Est, Campari
            (9.180, 45.165, 9.210, 45.185), # San Pietro in Verzolo, Montebolone
            (9.180, 45.185, 9.210, 45.205), # Vallone, Fossarmato
            (9.180, 45.205, 9.210, 45.225), # Torretta Est
        ],
        "landmarks": [
            (9.1517, 45.1819, 80, 1354, "Ponte Coperto"),
            (9.1578, 45.1908, 120, 1360, "Castello Visconteo"),
            (9.1528, 45.1856, 90, 1488, "Duomo di Pavia"),
            (9.1534, 45.1925, 80, 1132, "Basilica di San Pietro in Ciel d'Oro"),
            (9.1611, 45.1822, 80, 1155, "Basilica di San Michele Maggiore"),
            (9.1564, 45.1867, 90, 1361, "Università degli Studi di Pavia"),
            (9.1460, 45.1990, 150, 1932, "Policlinico San Matteo"),
            (9.1405, 45.2015, 80, 1965, "Città Giardino"),
            (9.1780, 45.2020, 90, 1968, "Vallone")
        ]
    },
    "como": {
        "title": "Como",
        "region": "Lombardia",
        "center": [9.0852, 45.8081],
        "zoom": 15.2,
        "pitch": 58,
        "bearing": -30,
        "bboxes": [
            (9.065, 45.795, 9.095, 45.810), # Camerlata, Borghi Ovest
            (9.065, 45.810, 9.095, 45.825), # Centro Storico, Villa Olmo
            (9.095, 45.795, 9.120, 45.810), # Borghi Est, Valduce
            (9.095, 45.810, 9.120, 45.825), # Funicolare, Brunate pendici
        ],
        "landmarks": [
            (9.0833, 45.8117, 90, 1396, "Duomo di Como"),
            (9.0839, 45.8114, 60, 1215, "Broletto di Como"),
            (9.0756, 45.8133, 70, 1927, "Tempio Voltiano"),
            (9.0864, 45.8111, 70, 1936, "Casa del Fascio (G. Terragni)"),
            (9.0667, 45.8206, 120, 1797, "Villa Olmo"),
            (9.0911, 45.8189, 70, 1894, "Funicolare Como-Brunate")
        ]
    },
    "torino": {
        "title": "Torino",
        "region": "Piemonte",
        "center": [7.6869, 45.0703],
        "zoom": 15.0,
        "pitch": 60,
        "bearing": -15,
        "bboxes": [
            (7.660, 45.055, 7.685, 45.070), # Crocetta, Porta Nuova
            (7.685, 45.055, 7.710, 45.070), # San Salvario, Valentino
            (7.660, 45.070, 7.685, 45.085), # Quadrilatero, Porta Susa
            (7.685, 45.070, 7.710, 45.085), # Vanchiglia, Mole Antonelliana
        ],
        "landmarks": [
            (7.6931, 45.0689, 80, 1889, "Mole Antonelliana"),
            (7.6858, 45.0731, 100, 1646, "Palazzo Reale di Torino"),
            (7.6864, 45.0711, 80, 1348, "Palazzo Madama"),
            (7.6828, 45.0678, 90, 1638, "Piazza San Carlo"),
            (7.6842, 45.0733, 70, 1498, "Duomo di San Giovanni Battista"),
            (7.6653, 45.0664, 90, 2015, "Grattacielo Intesa Sanpaolo (Renzo Piano)"),
            (7.6650, 45.0319, 120, 1923, "Lingotto")
        ]
    },
    "bologna": {
        "title": "Bologna",
        "region": "Emilia-Romagna",
        "center": [11.3426, 44.4949],
        "zoom": 15.0,
        "pitch": 58,
        "bearing": 25,
        "bboxes": [
            (11.330, 44.482, 11.345, 44.492), # Santo Stefano, Galvani
            (11.345, 44.482, 11.360, 44.492), # San Giovanni in Monte, Baraccano
            (11.330, 44.492, 11.345, 44.502), # Piazza Maggiore, Pratello, Stazione
            (11.345, 44.492, 11.360, 44.502), # Università, San Donato, Montagnola
            (11.315, 44.485, 11.330, 44.495), # Porta Saragozza, Sant'Isaia
        ],
        "landmarks": [
            (11.3467, 44.4942, 70, 1109, "Due Torri (Asinelli e Garisenda)"),
            (11.3431, 44.4931, 90, 1390, "Basilica di San Petronio"),
            (11.3433, 44.4939, 80, 1200, "Piazza Maggiore"),
            (11.3422, 44.4939, 70, 1336, "Palazzo d'Accursio"),
            (11.3436, 44.4922, 60, 1563, "Palazzo dell'Archiginnasio"),
            (11.2961, 44.4792, 100, 1765, "Santuario Madonna di San Luca")
        ]
    },
    "barletta": {
        "title": "Barletta",
        "region": "Puglia",
        "center": [16.2800, 41.3180],
        "zoom": 15.0,
        "pitch": 55,
        "bearing": 30,
        "bboxes": [
            (16.240, 41.290, 16.265, 41.305),
            (16.240, 41.305, 16.265, 41.320), # Barberini, Borgovilla Ovest
            (16.240, 41.320, 16.265, 41.335), # Settefrati Ovest, Zona Industriale
            (16.265, 41.290, 16.290, 41.305), # Zona 167, Medaglie d'Oro, Parco dell'Umanità
            (16.265, 41.305, 16.290, 41.320), # Borgovilla, Patalini, Stazione
            (16.265, 41.320, 16.290, 41.335), # Centro Storico, Castello Svevo, Cattedrale, Porto
            (16.290, 41.290, 16.315, 41.305), # Santuario Madonna dello Sterpeto
            (16.290, 41.305, 16.315, 41.320), # Patalini Est, Litoranea Levante
            (16.290, 41.320, 16.315, 41.335), # Porto Est
        ],
        "landmarks": [
            (16.2892, 41.3203, 100, 1202, "Castello Svevo di Barletta"),
            (16.2858, 41.3200, 80, 1126, "Cattedrale di Santa Maria Maggiore"),
            (16.2828, 41.3183, 50, 450, "Colosso di Barletta (Eraclio)"),
            (16.2847, 41.3192, 50, 1503, "Cantina della Disfida"),
            (16.2831, 41.3186, 60, 1100, "Basilica del Santo Sepolcro"),
            (16.2715, 41.3135, 80, 1920, "Borgovilla"),
            (16.2785, 41.3030, 90, 1985, "Zona 167 - Parco dell'Umanità"),
            (16.2790, 41.3110, 80, 1970, "Patalini")
        ]
    },
    "fano": {
        "title": "Fano",
        "region": "Marche",
        "center": [13.0182, 43.8436],
        "zoom": 15.0,
        "pitch": 55,
        "bearing": -15,
        "bboxes": [
            (12.990, 43.825, 13.020, 43.845), # Fano Ovest, Bellocchi
            (12.990, 43.845, 13.020, 43.865), # Vallato, Fano Nord
            (13.020, 43.825, 13.050, 43.845), # Sassonia, Porto, San Lazzaro
            (13.020, 43.845, 13.050, 43.865), # Lido, Litoranea Nord
        ],
        "landmarks": [
            (13.0139, 43.8431, 50, 9, "Arco d'Augusto (9 d.C.)"),
            (13.0142, 43.8428, 60, 9, "Mura Romane Augustee"),
            (13.0194, 43.8458, 90, 1452, "Rocca Malatestiana"),
            (13.0161, 43.8428, 70, 1140, "Cattedrale di Santa Maria Assunta"),
            (13.0178, 43.8439, 60, 1299, "Palazzo del Podestà"),
            (13.0189, 43.8419, 70, 1552, "Bastione del Sangallo")
        ]
    }
}


def parse_start_year(val_str: str) -> int | None:
    if not val_str:
        return None
    val_str = str(val_str).strip()
    # Check century e.g. "C12", "12th century"
    if "century" in val_str.lower() or "secolo" in val_str.lower():
        parts = [int(s) for s in val_str.split() if s.isdigit()]
        if parts:
            return (parts[0] - 1) * 100 + 50
    # Clean non-digits
    digits = "".join(ch if (ch.isdigit() or ch == "-") else " " for ch in val_str).split()
    for d in digits:
        try:
            yr = int(d)
            if 0 <= yr <= 2026:
                return yr
        except ValueError:
            continue
    return None


def fetch_osm_buildings(city_key, cfg):
    print(f"\n--- Fetching OSM data for {cfg['title']} ---")
    min_lon = min(b[0] for b in cfg["bboxes"])
    min_lat = min(b[1] for b in cfg["bboxes"])
    max_lon = max(b[2] for b in cfg["bboxes"])
    max_lat = max(b[3] for b in cfg["bboxes"])

    query = f"""[out:json][timeout:90];
(
  way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out body;
>;
out skel qt;"""

    overpass_endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter"
    ]

    for ep in overpass_endpoints:
        print(f"  Querying Overpass ({ep}) for bbox ({min_lat:.3f}, {min_lon:.3f}, {max_lat:.3f}, {max_lon:.3f})...")
        try:
            req = urllib.request.Request(
                ep,
                data=f"data={urllib.parse.quote(query)}".encode("utf-8"),
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ItalyInBuilding/1.0"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
            nodes = {}
            raw_ways = []
            for el in data.get("elements", []):
                if el["type"] == "node":
                    nodes[el["id"]] = (float(el["lon"]), float(el["lat"]))
                elif el["type"] == "way":
                    raw_ways.append(el)
            all_ways = []
            for w in raw_ways:
                wid = w["id"]
                tags = w.get("tags", {})
                nds = w.get("nodes", [])
                coords = [nodes[nid] for nid in nds if nid in nodes]
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    all_ways.append({"id": wid, "tags": tags, "coords": coords})
            if all_ways:
                print(f"  [SUCCESS] Parsed {len(all_ways):,} unique building polygons via Overpass.")
                return all_ways
        except Exception as e:
            print(f"  [WARN] Overpass {ep} query failed: {e}")

    # Fallback to OSM API bbox-by-bbox if needed
    print("  Falling back to OSM API map chunks...")
    all_ways = {}
    nodes = {}
    for bbox in cfg["bboxes"]:
        min_lon, min_lat, max_lon, max_lat = bbox
        url = f"https://api.openstreetmap.org/api/0.6/map?bbox={min_lon},{min_lat},{max_lon},{max_lat}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ItalyInBuilding/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for n in root.findall("node"):
                nodes[n.get("id")] = (float(n.get("lon")), float(n.get("lat")))
            for w in root.findall("way"):
                wid = w.get("id")
                tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
                if "building" in tags and wid not in all_ways:
                    nds = [nd.get("ref") for nd in w.findall("nd")]
                    coords = [nodes[ref] for ref in nds if ref in nodes]
                    if len(coords) >= 4 and coords[0] == coords[-1]:
                        all_ways[wid] = {"id": wid, "tags": tags, "coords": coords}
            time.sleep(1.0)
        except Exception as e:
            print(f"  [WARN] Failed OSM chunk {bbox}: {e}")

    print(f"  Parsed {len(all_ways):,} unique building polygons via OSM chunks.")
    return list(all_ways.values())


def process_city_dataset(city_key, cfg, raw_buildings):
    records = []
    center_lon, center_lat = cfg["center"]
    rng = np.random.default_rng(seed=hash(city_key) % 1000000)

    for i, b in enumerate(raw_buildings):
        tags = b["tags"]
        coords = b["coords"]
        poly = Polygon(coords)
        if not poly.is_valid or poly.is_empty:
            continue

        c_pt = poly.centroid
        dist_center_m = math.sqrt(
            ((c_pt.x - center_lon) * 111320 * math.cos(math.radians(center_lat)))**2 +
            ((c_pt.y - center_lat) * 111320)**2
        )

        # Height determination
        b_type = tags.get("building", "").lower()
        height = None
        if "height" in tags:
            try:
                height = float(tags["height"].replace("m", "").replace(",", ".").strip())
            except ValueError:
                pass
        if not height and "building:levels" in tags:
            try:
                lvls = float(tags["building:levels"].replace(",", ".").strip())
                height = lvls * 3.3
            except ValueError:
                pass
        if not height:
            if b_type in ["cathedral", "church", "basilica"]:
                height = float(rng.uniform(22.0, 36.0))
            elif b_type in ["tower", "bell_tower"]:
                height = float(rng.uniform(35.0, 60.0))
            elif b_type in ["civic", "public", "castle"]:
                height = float(rng.uniform(16.0, 26.0))
            else:
                # Historic center buildings usually 3-5 floors (10-18m)
                height = float(rng.uniform(10.5, 17.5))

        # Year determination
        year = parse_start_year(tags.get("start_date"))
        b_name = tags.get("name", "")

        # Landmark check
        matched_landmark = False
        for l_lon, l_lat, rad_m, l_year, l_name in cfg.get("landmarks", []):
            d_m = math.sqrt(
                ((c_pt.x - l_lon) * 111320 * math.cos(math.radians(l_lat)))**2 +
                ((c_pt.y - l_lat) * 111320)**2
            )
            if d_m <= rad_m:
                year = l_year
                b_name = l_name
                matched_landmark = True
                break

        # Distance from historical center heuristic if year unknown
        if not year:
            if dist_center_m < 350:
                # Medieval / Renaissance core
                year = int(rng.choice([1200, 1350, 1480, 1550, 1620, 1750], p=[0.1, 0.15, 0.25, 0.25, 0.15, 0.1]))
            elif dist_center_m < 750:
                # 18th - 19th century ring
                year = int(rng.integers(1800, 1920))
            elif dist_center_m < 1500:
                # Early to mid 20th century expansion
                year = int(rng.integers(1925, 1975))
            else:
                # Modern outer developments
                year = int(rng.integers(1975, 2022))

        records.append({
            "id": i + 1,
            "height": round(float(height), 1),
            "year": int(year),
            "name": str(b_name),
            "geometry": poly
        })

    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    geojson_path = os.path.join(PROCESSED_DIR, f"{city_key}_buildings.geojson")
    pyogrio.write_dataframe(gdf, geojson_path, driver="GeoJSON")
    print(f"  Saved {len(gdf):,} features to {geojson_path}")

    # Generate PMTiles using Tippecanoe with clean relative paths to avoid metadata leakage
    rel_pmtiles_path = os.path.relpath(os.path.join(TILES_DIR, f"{city_key}_buildings.pmtiles"), ROOT_DIR)
    rel_geojson_path = os.path.relpath(geojson_path, ROOT_DIR)
    web_pmtiles_path = os.path.join(WEB_DIR, f"{city_key}_buildings.pmtiles")
    print(f"  Generating PMTiles via Tippecanoe -> {rel_pmtiles_path}...")
    cmd = [
        "tippecanoe",
        f"--output={rel_pmtiles_path}",
        "--layer=buildings",
        f"--name={cfg['title']} Buildings",
        "--attribution=OpenStreetMap contributors",
        "--minimum-zoom=12",
        "--maximum-zoom=16",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
        rel_geojson_path
    ]
    subprocess.run(cmd, cwd=ROOT_DIR, check=True, stdout=subprocess.DEVNULL)
    shutil.copy2(os.path.join(ROOT_DIR, rel_pmtiles_path), web_pmtiles_path)
    print(f"  [DONE] {city_key}_buildings.pmtiles created ({os.path.getsize(web_pmtiles_path) / 1024:.1f} KB)")


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(TILES_DIR, exist_ok=True)
    os.makedirs(WEB_DIR, exist_ok=True)

    print("=" * 60)
    print("Italy by Building - Multi-City Pipeline Builder")
    print("=" * 60)

    for city_key, cfg in CITIES_CONFIG.items():
        raw_bldgs = fetch_osm_buildings(city_key, cfg)
        if raw_bldgs:
            process_city_dataset(city_key, cfg, raw_bldgs)

    print("\n[SUCCESS] All requested Italian cities successfully built.")


if __name__ == "__main__":
    main()
