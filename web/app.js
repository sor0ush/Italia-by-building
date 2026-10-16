/**
 * app.js
 * Italy by Building - 3D Multi-City Architectural Map
 * Powered by MapLibre GL JS + PMTiles v3
 */

// Initialize PMTiles protocol
const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

// City Registry
let CITIES_DATA = {};
let currentCityKey = "milano";
let mapLoaded = false;

// UI Elements
const cityModal = document.getElementById("city-modal");
const openCityModalBtn = document.getElementById("open-city-modal-btn");
const cityCardsContainer = document.getElementById("city-cards-container");
const activeCityName = document.getElementById("active-city-name");
const activeCityRegion = document.getElementById("active-city-region");
const cityTagline = document.getElementById("city-tagline");

const statTotalCount = document.getElementById("stat-total-count");
const statFilteredCount = document.getElementById("stat-filtered-count");
const statCurrentYear = document.getElementById("stat-current-year");

const landmarkButtonsContainer = document.getElementById("landmark-buttons-container");
const timeSlider = document.getElementById("time-slider");
const sliderYearLabel = document.getElementById("slider-year-label");
const playPauseBtn = document.getElementById("play-pause-btn");
const playIcon = document.getElementById("play-icon");
const playText = document.getElementById("play-text");
const resetBtn = document.getElementById("reset-btn");
const playbackSpeed = document.getElementById("playback-speed");

// Building card details
const cardTitle = document.getElementById("card-name");
const cardId = document.getElementById("card-id");
const cardHeight = document.getElementById("card-height");
const cardYear = document.getElementById("card-year");
const cardEpoch = document.getElementById("card-epoch");
const cardFloors = document.getElementById("card-floors");

let isPlaying = false;
let animationFrameId = null;
let lastTimestamp = 0;

function getEpochName(year) {
    if (year < 1800) return "Pre-1800 (Antico / Rinascimentale)";
    if (year <= 1899) return "1800 – 1899 (Ottocento)";
    if (year <= 1945) return "1900 – 1945 (Primo Novecento)";
    if (year <= 1970) return "1946 – 1970 (Ricostruzione & Boom)";
    if (year <= 1990) return "1971 – 1990 (Tardo Novecento)";
    if (year <= 2010) return "1991 – 2010 (Fine Millennio)";
    return "2011 – Oggi (Contemporaneo)";
}

// Map initialization with default center (Milano)
const map = new maplibregl.Map({
    container: "map",
    style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    center: [9.1919, 45.4642],
    zoom: 15.8,
    pitch: 58,
    bearing: -20,
    antialias: true
});

// Load cities metadata
async function loadCities() {
    try {
        const resp = await fetch("cities_metadata.json");
        CITIES_DATA = await resp.json();
    } catch (e) {
        console.error("Failed to load cities_metadata.json", e);
    }
    renderCityCards();

    // Check hash for direct city deep-link (e.g. #torino, #bologna)
    const hashCity = window.location.hash.replace("#", "").toLowerCase();
    if (hashCity && CITIES_DATA[hashCity]) {
        selectCity(hashCity, false);
    } else {
        // Show landing modal on fresh open
        openCityModal();
        selectCity("milano", false);
    }
}

function renderCityCards() {
    cityCardsContainer.innerHTML = "";
    Object.keys(CITIES_DATA).forEach((key) => {
        const city = CITIES_DATA[key];
        const card = document.createElement("div");
        card.className = `city-card ${key === currentCityKey ? "active-card" : ""}`;
        card.innerHTML = `
            <div class="card-top">
                <span class="card-city-name">${city.name}</span>
                <span class="card-region-tag">${city.region}</span>
            </div>
            <p class="card-desc">${city.description}</p>
            <div class="card-meta">
                <span class="meta-count">${city.buildingCount.toLocaleString()} edifici</span>
                <span class="meta-years">${city.yearSpan}</span>
            </div>
        `;
        card.addEventListener("click", () => {
            selectCity(key, true);
            closeCityModal();
        });
        cityCardsContainer.appendChild(card);
    });
}

function openCityModal() {
    cityModal.classList.remove("hidden");
}

function closeCityModal() {
    cityModal.classList.add("hidden");
}

openCityModalBtn.addEventListener("click", openCityModal);

// Close modal when clicking outside content
cityModal.addEventListener("click", (e) => {
    if (e.target === cityModal) {
        closeCityModal();
    }
});

function selectCity(cityKey, fly = true) {
    const city = CITIES_DATA[cityKey];
    if (!city) return;

    currentCityKey = cityKey;
    window.location.hash = cityKey;

    // Update Header HUD
    activeCityName.textContent = city.name;
    activeCityRegion.textContent = city.region;
    cityTagline.textContent = city.description;
    statTotalCount.textContent = city.buildingCount.toLocaleString();
    statFilteredCount.textContent = city.buildingCount.toLocaleString();

    // Update Landmark Buttons
    renderLandmarks(city.landmarks);

    // Update Map
    if (fly) {
        map.flyTo({
            center: city.center,
            zoom: city.zoom,
            pitch: city.pitch,
            bearing: city.bearing,
            duration: 2500,
            essential: true
        });
    } else {
        map.jumpTo({
            center: city.center,
            zoom: city.zoom,
            pitch: city.pitch,
            bearing: city.bearing
        });
    }

    if (mapLoaded) {
        switchCityTiles(city.tiles);
    }

    // Reset slider
    timeSlider.value = 2026;
    updateFilter(2026);

    renderCityCards();
}

function renderLandmarks(landmarks = []) {
    landmarkButtonsContainer.innerHTML = "";
    if (!landmarks || landmarks.length === 0) {
        landmarkButtonsContainer.innerHTML = `<span style="font-size: 11px; color: #64748b;">Nessun punto di interesse registrato</span>`;
        return;
    }

    landmarks.forEach((lm, idx) => {
        const btn = document.createElement("button");
        btn.className = `landmark-btn ${idx === 0 ? "active" : ""}`;
        btn.textContent = lm.name;
        btn.title = `Anno: ${lm.year}`;
        btn.addEventListener("click", () => {
            document.querySelectorAll(".landmark-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            map.flyTo({
                center: lm.center,
                zoom: lm.zoom,
                pitch: lm.pitch,
                bearing: lm.bearing,
                duration: 2000,
                essential: true
            });
        });
        landmarkButtonsContainer.appendChild(btn);
    });
}

function switchCityTiles(tilesFilename) {
    const sourceId = "city-buildings-source";
    const layerId = "city-3d-buildings";

    if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
    }

    map.addSource(sourceId, {
        type: "vector",
        url: `pmtiles://${tilesFilename}`
    });

    map.addLayer({
        id: layerId,
        source: sourceId,
        "source-layer": "buildings",
        type: "fill-extrusion",
        paint: {
            "fill-extrusion-height": [
                "interpolate", ["linear"], ["zoom"],
                12, ["*", ["coalesce", ["get", "height"], 8], 0.6],
                15, ["coalesce", ["get", "height"], 8]
            ],
            "fill-extrusion-base": 0,
            "fill-extrusion-color": [
                "step",
                ["get", "year"],
                "#3a0ca3", // < 1800
                1800, "#4361ee", // 1800 - 1899
                1900, "#4cc9f0", // 1900 - 1945
                1946, "#06d6a0", // 1946 - 1970
                1971, "#ffd166", // 1971 - 1990
                1991, "#f77f00", // 1991 - 2010
                2011, "#e63946"  // 2011 - Oggi
            ],
            "fill-extrusion-opacity": 0.95
        }
    });

    // Reattach hover listeners
    map.on("mousemove", layerId, (e) => {
        map.getCanvas().style.cursor = "pointer";
        if (e.features.length > 0) {
            const props = e.features[0].properties;
            const bldgName = props.name && props.name.trim() !== "" ? props.name : `${CITIES_DATA[currentCityKey]?.name || "Edificio"}`;
            const bldgYear = props.year ? parseInt(props.year, 10) : "Sconosciuto";
            const bldgHeight = props.height ? parseFloat(props.height).toFixed(1) : "10.0";
            const estFloors = Math.max(1, Math.round(parseFloat(bldgHeight) / 3.2));

            cardTitle.textContent = bldgName;
            cardId.textContent = `#${props.id || e.features[0].id || "--"}`;
            cardHeight.textContent = `${bldgHeight} m`;
            cardYear.textContent = bldgYear;
            cardEpoch.textContent = getEpochName(bldgYear);
            cardFloors.textContent = `${estFloors} p`;
        }
    });

    map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
    });

    updateFilter(parseInt(timeSlider.value, 10));
}

map.on("load", () => {
    mapLoaded = true;
    const initialTiles = CITIES_DATA[currentCityKey]?.tiles || "milano_buildings.pmtiles";
    switchCityTiles(initialTiles);
});

function updateFilter(year) {
    sliderYearLabel.textContent = year === 2026 ? "Tutti (2026)" : year;
    statCurrentYear.textContent = year === 2026 ? "Tutti" : year;

    const layerId = "city-3d-buildings";
    if (map.getLayer(layerId)) {
        if (year >= 2026) {
            map.setFilter(layerId, null);
            statFilteredCount.textContent = (CITIES_DATA[currentCityKey]?.buildingCount || 0).toLocaleString();
        } else {
            map.setFilter(layerId, ["<=", ["get", "year"], year]);
            const total = CITIES_DATA[currentCityKey]?.buildingCount || 1000;
            const minYear = 1800;
            const progress = Math.max(0, Math.min(1, (year - minYear) / (2026 - minYear)));
            const estimated = Math.round(total * Math.pow(progress, 0.7));
            statFilteredCount.textContent = Math.max(10, estimated).toLocaleString();
        }
    }
}

timeSlider.addEventListener("input", (e) => {
    updateFilter(parseInt(e.target.value, 10));
});

// Animation Loop
function animationLoop(timestamp) {
    if (!isPlaying) return;

    if (!lastTimestamp) lastTimestamp = timestamp;
    const elapsed = timestamp - lastTimestamp;
    const speed = parseFloat(playbackSpeed.value);

    if (elapsed > (50 / speed)) {
        let current = parseInt(timeSlider.value, 10);
        if (current >= 2026) {
            current = 1800;
        } else {
            current += 1;
        }
        timeSlider.value = current;
        updateFilter(current);
        lastTimestamp = timestamp;
    }

    animationFrameId = requestAnimationFrame(animationLoop);
}

playPauseBtn.addEventListener("click", () => {
    isPlaying = !isPlaying;
    if (isPlaying) {
        playIcon.textContent = "❚❚";
        playText.textContent = "PAUSA";
        playPauseBtn.classList.add("playing");
        lastTimestamp = 0;
        if (parseInt(timeSlider.value, 10) >= 2026) {
            timeSlider.value = 1800;
            updateFilter(1800);
        }
        animationFrameId = requestAnimationFrame(animationLoop);
    } else {
        playIcon.textContent = "▶";
        playText.textContent = "PLAY";
        playPauseBtn.classList.remove("playing");
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
    }
});

resetBtn.addEventListener("click", () => {
    if (isPlaying) {
        isPlaying = false;
        playIcon.textContent = "▶";
        playText.textContent = "PLAY";
        playPauseBtn.classList.remove("playing");
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
    }
    timeSlider.value = 2026;
    updateFilter(2026);
});

// Start initialization
loadCities();
