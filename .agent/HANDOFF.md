# AGENT HAND-OFF DOCUMENT: Italy in Building

## 1. Project Goal
Evolve "Milano by Building" into **"Italy in Building"**: a multi-city 3D WebGL architectural atlas for Italy with an interactive landing city selector and full Railway deployment support.
Supported Cities:
- **Milano** (Lombardia - 237k+ buildings)
- **Torino** (Piemonte)
- **Bologna** (Emilia-Romagna)
- **Monza** (Lombardia)
- **Pavia** (Lombardia)
- **Como** (Lombardia)
- **Barletta** (Puglia)
- **Fano** (Marche)

## 2. Current State-of-the-Art
- **Railway Deployment**: Verified locally with `docker build` and running container on port 8089. Includes `Dockerfile`, `deploy/nginx.conf.template` (HTTP 206 Byte-Range for all `.pmtiles`, `/healthz`), `railway.json`, and `.dockerignore`.
- **Multi-City Architecture**:
  - `web/cities_metadata.json` defines all 8 cities, camera presets, and historical landmarks.
  - All 8 cities compiled into standalone PMTiles v3 archives in `web/` and `data/tiles/`.
  - Landing city selection modal (`#city-modal`) displayed on initial load, with direct URL deep-linking (`#milano`, `#torino`, `#bologna`, etc.).
  - Header city switcher button with Italian flag badge.
  - Dynamic landmark quick-jump buttons and building inspection card for each city.
- **Verification**: `pipeline/verify_all.py` passed 100% across all 5 verification phases.

## 3. How to Deploy to Railway
```bash
railway up
```
Or connect the repository on Railway Dashboard; the `Dockerfile` and `railway.json` are auto-detected.
