# node_generator.py
# ══════════════════════════════════════════════════════════════════════════════
# DELHI URBAN FLOOD NODE GENERATOR
# Generates 2500 terrain-aware flood micro-hotspot nodes
# 1250 REAL nodes  → clustered around historically flood-prone seed zones
# 1250 DUMMY nodes → structured random within Delhi boundary (control set)
#
# DATA SOURCES:
# [1] CWC (Central Water Commission) — Yamuna flood stage records 2022-2024
#     https://cwc.gov.in/flood-forecast
# [2] Delhi Jal Board — Stormwater drain (nallah) network map 2023
#     https://www.delhijalboard.in
# [3] NDMA — Delhi flood inundation report, August 2023
#     https://ndma.gov.in
# [4] IMD Pune — District-wise rainfall data, Delhi 2022-2024
#     https://mausam.imd.gov.in
# [5] SRTM DEM 30m — Delhi elevation contours
#     https://earthexplorer.usgs.gov
# [6] DUSIB — JJ Cluster locations, Delhi
#     http://www.dusib.gov.in
# [7] Ground truth — TOI/NDTV; Yamuna 208.48m Jul 2023 (45-yr record)
#     IGI Terminal-1 collapse, Burari/Mustafabad inundation Jul 2024
# [8] Delhi Master Plan 2041 — Zone classification
#     https://dda.gov.in/masterplan2041
# [9] OpenStreetMap — Drain/road network cross-validation
#     https://www.openstreetmap.org
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd

# ── DELHI BOUNDARY (approx bounding box + polygon filter) ────────────────────
DELHI_LAT_MIN, DELHI_LAT_MAX = 28.40, 28.88
DELHI_LNG_MIN, DELHI_LNG_MAX = 76.84, 77.35

# Zones to EXCLUDE from dummy node generation
EXCLUSION_ZONES = [
    # IGI Airport campus [Src:9]
    {"lat_min": 28.52, "lat_max": 28.58, "lng_min": 77.06, "lng_max": 77.15},
    # Yamuna river channel itself [Src:9]
    {"lat_min": 28.40, "lat_max": 28.93, "lng_min": 77.21, "lng_max": 77.24},
    # Ridge Forest / Aravalli [Src:8]
    {"lat_min": 28.58, "lat_max": 28.70, "lng_min": 77.12, "lng_max": 77.18},
]

# ── FLOOD SEED ZONES ──────────────────────────────────────────────────────────
# elevation_m     : approx MSL [Src:5 SRTM DEM]
# historical_rain : flood events 2022-2024 out of 3 [Src:1,4,7]
# drain_quality   : 0.0=blocked 1.0=good [Src:2 DJB]
# zone_type       : [Src:8 DMP 2041]
# vulnerability   : base multiplier [Src:6 DUSIB]

FLOOD_SEED_ZONES = [
    {
        "name": "Yamuna Floodplain — Burari to Usmanpur",
        "lat": 28.7280, "lng": 77.2490, "radius_km": 1.8, "n_nodes": 110,
        "elevation_m": 199.5, "historical_rain": 3, "drain_quality": 0.15,
        "zone_type": "Unplanned", "vulnerability": 1.18,
        "source": "[Src:1,3,7] Burari inundated Jul 2023 & Jul 2024"
    },
    {
        "name": "Seelampur — Yamuna Bank JJ Cluster",
        "lat": 28.6620, "lng": 77.2790, "radius_km": 1.2, "n_nodes": 80,
        "elevation_m": 200.8, "historical_rain": 3, "drain_quality": 0.20,
        "zone_type": "Unplanned", "vulnerability": 1.16,
        "source": "[Src:6,7] JJ cluster; 2024 flood confirmed"
    },
    {
        "name": "Geeta Colony — Shahdara Drain Confluence",
        "lat": 28.6507, "lng": 77.2693, "radius_km": 1.0, "n_nodes": 70,
        "elevation_m": 202.0, "historical_rain": 2, "drain_quality": 0.30,
        "zone_type": "Unplanned", "vulnerability": 1.14,
        "source": "[Src:2,9] Shahdara drain nallah overflow"
    },
    {
        "name": "Mustafabad — Yamuna Vihar Low Pocket",
        "lat": 28.6980, "lng": 77.2820, "radius_km": 1.0, "n_nodes": 70,
        "elevation_m": 201.5, "historical_rain": 3, "drain_quality": 0.18,
        "zone_type": "Unplanned", "vulnerability": 1.19,
        "source": "[Src:6,7] Severely flooded Jul 2024; dense JJ cluster"
    },
    {
        "name": "ITO Barrage — Rajghat Low Zone",
        "lat": 28.6390, "lng": 77.2432, "radius_km": 1.1, "n_nodes": 75,
        "elevation_m": 203.0, "historical_rain": 3, "drain_quality": 0.25,
        "zone_type": "Unplanned", "vulnerability": 1.15,
        "source": "[Src:1,7] ITO barrage backwater; Yamuna 208.48m Jul 2023"
    },
    {
        "name": "Trilokpuri — Kondli Drain",
        "lat": 28.6180, "lng": 77.3050, "radius_km": 1.0, "n_nodes": 65,
        "elevation_m": 203.5, "historical_rain": 2, "drain_quality": 0.28,
        "zone_type": "Unplanned", "vulnerability": 1.13,
        "source": "[Src:3,7] Kondli drain overflow 2023 & 2024"
    },
    {
        "name": "Patparganj — Mayur Vihar Phase 1",
        "lat": 28.6083, "lng": 77.2952, "radius_km": 1.0, "n_nodes": 65,
        "elevation_m": 204.5, "historical_rain": 2, "drain_quality": 0.35,
        "zone_type": "Unplanned", "vulnerability": 1.12,
        "source": "[Src:2,9] Yamuna-adjacent; Patparganj nallah"
    },
    {
        "name": "Najafgarh Drain — Mangolpuri Sector",
        "lat": 28.6900, "lng": 77.0900, "radius_km": 1.4, "n_nodes": 80,
        "elevation_m": 210.5, "historical_rain": 2, "drain_quality": 0.22,
        "zone_type": "Unplanned", "vulnerability": 1.14,
        "source": "[Src:2,3] Najafgarh drain; heavily silted; 2023 overflow"
    },
    {
        "name": "Mundka — Najafgarh Drain West",
        "lat": 28.6680, "lng": 77.0300, "radius_km": 1.2, "n_nodes": 60,
        "elevation_m": 211.0, "historical_rain": 2, "drain_quality": 0.20,
        "zone_type": "Unplanned", "vulnerability": 1.12,
        "source": "[Src:2,9] Western nallah; blocked drain reports"
    },
    {
        "name": "Babarpur — Shahdara Drain East",
        "lat": 28.6823, "lng": 77.3050, "radius_km": 1.0, "n_nodes": 60,
        "elevation_m": 203.0, "historical_rain": 2, "drain_quality": 0.25,
        "zone_type": "Unplanned", "vulnerability": 1.13,
        "source": "[Src:2,3] Shahdara drain nallah corridor East Delhi"
    },
    {
        "name": "Gokulpuri — Low Elevation Pocket",
        "lat": 28.6920, "lng": 77.2960, "radius_km": 0.9, "n_nodes": 55,
        "elevation_m": 202.5, "historical_rain": 2, "drain_quality": 0.28,
        "zone_type": "Unplanned", "vulnerability": 1.12,
        "source": "[Src:2,8] Low-lying pocket; poor secondary drainage"
    },
    {
        "name": "Okhla — Agra Canal Drain Zone",
        "lat": 28.5350, "lng": 77.2710, "radius_km": 1.1, "n_nodes": 65,
        "elevation_m": 207.0, "historical_rain": 2, "drain_quality": 0.32,
        "zone_type": "Unplanned", "vulnerability": 1.11,
        "source": "[Src:3,9] Agra canal + nallah overflow; Okhla 2023"
    },
    {
        "name": "Badarpur — Sarita Vihar Drain",
        "lat": 28.5048, "lng": 77.2858, "radius_km": 1.0, "n_nodes": 55,
        "elevation_m": 208.5, "historical_rain": 1, "drain_quality": 0.38,
        "zone_type": "Unplanned", "vulnerability": 1.09,
        "source": "[Src:2,8] Southern drain network; moderate flood risk"
    },
    {
        "name": "Wazirabad — Reservoir Overflow Risk",
        "lat": 28.7480, "lng": 77.2290, "radius_km": 1.0, "n_nodes": 60,
        "elevation_m": 205.0, "historical_rain": 2, "drain_quality": 0.20,
        "zone_type": "Unplanned", "vulnerability": 1.13,
        "source": "[Src:1,7] Wazirabad barrage backwater; 2023 stage breach"
    },
    {
        "name": "Nizamuddin — Yamuna Flood Zone",
        "lat": 28.5887, "lng": 77.2547, "radius_km": 1.0, "n_nodes": 60,
        "elevation_m": 203.5, "historical_rain": 2, "drain_quality": 0.30,
        "zone_type": "Unplanned", "vulnerability": 1.12,
        "source": "[Src:1,3] Nizamuddin bridge downstream flooding"
    },
    {
        "name": "Bhalaswa — Rohini Drain North",
        "lat": 28.7380, "lng": 77.1700, "radius_km": 1.1, "n_nodes": 65,
        "elevation_m": 212.0, "historical_rain": 1, "drain_quality": 0.25,
        "zone_type": "Unplanned", "vulnerability": 1.10,
        "source": "[Src:6,9] Rohini drain; Bhalaswa landfill proximity"
    },
    {
        "name": "Dwarka — Palam Drain Low Pocket",
        "lat": 28.5780, "lng": 77.0700, "radius_km": 1.2, "n_nodes": 55,
        "elevation_m": 213.5, "historical_rain": 1, "drain_quality": 0.35,
        "zone_type": "Planned", "vulnerability": 1.05,
        "source": "[Src:2,9] Palam drain overflow into Dwarka sectors"
    },
    {
        "name": "Rohini — Sector 16-17 Drain",
        "lat": 28.7350, "lng": 77.1100, "radius_km": 1.0, "n_nodes": 50,
        "elevation_m": 213.0, "historical_rain": 1, "drain_quality": 0.30,
        "zone_type": "Planned", "vulnerability": 1.06,
        "source": "[Src:2,8] Rohini sector internal drain; 2022 waterlogging"
    },
    {
        "name": "Shahdara — Yamuna Pushta",
        "lat": 28.6742, "lng": 77.2897, "radius_km": 1.0, "n_nodes": 50,
        "elevation_m": 201.0, "historical_rain": 3, "drain_quality": 0.15,
        "zone_type": "Unplanned", "vulnerability": 1.17,
        "source": "[Src:6,7] Pushta settlements; direct Yamuna exposure all 3 yrs"
    },
]

# ── HISTORICAL RAINFALL BASELINE (for context, baked into vulnerability) ─────
# Source: [Src:4] IMD; [Src:1] CWC stage data
# 2022 Delhi monsoon: 653mm total (normal)
# 2023 Delhi monsoon: 771mm total; Yamuna stage 208.48m on 13 Jul (45yr record)
# 2024 Delhi monsoon: 228mm in 24hrs on 28 Jun; Terminal-1 collapse; >100 deaths
HISTORICAL_RAIN_MM = {1: 653, 2: 711, 3: 771}   # approx peak monsoon mm
HISTORICAL_RAIN_WEIGHT = {0: 0.0, 1: 0.25, 2: 0.55, 3: 1.0}

# ── ELEVATION REFERENCE ───────────────────────────────────────────────────────
# Source: [Src:5] SRTM DEM; Survey of India topo sheets
# Yamuna floodplain bed:    ~198-202m MSL  ← lowest, floods first
# Central Delhi (ITO):      ~203-207m MSL
# South Delhi ridge:        ~220-240m MSL  ← highest, drains fastest
# Najafgarh basin:          ~200-205m MSL
# West Delhi plains:        ~210-215m MSL
ELEVATION_FLOOD_THRESHOLD = 206.0   # below this = high flood risk [Src:1,5]

def is_excluded(lat, lng):
    for ex in EXCLUSION_ZONES:
        if ex["lat_min"] < lat < ex["lat_max"] and ex["lng_min"] < lng < ex["lng_max"]:
            return True
    return False

def generate_nodes(seed=42):
    """
    Returns a pandas DataFrame of 2500 terrain-aware flood nodes.
    ~1250 REAL nodes clustered around flood-prone seed zones.
    ~1250 DUMMY nodes structured-randomly within Delhi boundary.
    """
    rng = np.random.default_rng(seed)
    records = []

    # ── REAL NODES ────────────────────────────────────────────────────────────
    KM_TO_DEG = 1.0 / 111.0
    for zone in FLOOD_SEED_ZONES:
        r_deg = zone["radius_km"] * KM_TO_DEG
        generated = 0
        attempts  = 0
        while generated < zone["n_nodes"] and attempts < zone["n_nodes"] * 20:
            attempts += 1
            lat = rng.normal(zone["lat"], r_deg)
            lng = rng.normal(zone["lng"], r_deg * 1.2)
            if not (DELHI_LAT_MIN < lat < DELHI_LAT_MAX):
                continue
            if not (DELHI_LNG_MIN < lng < DELHI_LNG_MAX):
                continue
            if is_excluded(lat, lng):
                continue

            hist_w   = HISTORICAL_RAIN_WEIGHT[zone["historical_rain"]]
            elev_w   = max(0, (ELEVATION_FLOOD_THRESHOLD - zone["elevation_m"]) / 10.0)
            vuln     = round(zone["vulnerability"] + hist_w * 0.05 + elev_w * 0.02
                             + rng.uniform(-0.02, 0.02), 3)
            cap      = int(25 * zone["drain_quality"] * rng.uniform(0.85, 1.15))
            cap      = max(5, min(cap, 55))

            records.append({
                "lat":               round(float(lat), 5),
                "lng":               round(float(lng), 5),
                "zone_type":         zone["zone_type"],
                "vulnerability":     vuln,
                "base_capacity":     cap,
                "elevation_m":       round(zone["elevation_m"] + rng.uniform(-1.5, 1.5), 1),
                "historical_rain":   zone["historical_rain"],
                "drain_quality":     zone["drain_quality"],
                "is_real_node":      True,
                "seed_zone":         zone["name"],
            })
            generated += 1

    real_count = len(records)

    # ── DUMMY NODES ───────────────────────────────────────────────────────────
    target_dummy = 2500 - real_count
    generated = 0
    attempts  = 0
    while generated < target_dummy and attempts < target_dummy * 30:
        attempts += 1
        lat = rng.uniform(DELHI_LAT_MIN, DELHI_LAT_MAX)
        lng = rng.uniform(DELHI_LNG_MIN, DELHI_LNG_MAX)
        if is_excluded(lat, lng):
            continue
        # elevation interpolation: south Delhi higher
        elev = 220.0 - (lat - 28.40) * 25.0 + rng.uniform(-3, 3)
        elev = round(float(elev), 1)
        vuln = round(float(rng.uniform(0.80, 1.05)), 3)
        cap  = int(rng.uniform(30, 60))
        records.append({
            "lat":               round(float(lat), 5),
            "lng":               round(float(lng), 5),
            "zone_type":         "Planned" if rng.random() > 0.35 else "Unplanned",
            "vulnerability":     vuln,
            "base_capacity":     cap,
            "elevation_m":       elev,
            "historical_rain":   int(rng.integers(0, 2)),
            "drain_quality":     round(float(rng.uniform(0.35, 0.85)), 2),
            "is_real_node":      False,
            "seed_zone":         "DUMMY",
        })
        generated += 1

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = generate_nodes()
    real  = df[df.is_real_node].shape[0]
    dummy = df[~df.is_real_node].shape[0]
    print(f"Total nodes : {len(df)}")
    print(f"Real nodes  : {real}")
    print(f"Dummy nodes : {dummy}")
    print(f"\nSample real node:")
    print(df[df.is_real_node].iloc[0])
    print(f"\nSample dummy node:")
    print(df[~df.is_real_node].iloc[0])
    print(f"\nVulnerability range (real) : {df[df.is_real_node].vulnerability.min():.3f} - {df[df.is_real_node].vulnerability.max():.3f}")
    print(f"Vulnerability range (dummy): {df[~df.is_real_node].vulnerability.min():.3f} - {df[~df.is_real_node].vulnerability.max():.3f}")
    print(f"Elevation range (real)     : {df[df.is_real_node].elevation_m.min()} - {df[df.is_real_node].elevation_m.max()} m MSL")
