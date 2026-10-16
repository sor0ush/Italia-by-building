#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

INPUT_GEOJSON="data/processed/milano_buildings.geojson"
OUTPUT_PMTILES="data/tiles/milano_buildings.pmtiles"
WEB_PMTILES="web/milano_buildings.pmtiles"

echo "============================================================"
echo "Italy by Building - PMTiles Generation (Milano)"
echo "============================================================"

cd "${ROOT_DIR}"

if [ ! -f "${INPUT_GEOJSON}" ]; then
    echo "[ERROR] Input file not found: ${INPUT_GEOJSON}"
    exit 1
fi

mkdir -p "data/tiles"
mkdir -p "web"

echo "Input GeoJSON: ${INPUT_GEOJSON} ($(du -h "${INPUT_GEOJSON}" | cut -f1))"
echo "Target PMTiles: ${OUTPUT_PMTILES}"

tippecanoe \
    --output="${WEB_PMTILES}" \
    --layer=buildings \
    --name="Italy by Building - Milano" \
    --attribution="Comune di Milano / Open Data" \
    --minimum-zoom=12 \
    --maximum-zoom=16 \
    --drop-densest-as-needed \
    --extend-zooms-if-still-dropping \
    --force \
    "${INPUT_GEOJSON}"

cp -f "${WEB_PMTILES}" "${OUTPUT_PMTILES}"
echo "[SUCCESS] Generated PMTiles: $(du -h "${WEB_PMTILES}" | cut -f1)"

# Deterministic validation using Python pmtiles reader
uv run python -c "
import sys
from pmtiles.reader import Reader, MemorySource

with open('${WEB_PMTILES}', 'rb') as f:
    reader = Reader(MemorySource(f.read()))
    hdr = reader.header()
    min_lon = hdr['min_lon_e7'] / 1e7
    max_lon = hdr['max_lon_e7'] / 1e7
    min_lat = hdr['min_lat_e7'] / 1e7
    max_lat = hdr['max_lat_e7'] / 1e7
    center_lon = hdr['center_lon_e7'] / 1e7
    center_lat = hdr['center_lat_e7'] / 1e7

    print('PMTiles Header Verification:')
    print(f' - Spec Version: {hdr[\"version\"]}')
    print(f' - Zoom Range: z{hdr[\"min_zoom\"]} to z{hdr[\"max_zoom\"]}')
    print(f' - Tiles Count: {hdr[\"tile_entries_count\"]}')
    print(f' - Bounds: ({min_lon:.4f}, {min_lat:.4f}) to ({max_lon:.4f}, {max_lat:.4f})')
    print(f' - Center: ({center_lon:.4f}, {center_lat:.4f}) @ z{hdr[\"center_zoom\"]}')

    assert hdr['max_zoom'] >= 14, 'Max zoom must be at least 14'
    assert min_lon > 8.0 and max_lon < 10.5, 'Invalid Milan longitude bounds'
    assert min_lat > 44.5 and max_lat < 46.5, 'Invalid Milan latitude bounds'
    print('[SUCCESS] PMTiles header and spatial bounding box validated.')
"
