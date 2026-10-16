# Italy in Building 🇮🇹

Un atlante architettonico interattivo in 3D WebGL per esplorare le città d'Italia: ogni singolo edificio è estruso alla sua vera altezza volumetrica e colorato in base all'epoca storica di costruzione, con uno slider temporale interattivo, navigazione per monumenti storici e selezione delle città. Ispirato ad [Amsterdam by Building](https://github.com/alexbarakov/amsterdam-by-building).

![Railway Deploy](https://img.shields.io/badge/Deploy-Railway%20Ready-blueviolet)
![Engine](https://img.shields.io/badge/Engine-MapLibre%20GL%20JS-blue)
![Tiling](https://img.shields.io/badge/Format-PMTiles%20v3-green)
![Container](https://img.shields.io/badge/Container-Nginx%20Unprivileged-orange)

---

## 🏛️ Città Disponibili

All'avvio dell'applicazione o cliccando sul pulsante **🇮🇹 Città** nella testata, è possibile selezionare e navigare tra 8 città d'Italia:

| Città | Regione | Edifici Modellati | Epoca Storica | Monumenti & Landmark Inclusi |
|---|---|---|---|---|
| **Milano** | Lombardia | **237,743** | 372 d.C. – 2026 | Duomo, Castello Sforzesco, Scala, Galleria, Velasca, Pirelli, CityLife, Porta Nuova |
| **Torino** | Piemonte | **1,282** | 1348 – 2026 | Mole Antonelliana, Palazzo Reale, Palazzo Madama, Piazza San Carlo, Intesa Sanpaolo |
| **Bologna** | Emilia-Romagna | **4,079** | 1109 – 2026 | Due Torri (Asinelli & Garisenda), Basilica di San Petronio, Piazza Maggiore, Archiginnasio |
| **Monza** | Lombardia | **1,983** | 1293 – 2026 | Villa Reale del Piermarini, Duomo di Monza, Arengario Medievale, Ponte dei Leoni |
| **Pavia** | Lombardia | **12,757** | 1132 – 2026 | Città Giardino, Vallone, Policlinico San Matteo, Polo Cravino, Ponte Coperto, Castello, Duomo |
| **Como** | Lombardia | **3,462** | 1215 – 2026 | Cattedrale Santa Maria Assunta, Broletto, Casa del Fascio (Terragni), Tempio Voltiano, Villa Olmo |
| **Barletta** | Puglia | **5,285** | 450 d.C. – 2026 | Castello Svevo, Cattedrale, Borgovilla, Patalini, Settefrati, Zona 167 - Parco Umanità, Colosso |
| **Fano** | Marche | **8,284** | 9 d.C. – 2026 | Arco d'Augusto (9 d.C.), Mura Romane, Rocca Malatestiana, Vallato, Sassonia & Porto, Bellocchi |

---

## 🚀 Quick Start & Sviluppo Locale

### 1. Requisiti
- Python 3.10+ (con [`uv`](https://docs.astral.sh/uv/))
- `tippecanoe` (per la compilazione dei vector tiles)
- Docker (opzionale, per testare il container Railway)

### 2. Avviare il Server Locale
```bash
uv run python pipeline/serve.py 8080
```
Apri [http://localhost:8080](http://localhost:8080) nel browser.
Puoi navigare direttamente alle singole città tramite hash URL:
- `http://localhost:8080/#milano`
- `http://localhost:8080/#torino`
- `http://localhost:8080/#bologna`
- `http://localhost:8080/#monza`
- `http://localhost:8080/#pavia`
- `http://localhost:8080/#como`
- `http://localhost:8080/#barletta`
- `http://localhost:8080/#fano`

---

## 🚢 Deploy su Railway

Il progetto è configurato per il deploy immediato con container unprivileged su [Railway](https://railway.app):

### File di configurazione inclusi:
- **[`Dockerfile`](Dockerfile)**: Immagine Nginx non-root ultra-leggera (`nginxinc/nginx-unprivileged:1.28-alpine`) con healthcheck attivo.
- **[`deploy/nginx.conf.template`](deploy/nginx.conf.template)**:
  - Supporto nativo streaming vettoriale **HTTP 206 Byte-Range** (`max_ranges 1; etag on; gzip off;`) per tutti i file `.pmtiles`.
  - Endpoint `/healthz` con risposta `{"status":"ok"}`.
  - Compressione Gzip per HTML, CSS, JSON e JavaScript.
- **[`railway.json`](railway.json)**: Specifica build Dockerfile e healthcheck per l'orchestratore Railway.
- **[`.dockerignore`](.dockerignore)**: Esclude file grezzi e temporanei trasferendo solo gli asset web ottimizzati.

### Istruzioni Deploy Railway:
```bash
# Con la CLI di Railway:
railway login
railway init
railway up

# Oppure tramite GitHub:
# Collega la repository su Railway.app: il Dockerfile e railway.json
# verranno rilevati automaticamente senza alcuna configurazione manuale.
```

---

## 🧪 Esecuzione della Pipeline e Audit Completo

```bash
# 1. Rigenera i dataset per le città italiane
uv run python pipeline/build_italian_cities.py

# 2. Esegui la suite di verifica end-to-end (dati, pmtiles v3, assets web, railway, streaming)
uv run python pipeline/verify_all.py

# 3. Test build container Docker locale
docker build -t italy-in-building .
docker run -p 8080:8080 -e PORT=8080 italy-in-building
```
