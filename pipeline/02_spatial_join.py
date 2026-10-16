#!/usr/bin/env python3
"""
02_spatial_join.py
Spatial ETL & Attribute Harmonization for 'Milano by Building'.

Performs:
1. Loads 3D volumetric building footprints (DBT 2020 UN_VOL).
2. Computes realistic building height: (roof elevation UN_VOL_QE - ground elevation min(Z)).
3. Converts 3D geometries to 2D polygons in WGS84 (EPSG:4326).
4. Spatial joins building centroids against Milan 2011 Census tracts.
5. Harmonizes construction epochs from ISTAT census building distributions.
6. Overlays exact landmark construction dates for Milan's iconic historic and modern monuments.
7. Exports processed dataset to 'data/processed/milano_buildings.geojson'.
"""

import os
import sys
import math
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import pyogrio

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
OUTPUT_GEOJSON = os.path.join(PROCESSED_DIR, "milano_buildings.geojson")

# Curated landmark registry (lon, lat, radius_meters, build_year, name)
LANDMARKS = [
    (9.1919, 45.4642, 130, 1386, "Duomo di Milano"),
    (9.1793, 45.4705, 180, 1450, "Castello Sforzesco"),
    (9.1709, 45.4660, 80, 1469, "Santa Maria delle Grazie (Cenacolo)"),
    (9.1756, 45.4624, 90, 1099, "Basilica di Sant'Ambrogio"),
    (9.1820, 45.4578, 80, 372, "Basilica di San Lorenzo Maggiore"),
    (9.1895, 45.4674, 70, 1778, "Teatro alla Scala"),
    (9.1911, 45.4633, 90, 1773, "Palazzo Reale"),
    (9.1723, 45.4759, 60, 1807, "Arco della Pace"),
    (9.1899, 45.4658, 80, 1865, "Galleria Vittorio Emanuele II"),
    (9.1788, 45.4855, 180, 1866, "Cimitero Monumentale"),
    (9.2045, 45.4870, 180, 1931, "Milano Centrale"),
    (9.1239, 45.4781, 150, 1926, "Stadio San Siro"),
    (9.1898, 45.4600, 60, 1958, "Torre Velasca"),
    (9.2008, 45.4847, 60, 1960, "Grattacielo Pirelli (Pirellone)"),
    (9.1963, 45.4872, 80, 2010, "Palazzo Lombardia"),
    (9.1899, 45.4839, 70, 2012, "Torre UniCredit (Gae Aulenti)"),
    (9.1901, 45.4858, 60, 2014, "Bosco Verticale"),
    (9.1558, 45.4776, 60, 2015, "Torre Allianz (Isozaki)"),
    (9.1565, 45.4764, 60, 2017, "Torre Generali (Hadid)"),
    (9.1548, 45.4769, 60, 2020, "Torre PwC (Libeskind)"),
    (9.14767, 45.51375, 45, 1986, "Via Sabatino Lopez 5"),
]

# Census epoch bins mapped to representative years
EPOCH_COLS_MAP = {
    "Edifici ad uso residenziale costruiti prima del 1919": 1900,
    "Edifici ad uso residenziale costruiti dal 1919 al 1945": 1930,
    "Edifici ad uso residenziale costruiti dal 1946 al 1960": 1953,
    "Edifici ad uso residenziale costruiti dal 1961 al 1970": 1965,
    "Edifici ad uso residenziale costruiti dal 1971 al 1980": 1975,
    "Edifici ad uso residenziale costruiti dal 1981 al 1990": 1985,
    "Edifici ad uso residenziale costruiti dal 1991 al 2000": 1995,
    "Edifici ad uso residenziale costruiti dal 2001 al 2005": 2003,
    "Edifici ad uso residenziale costruiti dopo il 2005": 2012,
}


def compute_building_height(row) -> float:
    """Calculates building height in meters from DBT volumetric unit."""
    try:
        geom = row.geometry
        coords = list(geom.exterior.coords)
        ground_z = min(c[2] for c in coords if len(c) > 2)
        roof_z = float(row.get("UN_VOL_QE", 0))
        h = roof_z - ground_z
        if 2.5 <= h <= 300.0:
            return round(float(h), 1)
        # Fallback to UN_VOL_AV if available
        av = float(row.get("UN_VOL_AV", 0))
        if 2.5 <= av <= 300.0:
            return round(float(av), 1)
    except Exception:
        pass
    return 8.0  # default residential 2-floor height fallback


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print("=" * 60)
    print("Milano by Building - Step 02: Spatial ETL & Join")
    print("=" * 60)

    # 1. Load census datasets
    print("[1/5] Loading census section boundaries and epoch data...")
    sez_path = os.path.join(RAW_DIR, "sezioni_censimento_2011.geojson")
    csv_path = os.path.join(RAW_DIR, "ds384_edifici_censimento_2011.csv")

    sez_gdf = gpd.read_file(sez_path)[["SEZ", "geometry"]].to_crs(epsg=4326)
    census_df = pd.read_csv(csv_path, sep=";", encoding="latin1")

    # Compute weighted average construction year per census section
    print("[2/5] Calculating epoch statistics per census section...")
    section_year_stats = {}
    city_total_weight = 0
    city_weighted_year_sum = 0

    for _, r in census_df.iterrows():
        try:
            sez_id = int(r["Numero sezione"])
        except (ValueError, TypeError):
            continue

        tot_buildings = 0
        w_sum = 0
        bins = []
        for col_name, rep_year in EPOCH_COLS_MAP.items():
            if col_name in r:
                try:
                    count = int(r[col_name])
                    if count > 0:
                        tot_buildings += count
                        w_sum += count * rep_year
                        bins.append((rep_year, count))
                except (ValueError, TypeError):
                    pass

        if tot_buildings > 0:
            avg_year = int(round(w_sum / tot_buildings))
            section_year_stats[sez_id] = {
                "avg_year": avg_year,
                "bins": bins,
                "total": tot_buildings
            }
            city_total_weight += tot_buildings
            city_weighted_year_sum += w_sum

    city_default_year = int(round(city_weighted_year_sum / city_total_weight)) if city_total_weight > 0 else 1965
    print(f"  Processed {len(section_year_stats)} census sections. Citywide default year: {city_default_year}")

    # Map average year to sezioni GeoDataFrame
    sez_gdf["avg_year"] = sez_gdf["SEZ"].map(lambda s: section_year_stats.get(s, {}).get("avg_year", city_default_year))

    # 2. Load building volumes
    print("[3/5] Loading UN_VOL volumetric building footprints...")
    shp_path = os.path.join(RAW_DIR, "UN_VOL.shp")
    bldgs = gpd.read_file(shp_path)
    total_raw = len(bldgs)
    print(f"  Loaded {total_raw:,} building volume features.")

    # Calculate height while geometries still have 3D coordinates
    print("  Calculating 3D extrusion heights...")
    bldgs["height"] = bldgs.apply(compute_building_height, axis=1)

    # Convert 3D geometry to 2D
    bldgs["geometry"] = shapely.force_2d(bldgs["geometry"])

    # Reproject to WGS84
    print("  Reprojecting geometries to WGS84 (EPSG:4326)...")
    bldgs = bldgs.to_crs(epsg=4326)

    # 3. Spatial Join with Census tracts using centroids
    print("[4/5] Executing spatial join between building centroids and census tracts...")
    centroids = bldgs.geometry.centroid
    pts_gdf = gpd.GeoDataFrame({"orig_idx": bldgs.index}, geometry=centroids, crs=bldgs.crs)
    joined = gpd.sjoin(pts_gdf, sez_gdf[["SEZ", "avg_year", "geometry"]], how="left", predicate="within")

    # Group by orig_idx to avoid duplicates from boundary overlaps
    joined = joined[~joined.index.duplicated(keep="first")]
    bldgs["SEZ"] = joined["SEZ"].fillna(-1).astype(int)
    bldgs["year"] = joined["avg_year"].fillna(city_default_year).astype(int)

    # Refine individual building years using empirical distribution of the tract
    print("  Refining block-level year variation according to census age distributions...")
    rng = np.random.default_rng(seed=42)

    # Allocate realistic year distribution within each section
    for sez_id, stats in section_year_stats.items():
        mask = bldgs["SEZ"] == sez_id
        n_tract_bldgs = mask.sum()
        if n_tract_bldgs == 0:
            continue
        bins = stats["bins"]
        years = [b[0] for b in bins]
        counts = np.array([b[1] for b in bins], dtype=float)
        probs = counts / counts.sum()
        assigned_years = rng.choice(years, size=n_tract_bldgs, p=probs)
        # Add small deterministic jitter within epoch (+- 1 to 3 years) for organic visual appeal
        jitter = rng.integers(-2, 3, size=n_tract_bldgs)
        assigned_years = np.clip(assigned_years + jitter, 1850, 2024)
        bldgs.loc[mask, "year"] = assigned_years

    # 4. Landmark Overlays
    print("  Applying iconic historic landmark dates and labels...")
    bldgs["name"] = ""
    # Approximate degree distance for radius in meters (1 deg lat ~ 111,000m, 1 deg lon ~ 78,000m at 45°N)
    for l_lon, l_lat, radius_m, l_year, l_name in LANDMARKS:
        d_lat = radius_m / 111320.0
        d_lon = radius_m / (111320.0 * math.cos(math.radians(l_lat)))
        # Bounding box filter first
        cand = bldgs[
            (centroids.x >= l_lon - d_lon) & (centroids.x <= l_lon + d_lon) &
            (centroids.y >= l_lat - d_lat) & (centroids.y <= l_lat + d_lat)
        ]
        if not cand.empty:
            # Find closest feature to landmark epicenter
            dists = ((centroids.loc[cand.index].x - l_lon)**2 * (math.cos(math.radians(l_lat)))**2 + (centroids.loc[cand.index].y - l_lat)**2)**0.5 * 111320.0
            closest_idx = dists.idxmin()
            bldgs.loc[closest_idx, "year"] = l_year
            bldgs.loc[closest_idx, "name"] = l_name
            # For large complexes (Duomo, Castello, Centrale), tag surrounding features too
            nearby_mask = cand.index[dists < (radius_m * 0.75)]
            bldgs.loc[nearby_mask, "year"] = l_year
            bldgs.loc[nearby_mask, "name"] = l_name

    # 5. Clean output columns and export GeoJSON
    print("[5/5] Exporting clean dataset to GeoJSON...")
    bldgs["id"] = range(1, len(bldgs) + 1)
    output_cols = ["id", "height", "year", "name", "geometry"]
    clean_gdf = bldgs[output_cols].copy()

    # Filter out empty or invalid geometries
    clean_gdf = clean_gdf[clean_gdf.geometry.is_valid & (~clean_gdf.geometry.is_empty)]

    print(f"  Writing {len(clean_gdf):,} features to {OUTPUT_GEOJSON}...")
    pyogrio.write_dataframe(clean_gdf, OUTPUT_GEOJSON, driver="GeoJSON")

    file_size_mb = os.path.getsize(OUTPUT_GEOJSON) / (1024 * 1024)
    print(f"[SUCCESS] Exported {OUTPUT_GEOJSON} ({file_size_mb:.1f} MB)")
    print(f"  Sample statistics:")
    print(f"  - Height range: {clean_gdf['height'].min():.1f}m to {clean_gdf['height'].max():.1f}m (median: {clean_gdf['height'].median():.1f}m)")
    print(f"  - Year range: {clean_gdf['year'].min()} to {clean_gdf['year'].max()} (median: {clean_gdf['year'].median():.0f})")
    print(f"  - Landmark tagged buildings: {(clean_gdf['name'] != '').sum():,}")


if __name__ == "__main__":
    main()
