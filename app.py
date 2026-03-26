
import os

from hathni_kund import get_hk_data




from report_engine import (
    build_snapshot, send_ndrf_dispatch,
    send_morning_briefing, check_ensemble_alert,
    generate_report_html
)
from datetime import datetime
import time



from flask import Flask, request, jsonify
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from math import radians, cos, sin, asin, sqrt
import pandas as pd
import numpy as np
import folium
import geopandas as gpd
from shapely.geometry import LineString
import time
import warnings

warnings.filterwarnings("ignore")

app = Flask(__name__)

BHARAT_MANDAPAM = [28.6196, 77.2425]
NUM_POINTS = 2500
CACHE_TTL = 600

RELIEF_CAMPS = [
    {"name": "NDRF Unit 8 (CWG Village)",  "lat": 28.612, "lng": 77.275, "type": "Real"},
    {"name": "Geeta Colony Relief Center", "lat": 28.650, "lng": 77.265, "type": "Real"},
    {"name": "Okhla Phase 1 Response Hub", "lat": 28.525, "lng": 77.285, "type": "Dummy"},
    {"name": "Mayur Vihar Ext. Shelter",   "lat": 28.600, "lng": 77.295, "type": "Dummy"},
]

DELHI_BOUNDARY = [
    [28.8832, 77.0840], [28.8900, 77.1200], [28.8830, 77.1600],
    [28.8710, 77.1900], [28.8580, 77.2100], [28.8430, 77.2250],
    [28.8280, 77.2380], [28.8130, 77.2490], [28.7980, 77.2620],
    [28.7820, 77.2780], [28.7670, 77.2940], [28.7540, 77.3100],
    [28.7410, 77.3260], [28.7290, 77.3400], [28.7130, 77.3510],
    [28.6950, 77.3580], [28.6780, 77.3630], [28.6600, 77.3650],
    [28.6430, 77.3640], [28.6260, 77.3580], [28.6090, 77.3480],
    [28.5920, 77.3360], [28.5760, 77.3220], [28.5600, 77.3100],
    [28.5430, 77.3020], [28.5270, 77.2900], [28.5110, 77.2760],
    [28.4960, 77.2580], [28.4820, 77.2380], [28.4700, 77.2150],
    [28.4610, 77.1890], [28.4550, 77.1620], [28.4520, 77.1340],
    [28.4530, 77.1060], [28.4590, 77.0790], [28.4700, 77.0540],
    [28.4850, 77.0320], [28.5030, 77.0150], [28.5230, 77.0020],
    [28.5440, 76.9930], [28.5660, 76.9890], [28.5880, 76.9890],
    [28.6100, 76.9930], [28.6310, 77.0010], [28.6510, 77.0130],
    [28.6700, 77.0290], [28.6880, 77.0470], [28.7050, 77.0650],
    [28.7220, 77.0780], [28.7420, 77.0830], [28.7630, 77.0820],
    [28.7840, 77.0800], [28.8060, 77.0790], [28.8280, 77.0800],
    [28.8560, 77.0810], [28.8832, 77.0840],
]


def load_yamuna_points():
    try:
        pts = []
        with open('yamuna_points.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                lat, lng = line.split(',')
                pts.append((float(lat.strip()), float(lng.strip())))
        return pts if pts else YAMUNA_FALLBACK
    except Exception:
        return YAMUNA_FALLBACK

# Fallback if file missing
YAMUNA_FALLBACK = [
    (28.8720, 77.1882),
    (28.6196, 77.2425),
    (28.4040, 77.3010),
]

YAMUNA_POLYLINE = load_yamuna_points()


DELHI_GRID_CENTROIDS = [
    (28.45, 77.05), (28.45, 77.20), (28.45, 77.35),
    (28.55, 77.05), (28.55, 77.20), (28.55, 77.35),
    (28.62, 77.10), (28.62, 77.24), (28.62, 77.38),
    (28.70, 77.10), (28.70, 77.24), (28.70, 77.38),
    (28.78, 77.10), (28.78, 77.24), (28.78, 77.38),
    (28.85, 77.10), (28.85, 77.20), (28.85, 77.35),
    (28.50, 77.15), (28.75, 77.28),
]

# ── 50 Delhi localities → lat/lng ─────────────────────────────────────────────
DELHI_LOCALITIES = {
    "connaught place":    (28.6315, 77.2167),
    "cp":                 (28.6315, 77.2167),
    "lajpat nagar":       (28.5700, 77.2433),
    "chandni chowk":      (28.6506, 77.2303),
    "karol bagh":         (28.6519, 77.1909),
    "saket":              (28.5245, 77.2066),
    "dwarka":             (28.5921, 77.0460),
    "rohini":             (28.7495, 77.0666),
    "janakpuri":          (28.6289, 77.0831),
    "nehru place":        (28.5491, 77.2513),
    "okhla":              (28.5350, 77.2710),
    "shahdara":           (28.6742, 77.2897),
    "mayur vihar":        (28.6083, 77.2952),
    "yamuna vihar":       (28.6950, 77.2780),
    "kashmere gate":      (28.6678, 77.2285),
    "ito":                (28.6289, 77.2414),
    "nizamuddin":         (28.5887, 77.2547),
    "rajghat":            (28.6401, 77.2493),
    "red fort":           (28.6562, 77.2410),
    "india gate":         (28.6129, 77.2295),
    "pitampura":          (28.7011, 77.1336),
    "shalimar bagh":      (28.7165, 77.1644),
    "wazirabad":          (28.7480, 77.2514),
    "burari":             (28.7531, 77.2074),
    "geeta colony":       (28.6507, 77.2693),
    "preet vihar":        (28.6431, 77.2964),
    "vivek vihar":        (28.6704, 77.3142),
    "dilshad garden":     (28.6823, 77.3199),
    "anand vihar":        (28.6469, 77.3152),
    "laxmi nagar":        (28.6328, 77.2773),
    "gandhi nagar":       (28.6640, 77.2758),
    "gtb nagar":          (28.7001, 77.2033),
    "model town":         (28.7133, 77.1934),
    "azadpur":            (28.7207, 77.1849),
    "netaji subhash place":(28.6950, 77.1519),
    "paschim vihar":      (28.6689, 77.1019),
    "uttam nagar":        (28.6211, 77.0560),
    "vikaspuri":          (28.6390, 77.0714),
    "rajouri garden":     (28.6487, 77.1225),
    "patel nagar":        (28.6577, 77.1699),
    "punjabi bagh":       (28.6689, 77.1350),
    "kirti nagar":        (28.6554, 77.1501),
    "moti nagar":         (28.6623, 77.1611),
    "subhash nagar":      (28.6440, 77.1299),
    "tilak nagar":        (28.6350, 77.1000),
    "badarpur":           (28.5048, 77.2858),
    "sarita vihar":       (28.5356, 77.2908),
    "jasola":             (28.5509, 77.2940),
    "tughlakabad":        (28.4845, 77.2567),
    "mehrauli":           (28.5235, 77.1846),
    "vasant kunj":        (28.5213, 77.1564),
    "munirka":            (28.5604, 77.1776),
    "rk puram":           (28.5672, 77.1813),
    "hauz khas":          (28.5494, 77.2001),
    "green park":         (28.5583, 77.2063),
    "malviya nagar":      (28.5340, 77.2095),
    "bharat mandapam":    (28.6196, 77.2425),
    "pragati maidan":     (28.6196, 77.2425),
    "ito barrage":        (28.6390, 77.2432),
    "palla":              (28.8720, 77.1882),
    "signature bridge":   (28.7740, 77.2195),
    "cherrapunji": (25.3009, 91.6962),
    "nohkalikai falls": (25.2776, 91.7265),
    "mawsmai cave": (25.2840, 91.7400),
}

_rainfall_cache = {"data": None, "ts": 0}
_hk_cache = {"data": None, "ts": 0}


# ── HELPERS ───────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6372.8
    dLat = radians(lat2 - lat1); dLon = radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return 2 * R * asin(sqrt(a))

def make_digipin(lat, lng):
    return "DL-" + str(lat)[:7].replace(".", "").replace("-","")[-4:] + str(lng)[:7].replace(".", "").replace("-","")[-4:]

def nearest_camp_info(lat, lng):
    camp = min(RELIEF_CAMPS, key=lambda c: haversine(lat, lng, c["lat"], c["lng"]))
    return camp["name"], round(haversine(lat, lng, camp["lat"], camp["lng"]), 2)

def fetch_open_meteo(lat, lon):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&current=precipitation,rain,showers&timezone=Asia%2FKolkata")
    try:
        r = requests.get(url, timeout=8); r.raise_for_status()
        c = r.json().get("current", {})
        return max(float(c.get("precipitation",0) or 0),
                   float(c.get("rain",0) or 0)+float(c.get("showers",0) or 0))
    except Exception:
        return None

def fetch_imd_delhi():
    try:
        r = requests.get("https://mausam.imd.gov.in/api/districtwise_rainfall_api.php?id=164", timeout=6)
        r.raise_for_status()
        return float(r.json().get("ACTUAL",0) or 0) / 24.0
    except Exception:
        return 0.0

def fetch_grid_rainfall():
    imd_rain = fetch_imd_delhi()
    centroid_data = []
    for lat, lon in DELHI_GRID_CENTROIDS:
        om = fetch_open_meteo(lat, lon)
        blended = (0.6*om + 0.4*imd_rain) if om is not None else imd_rain
        centroid_data.append({"lat": lat, "lon": lon, "rain_mm": round(blended, 3)})
        time.sleep(0.05)
    return centroid_data, imd_rain

def idw_interpolate(node_lats, node_lons, centroid_data, power=2):
    c_lats = np.array([c["lat"] for c in centroid_data])
    c_lons = np.array([c["lon"] for c in centroid_data])
    c_rain = np.array([c["rain_mm"] for c in centroid_data])
    node_lats = np.array(node_lats); node_lons = np.array(node_lons)
    out = np.zeros(len(node_lats))
    for i in range(len(node_lats)):
        dists = np.array([haversine(node_lats[i], node_lons[i], c_lats[j], c_lons[j])
                          for j in range(len(c_lats))])
        exact = np.where(dists < 0.001)[0]
        if len(exact): out[i] = c_rain[exact[0]]; continue
        w = 1.0/(dists**power)
        out[i] = np.sum(w*c_rain)/np.sum(w)
    return out

def compute_simulated_idw(base_rain, river_stage, silt, trash, enable_river, enable_maint):
    rng = np.random.default_rng(seed=int(base_rain * 100))
    noise = rng.uniform(0.65, 1.35, len(DELHI_GRID_CENTROIDS))
    centroid_data = [
        {"lat": lat, "lon": lon, "rain_mm": round(float(base_rain * noise[i]), 3)}
        for i, (lat, lon) in enumerate(DELHI_GRID_CENTROIDS)
    ]
    node_lats = df["lat"].tolist(); node_lons = df["lng"].tolist()
    node_rains = idw_interpolate(node_lats, node_lons, centroid_data)
    maint_factor = (silt * trash) if enable_maint else 1.0
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        local_rain    = float(node_rains[i])
        effective_cap = row["base_capacity"] / maint_factor
        dist_km       = row["dist_to_river"]
        river_surcharge = 0.0
        if enable_river and river_stage > 205.3:
            river_surcharge = ((river_stage - 205.3) * 45.0) / (dist_km + 0.1)
        flood_load = max(0.0, (local_rain * row["vulnerability"] - effective_cap) + river_surcharge)
        sig_rain  = min(local_rain / 150.0, 1.0) * 30
        sig_river = min(river_surcharge / 100.0, 1.0) * 25 if enable_river else 0
        sig_drain = max(0, (1.0 - effective_cap / 60.0)) * 25
        sig_vuln  = (row["vulnerability"] - 0.8) / 0.4 * 20
        ensemble  = round(sig_rain + sig_river + sig_drain + sig_vuln, 2)
        readiness = round(max(0, 100 - ensemble - (flood_load * 0.3)), 1)
        results.append({
            "lat": round(row["lat"], 5), "lng": round(row["lng"], 5),
            "rain_mm": round(local_rain, 3), "flood_load": round(flood_load, 2),
            "readiness": readiness, "ensemble": ensemble,
            "digipin": row["digipin"], "zone_type": row["zone_type"],
            "dist_river": round(dist_km, 2),
            "base_capacity": int(row["base_capacity"]),
            "vulnerability": round(float(row["vulnerability"]), 2),
        })
    avg_ensemble  = round(float(np.mean([r["ensemble"] for r in results])), 2)
    avg_readiness = round(float(np.mean([r["readiness"] for r in results])), 1)
    critical      = [r for r in results if r["flood_load"] > 80]
    return {
        "nodes": results, "avg_ensemble": avg_ensemble,
        "avg_readiness": avg_readiness, "critical_count": len(critical),
        "top_critical": sorted(critical, key=lambda x: x["flood_load"], reverse=True)[:5],
        "centroid_data": centroid_data, "base_rain": base_rain,
        "river_stage": river_stage, "maint_factor": round(maint_factor, 2),
    }


# ── BUILD YAMUNA + NODE DATA ───────────────────────────────────────────────────
yamuna_shapely = LineString([(lon, lat) for lat, lon in YAMUNA_POLYLINE])
yamuna_gdf = gpd.GeoDataFrame(geometry=[yamuna_shapely], crs="EPSG:4326")

from node_generator import generate_nodes
df = generate_nodes() # node generator
# Recompute dist_to_river for new nodes
points_gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lng, df.lat), crs="EPSG:4326")
df["dist_to_river"] = (
    points_gdf.to_crs(epsg=32643).geometry
    .distance(yamuna_gdf.to_crs(epsg=32643).unary_union)
    / 1000.0
)
df["digipin"] = df.apply(lambda r: make_digipin(r["lat"], r["lng"]), axis=1)

# ── TEST NODES: Cherrapunji (outside Delhi — proves live engine) ──────────────
cherrapunji_nodes = pd.DataFrame({
    "lat":           [25.3009,   25.2776,   25.2840],
    "lng":           [91.6962,   91.7265,   91.7400],
    "zone_type":     ["Planned", "Unplanned","Unplanned"],
    "vulnerability": [1.05,       1.15,       1.10],
    "base_capacity": [30,         20,         20],
    "dist_to_river": [0.0,        0.0,        0.0],
})
cherrapunji_nodes["digipin"] = cherrapunji_nodes.apply(
    lambda r: make_digipin(r["lat"], r["lng"]), axis=1
)
df = pd.concat([df, cherrapunji_nodes], ignore_index=True)

# ── Pre-build node registry for search (JSON embedded in page) ────────────────
node_registry = []
for idx, row in df.head(450).iterrows():
    camp_name, camp_dist = nearest_camp_info(row["lat"], row["lng"])
    node_registry.append({
        "idx":       idx,
        "lat":       round(row["lat"], 5),
        "lng":       round(row["lng"], 5),
        "digipin":   row["digipin"],
        "zone":      row["zone_type"],
        "vuln":      round(float(row["vulnerability"]), 2),
        "cap":       int(row["base_capacity"]),
        "dist_r":    round(row["dist_to_river"], 2),
        "camp":      camp_name,
        "camp_dist": camp_dist,
    })
import json
NODE_REGISTRY_JSON = json.dumps(node_registry)
LOCALITIES_JSON    = json.dumps({k: list(v) for k, v in DELHI_LOCALITIES.items()})


# ── BUILD MAP ─────────────────────────────────────────────────────────────────
m = folium.Map(location=BHARAT_MANDAPAM, zoom_start=11, tiles=None)
folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                 attr="Google", name="Satellite").add_to(m)

folium.RegularPolygonMarker(
    location=BHARAT_MANDAPAM, number_of_sides=8, radius=15,
    color="#FFD700", fill=True, fill_opacity=0.8,
    tooltip="🏛️ BHARAT MANDAPAM — Command HQ"
).add_to(m)

folium.Polygon(locations=DELHI_BOUNDARY, color="#ffcc00", weight=2, opacity=0.7,
               fill=True, fill_color="#ffcc00", fill_opacity=0.04,
               dash_array="6,10", tooltip=None).add_to(m)

folium.PolyLine(YAMUNA_POLYLINE, color="#001a2e", weight=24, opacity=0.5).add_to(m)
folium.PolyLine(YAMUNA_POLYLINE, color="#005f8e", weight=15, opacity=0.7).add_to(m)
folium.PolyLine(YAMUNA_POLYLINE, color="#00d4ff", weight=6,  opacity=1.0,
                tooltip="🌊 Yamuna River").add_to(m)

for lm in [
    {"name":"Palla Village Entry","lat":28.8720,"lng":77.1882,"c":"#00ffcc"},
    {"name":"Wazirabad Barrage",  "lat":28.8120,"lng":77.2115,"c":"#ffcc00"},
    {"name":"Signature Bridge",   "lat":28.7740,"lng":77.2195,"c":"#ffcc00"},
    {"name":"ITO Barrage",        "lat":28.6390,"lng":77.2432,"c":"#ffcc00"},
    {"name":"Nizamuddin Bridge",  "lat":28.5740,"lng":77.2695,"c":"#ffcc00"},
    {"name":"Okhla Barrage",      "lat":28.5270,"lng":77.3010,"c":"#ffcc00"},

]:
    folium.CircleMarker(location=[lm["lat"],lm["lng"]], radius=7,
                        color=lm["c"], weight=2, fill=True,
                        fill_color=lm["c"], fill_opacity=0.9,
                        tooltip=f"🔵 {lm['name']}").add_to(m)

for camp in RELIEF_CAMPS:
    color = "#00ffcc" if camp["type"]=="Real" else "#ffaa00"
    folium.CircleMarker(location=[camp["lat"],camp["lng"]], radius=10,
                        color=color, weight=3, fill=True,
                        fill_color=color, fill_opacity=0.5,
                        tooltip=f"🚁 {camp['name']} [{camp['type']}]").add_to(m)

for idx, row in df.head(450).iterrows():
    tag = f"{row['lat']}_{row['lng']}_SYNC"
    camp_name, camp_dist = nearest_camp_info(row["lat"], row["lng"])
    vuln_pct = int(row["vulnerability"]*100)
    dist_r   = round(row["dist_to_river"], 2)
    cap      = int(row["base_capacity"])

    tooltip_html = f"""<div style="font-family:'Courier New',monospace;font-size:11px;
      background:#0a0a12;color:#fff;padding:10px 14px;border-radius:8px;
      border:1px solid #333;min-width:240px;line-height:2.0;">
      <div style="color:#00ffcc;font-size:13px;font-weight:bold;letter-spacing:1px;margin-bottom:4px;">
        📍 {row['digipin']}</div>
      <div style="color:#556;font-size:9px;margin-bottom:8px;">{row['lat']:.5f}° N, {row['lng']:.5f}° E</div>
      <div>🏙️ Zone: <span style="color:#ffcc00">{row['zone_type']}</span></div>
      <div>⚡ Vulnerability: <span style="color:#ff6666">{vuln_pct}%</span></div>
      <div>🌊 Dist to Yamuna: <span style="color:#00aaff">{dist_r} km</span></div>
      <div>🚰 Drain Capacity: <span style="color:#00ffcc">{cap} mm/hr</span></div>
      <hr style="border-color:#222;margin:6px 0;">
      <div>💧 Spatial Rain: <span id="sr_{idx}" style="color:#00aaff">—</span></div>
      <div>🌊 Flood Load: <span id="fl_{idx}" style="color:#df00ff;font-weight:bold;">move slider →</span></div>
      <div>📊 Ensemble: <span id="es_{idx}" style="color:#ffaa00">—</span></div>
      <div>🛡️ Readiness: <span id="rd_{idx}" style="color:#00ffcc">——</span></div>
      <hr style="border-color:#222;margin:6px 0;">
      <div style="color:#667;font-size:9px;">🚁 {camp_name}<br>📏 {camp_dist} km away</div>
    </div>"""

    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=6, color="white", weight=1,
        fill=True, fill_color="#00ff00", fill_opacity=0.9,
        tooltip=folium.Tooltip(tooltip_html, sticky=True),
        className=(f"node {row['zone_type']} v-{vuln_pct} "
                   f"d-{min(int(row['dist_to_river']*10),999)} "
                   f"c-{cap} idx-{idx} data-{tag}")
    ).add_to(m)


# ── MODAL ─────────────────────────────────────────────────────────────────────
modal_html = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');
  #modeOverlay{position:fixed;inset:0;z-index:9999999;display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    background:radial-gradient(ellipse at 50% 40%,#0a0f1a 0%,#000 100%);
    font-family:'Rajdhani',sans-serif;overflow:hidden;}
  #modeOverlay::before{content:'';position:absolute;inset:0;
    background-image:linear-gradient(rgba(0,255,204,.04) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,255,204,.04) 1px,transparent 1px);
    background-size:40px 40px;animation:gridDrift 20s linear infinite;pointer-events:none;}
  @keyframes gridDrift{from{transform:translateY(0)}to{transform:translateY(40px)}}
  #modeOverlay::after{content:'';position:absolute;inset:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.08) 2px,rgba(0,0,0,.08) 4px);
    pointer-events:none;}
  .modal-content{position:relative;z-index:1;text-align:center;animation:fadeUp .8s cubic-bezier(.16,1,.3,1) both;}
  @keyframes fadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
  .modal-emblem{width:64px;height:64px;margin:0 auto 24px;position:relative;}
  .modal-emblem svg{width:100%;height:100%;animation:spinSlow 12s linear infinite;}
  @keyframes spinSlow{to{transform:rotate(360deg)}}
  .modal-emblem-core{position:absolute;inset:16px;background:#00ffcc;border-radius:50%;
    box-shadow:0 0 20px #00ffcc,0 0 40px rgba(0,255,204,.4);animation:corePulse 2s ease-in-out infinite;}
  @keyframes corePulse{0%,100%{box-shadow:0 0 20px #00ffcc,0 0 40px rgba(0,255,204,.4)}
    50%{box-shadow:0 0 30px #00ffcc,0 0 70px rgba(0,255,204,.6)}}
  .modal-label{font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:4px;color:#00ffcc;margin-bottom:8px;opacity:.7;}
  .modal-title{font-size:42px;font-weight:700;color:#fff;line-height:1.1;letter-spacing:-.5px;margin-bottom:6px;}
  .modal-title span{color:#00ffcc;}
  .modal-subtitle{font-family:'Share Tech Mono',monospace;font-size:11px;color:#c0d4e8;letter-spacing:2px;margin-bottom:52px;}
  .modal-buttons{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;}
  .modal-footer{margin-top:40px;font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:2px;color:#aabbcc;}
  .mode-btn{position:relative;width:220px;padding:0;border:none;background:none;cursor:pointer;
    font-family:'Rajdhani',sans-serif;outline:none;transition:transform .2s;}
  .mode-btn:hover{transform:translateY(-4px);}.mode-btn:active{transform:translateY(-1px);}
  .mode-btn-inner{padding:28px 20px 24px;border-radius:12px;border:1px solid;position:relative;
    overflow:hidden;transition:box-shadow .3s;}
  #btnSimulated .mode-btn-inner{background:linear-gradient(135deg,#0d1f1a,#081510);border-color:#00ffcc;}
  #btnSimulated:hover .mode-btn-inner{box-shadow:0 0 30px rgba(0,255,204,.25),inset 0 0 20px rgba(0,255,204,.05);}
  #btnReal .mode-btn-inner{background:linear-gradient(135deg,#1a0d1a,#100811);border-color:#df00ff;}
  #btnReal:hover .mode-btn-inner{box-shadow:0 0 30px rgba(223,0,255,.25),inset 0 0 20px rgba(223,0,255,.05);}
  .mode-btn-inner::before{content:'';position:absolute;top:-100%;left:-100%;width:300%;height:300%;
    background:linear-gradient(135deg,transparent 40%,rgba(255,255,255,.04) 50%,transparent 60%);
    transition:top .5s,left .5s;}
  .mode-btn:hover .mode-btn-inner::before{top:-50%;left:-50%;}
  .btn-icon{font-size:32px;margin-bottom:10px;display:block;}
  .btn-title{font-size:22px;font-weight:700;letter-spacing:2px;display:block;margin-bottom:8px;}
  #btnSimulated .btn-title{color:#00ffcc;}#btnReal .btn-title{color:#df00ff;}
  .btn-desc{font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:1px;line-height:1.6;color:#667;display:block;}
  .btn-badge{position:absolute;top:10px;right:10px;font-family:'Share Tech Mono',monospace;
    font-size:8px;padding:3px 7px;border-radius:3px;letter-spacing:1px;}
  #btnSimulated .btn-badge{background:rgba(0,255,204,.12);color:#00ffcc;border:1px solid rgba(0,255,204,.3);}
  #btnReal .btn-badge{background:rgba(223,0,255,.12);color:#df00ff;border:1px solid rgba(223,0,255,.3);
    animation:badgePulse 1.5s ease-in-out infinite;}
  @keyframes badgePulse{0%,100%{opacity:1}50%{opacity:.4}}
  #connectingState{display:none;flex-direction:column;align-items:center;gap:16px;}
  .connect-spinner{width:48px;height:48px;border:2px solid rgba(223,0,255,.2);
    border-top-color:#df00ff;border-radius:50%;animation:spin .8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg)}}
  .connect-label{font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:3px;color:#df00ff;}
  .connect-log{font-family:'Share Tech Mono',monospace;font-size:9px;color:#556;letter-spacing:1px;text-align:center;line-height:2;}
  #modeBadge{display:none;position:fixed;top:15px;right:15px;z-index:99999;
    font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:2px;
    padding:8px 14px;border-radius:6px;border:1px solid;backdrop-filter:blur(8px);}
  #modeBadge.simulated{background:rgba(0,255,204,.08);border-color:rgba(0,255,204,.4);color:#00ffcc;}
  #modeBadge.real{background:rgba(223,0,255,.08);border-color:rgba(223,0,255,.4);color:#df00ff;
    animation:badgePulse 2s ease-in-out infinite;}
  .leaflet-tooltip{background:transparent !important;border:none !important;box-shadow:none !important;padding:0 !important;}
  .leaflet-interactive:focus{outline:none !important;}
</style>
<div id="modeOverlay">
  <div class="modal-content" id="selectorState">
    <div class="modal-emblem">
      <svg viewBox="0 0 64 64" fill="none">
        <polygon points="32,2 62,18 62,46 32,62 2,46 2,18" stroke="#00ffcc" stroke-width="1" stroke-opacity=".5"/>
        <polygon points="32,10 54,22 54,42 32,54 10,42 10,22" stroke="#00ffcc" stroke-width=".5" stroke-opacity=".3"/>
      </svg>
      <div class="modal-emblem-core"></div>
    </div>
    <div class="modal-label">NATIONAL DISASTER RESPONSE FRAMEWORK</div>
    <div class="modal-title">Urban Flood <span>Intelligence</span></div>
    <div class="modal-title" style="font-size:28px;font-weight:400;color:#aaa;margin-top:4px;">Predictive Micro-Hotspot Engine</div>
    <div class="modal-subtitle">DELHI NCR · 2500 NODES · BHARAT MANDAPAM COMMAND</div>
    <div class="modal-buttons">
      <button class="mode-btn" id="btnSimulated" onclick="selectMode('simulated')">
        <div class="mode-btn-inner">
          <span class="btn-badge">OFFLINE</span>
          <span class="btn-icon">🧪</span>
          <span class="btn-title">SIMULATED</span>
          <span class="btn-desc">IDW SPATIAL ENGINE<br>RAINFALL · YAMUNA STAGE<br>ENSEMBLE SCORE · READINESS<br>NDRF DISPATCH ACTIVE</span>
        </div>
      </button>
      <button class="mode-btn" id="btnReal" onclick="selectMode('real')">
        <div class="mode-btn-inner">
          <span class="btn-badge">● LIVE</span>
          <span class="btn-icon">🛰️</span>
          <span class="btn-title">REAL</span>
          <span class="btn-desc">OPEN-METEO · IMD FEEDS<br>9-SIGNAL ENSEMBLE MODEL<br>HATHNI KUND · DEM · ALGO<br>ALERT SYSTEM ACTIVE</span>
        </div>
      </button>
    </div>
    <div class="modal-footer">SELECT OPERATIONAL MODE TO INITIALIZE ENGINE</div>
  </div>
  <div id="connectingState" style="display:none;flex-direction:column;align-items:center;gap:16px;">
    <div class="connect-spinner"></div>
    <div class="connect-label" id="connectTitle">INITIALIZING</div>
    <div class="connect-log" id="connectLog"></div>
    <div class="modal-footer" style="margin-top:10px;" id="connectFooter">PLEASE WAIT...</div>
  </div>
</div>
<div id="modeBadge"></div>
<script>
  window.FLOOD_MODE = null; window.simNodeLookup = {};
  function selectMode(mode){
    window.FLOOD_MODE = mode;
    document.getElementById('selectorState').style.display='none';
    document.getElementById('connectingState').style.display='flex';
    if(mode==='simulated'){
      document.getElementById('connectTitle').innerText='LOADING SIMULATION ENGINE';
      document.getElementById('connectFooter').innerText='IDW SPATIAL ENGINE · OFFLINE';
      const logs=['▸ Seeding 20 grid centroids with base rainfall...',
        '▸ Applying spatial gaussian noise (±35%)...',
        '▸ Running IDW interpolation across 2500 nodes...',
        '▸ Computing 4-signal ensemble scores...',
        '▸ Calculating Yamuna proximity surcharge...',
        '▸ Evaluating drain capacity & maintenance factors...',
        '<span style="color:#00ffcc">✓ SIMULATION ENGINE READY</span>'];
      let i=0; document.getElementById('connectLog').innerHTML='';
      const iv=setInterval(()=>{
        document.getElementById('connectLog').innerHTML+=logs[i]+'<br>'; i++;
        if(i>=logs.length){clearInterval(iv);setTimeout(()=>{
          dismissOverlay();showBadge('simulated','🧪 SIMULATED MODE');
                    setTimeout(()=>updateSim(),400);
          fetchLiveProof();
        },600);}

      },450);
    } else {
      document.getElementById('connectTitle').innerText='INITIALIZING LIVE FEEDS';
      document.getElementById('connectFooter').innerText='OPEN-METEO + IMD · FREE · NO API KEY';
      const logs=['▸ Querying Open-Meteo for 20 Delhi grid centroids...',
        '▸ Fetching IMD district rainfall (Delhi ID: 164)...',
        '▸ Blending Open-Meteo (60%) + IMD (40%)...',
        '▸ Running IDW interpolation to 1250 real nodes...',
        '▸ Pinging CWC Hathni Kund discharge...',
        '▸ Loading DEM elevation lookup...',
        '▸ Running 9-signal ensemble engine...',
        '<span style="color:#df00ff">✓ ALL FEEDS CONNECTED</span>'];
      let i=0; document.getElementById('connectLog').innerHTML='';
      const iv=setInterval(()=>{
        document.getElementById('connectLog').innerHTML+=logs[i]+'<br>'; i++;
        if(i>=logs.length){clearInterval(iv);setTimeout(()=>{
          dismissOverlay();showBadge('real','🛰️ REAL MODE · LIVE');
                    if(typeof window.initRealMode==='function') window.initRealMode();
          fetchLiveProof();
        },800);}

      },550);
    }
  }
  function dismissOverlay(){
    const o=document.getElementById('modeOverlay');
    o.style.transition='opacity .5s ease,transform .5s ease';
    o.style.opacity='0';o.style.transform='scale(1.02)';
    setTimeout(()=>{o.style.display='none';},500);
  }
  function showBadge(mode,label){
    const b=document.getElementById('modeBadge');b.className=mode;b.innerText=label;b.style.display='block';
  }
</script>
"""


# ── DASHBOARD (with search bar) ───────────────────────────────────────────────
dashboard_html = f"""
<div style="position:fixed;top:15px;left:15px;width:375px;max-height:94vh;overflow-y:auto;
  background:rgba(10,10,15,0.98);color:#fff;z-index:999999 !important;padding:20px;
  border-radius:12px;font-family:'Segoe UI',sans-serif;border:1px solid #444;
  box-shadow:0 10px 30px rgba(0,0,0,.5);">

  <div style="font-size:24px;font-weight:bold;color:#00ffcc;margin-bottom:2px;" id="liveClock">00:00:00</div>
  <div style="font-size:10px;color:#888;letter-spacing:1px;margin-bottom:10px;">URBAN FLOODING &amp; HYDROLOGY ENGINE</div>

  <!-- ── SEARCH BAR ── -->
  <div style="position:relative;margin-bottom:12px;">
    <div style="display:flex;align-items:center;background:#111;border:1px solid #333;
      border-radius:8px;padding:8px 12px;gap:8px;transition:border-color .2s;"
      id="searchBox">
      <span style="font-size:14px;">🔍</span>
      <input type="text" id="searchInput" placeholder="Search DigiPIN or locality (e.g. lajpat, DL-86)..."
        autocomplete="off"
        style="background:transparent;border:none;outline:none;color:#fff;font-size:11px;
               font-family:'Courier New',monospace;width:100%;letter-spacing:.5px;"
        oninput="onSearchInput(this.value)"
        onkeydown="onSearchKey(event)"
        onfocus="document.getElementById('searchBox').style.borderColor='#00ffcc'"
        onblur="setTimeout(()=>{{document.getElementById('searchBox').style.borderColor='#333';hideSuggestions();}},200)">
      <span id="searchClear" onclick="clearSearch()"
        style="cursor:pointer;color:#556;font-size:16px;display:none;">✕</span>
    </div>
    <!-- Suggestions dropdown -->
    <div id="searchSuggestions"
      style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;
             background:#0d0d14;border:1px solid #333;border-radius:8px;
             z-index:9999999;max-height:220px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.6);">
    </div>
  </div>

  <!-- Search result card -->
  <div id="searchResultCard" style="display:none;background:#0d1a14;border:1px solid #00ffcc44;
    border-radius:8px;padding:12px;margin-bottom:10px;font-size:11px;font-family:'Courier New',monospace;">
  </div>

  <div id="dataSourceTag" style="font-size:9px;font-family:'Courier New',monospace;color:#556;
    letter-spacing:2px;margin-bottom:12px;padding:6px 10px;background:#111;
    border-radius:4px;border:1px solid #222;">⬛ SELECT MODE TO BEGIN</div>

  <!-- READINESS -->
  <div style="background:linear-gradient(90deg,#111,#222);padding:15px;border-radius:8px;
    margin-bottom:8px;border:1px solid #00ffcc;text-align:center;">
    <div style="font-size:10px;color:#00ffcc;text-transform:uppercase;letter-spacing:1px;">Avg Zonal Readiness</div>
    <div style="font-size:38px;font-weight:bold;margin:4px 0;" id="avgReadiness">—</div>
    <div style="font-size:9px;color:#556;">Structural + Maintenance + Spatial Load</div>
  </div>

  <!-- ENSEMBLE + CRITICAL -->
  <div style="background:#111;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #333;
    display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-size:9px;color:#ffaa00;letter-spacing:2px;">ENSEMBLE SCORE</div>
      <div style="font-size:22px;font-weight:bold;color:#ffaa00;" id="ensembleScore">—</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:9px;color:#ff6666;letter-spacing:2px;">CRITICAL ZONES</div>
      <div style="font-size:22px;font-weight:bold;color:#ff6666;" id="criticalCount">—</div>
    </div>
  </div>
  <!-- HATHNI KUND WIDGET -->
<div id="hkWidget" style="background:#060d14;border:1px solid #00aaff44;
  border-radius:8px;padding:14px;margin-bottom:10px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;width:60%;height:2px;
    background:linear-gradient(90deg,transparent,#00aaff,#00ffcc,transparent);
    animation:hkScan 3s linear infinite;"></div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div style="font-size:10px;color:#00aaff;letter-spacing:2px;
      font-family:'Courier New',monospace;">🌊 HATHNI KUND BARRAGE</div>
    <div id="hkAlertBadge" style="font-size:9px;padding:3px 8px;border-radius:3px;
      background:rgba(0,255,204,.1);border:1px solid rgba(0,255,204,.3);
      color:#00ffcc;font-family:'Courier New',monospace;">LOADING...</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;
    font-family:'Courier New',monospace;margin-bottom:10px;">
    <div style="background:#0a0a12;padding:8px;border-radius:6px;border:1px solid #1a2a3a;">
      <div style="color:#556;font-size:9px;margin-bottom:3px;">DISCHARGE</div>
      <div style="color:#00aaff;font-weight:bold;font-size:13px;" id="hkDischarge">—</div>
      <div style="color:#334;font-size:8px;" id="hkLakh">— lakh cusecs</div>
    </div>
    <div style="background:#0a0a12;padding:8px;border-radius:6px;border:1px solid #1a2a3a;">
      <div style="color:#556;font-size:9px;margin-bottom:3px;">PRED. DELHI STAGE</div>
      <div style="color:#ffcc00;font-weight:bold;font-size:13px;" id="hkStage">—</div>
      <div style="color:#334;font-size:8px;">danger &gt; 205.3m</div>
    </div>
    <div style="background:#0a0a12;padding:8px;border-radius:6px;border:1px solid #1a2a3a;">
      <div style="color:#556;font-size:9px;margin-bottom:3px;">DELHI ETA</div>
      <div style="color:#ff6666;font-weight:bold;font-size:13px;" id="hkETA">—</div>
      <div style="color:#556;font-size:8px;" id="hkETACountdown">computing...</div>
    </div>
    <div style="background:#0a0a12;padding:8px;border-radius:6px;border:1px solid #1a2a3a;">
      <div style="color:#556;font-size:9px;margin-bottom:3px;">TREND</div>
      <div style="color:#00ffcc;font-weight:bold;font-size:13px;" id="hkTrend">—</div>
      <div style="color:#334;font-size:8px;" id="hkSource">CWC data</div>
    </div>
  </div>
  <!-- Scenario dropdown — visible in simulated mode only -->
  <div id="hkScenarioPanel">
    <div style="font-size:9px;color:#445;letter-spacing:1px;margin-bottom:5px;">
      🎛️ SCENARIO PRESET</div>
    <select id="hkScenario" onchange="applyHKScenario()"
      style="width:100%;background:#0a0a12;color:#00aaff;padding:8px;
      border-radius:4px;font-size:10px;font-family:'Courier New',monospace;
      border:1px solid #1a3a5a;cursor:pointer;">
      <option value="0">🟢 NORMAL — &lt;10k cusecs (Stage ~203.8m)</option>
      <option value="50000">🔵 ADVISORY — 50k cusecs (Stage ~204.8m)</option>
      <option value="100000">🟡 WARNING — 1 lakh cusecs (Stage ~205.8m)</option>
      <option value="200000">🟠 DANGER — 2 lakh cusecs (Stage ~206.5m)</option>
      <option value="350000">🔴 SEVERE — 3.5 lakh cusecs (Stage ~207.5m)</option>
    </select>
  </div>
  <!-- Auto-apply toggle — visible in real mode only -->
  <div id="hkAutoApplyPanel" style="display:none;margin-top:8px;">
    <div style="display:flex;align-items:center;justify-content:space-between;
      font-size:10px;color:#556;">
      <span>Auto-apply HK stage to engine</span>
      <input type="checkbox" id="hkAutoApply" checked onchange="applyHKToEngine()">
    </div>
  </div>
  <div style="font-size:8px;color:#334;margin-top:8px;text-align:right;"
    id="hkFetchedAt">—</div>
</div>
<div id="hkAlertBanner" style="display:none;"></div>

  <!-- SIGNALS -->
  <div style="background:#0a0a0a;padding:12px;border-radius:8px;margin-bottom:10px;border:1px solid #222;">
    <div style="font-size:9px;color:#556;letter-spacing:2px;margin-bottom:8px;">📡 ENGINE SIGNALS</div>
    <div style="font-size:11px;color:#aaa;line-height:2.4;">
      <span style="color:#556;">🌧️ Rainfall Base:</span><span id="sig1val" style="color:#00ffcc;float:right;">—</span><br>
      <span style="color:#556;">🌊 River Stage:</span><span id="sig2val" style="color:#00aaff;float:right;">—</span><br>
      <span style="color:#556;">⚙️ Drain Efficiency:</span><span id="sig3val" style="color:#ffaa00;float:right;">—</span><br>
      <span style="color:#556;">📊 Avg Ensemble:</span><span id="sig4val" style="color:#df00ff;float:right;">—</span>
    </div>
  </div>

  <!-- SLIDERS -->
  <div id="sliderPanel">
    <div style="background:#1a1a1a;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #333;">
      <label style="font-size:12px;font-weight:bold;display:block;margin-bottom:5px;">
        🌧️ BASE RAINFALL: <span id="rainDisp" style="color:#00ffcc">10 mm/hr</span>
      </label>
      <input type="range" min="0" max="150" value="10" id="rainSlider" style="width:100%;cursor:pointer;">
      <div style="display:flex;justify-content:space-between;font-size:9px;color:#445;margin-top:2px;">
        <span>0</span><span>Moderate 50</span><span>Extreme 150</span>
      </div>
    </div>
    <div style="background:#1a1a1a;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #333;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <label style="font-size:12px;font-weight:bold;">🌊 YAMUNA OVERFLOW</label>
        <input type="checkbox" id="toggleRiver" onchange="updateSim()">
      </div>
      <label style="font-size:11px;color:#00aaff;margin-top:5px;display:block;">
        Stage: <span id="riverDisp">204.0 m</span>
        <span style="font-size:9px;color:#445;margin-left:8px;">(danger &gt;205.3m)</span>
      </label>
      <input type="range" min="203" max="209" value="204" step="0.1" id="riverSlider" style="width:100%;cursor:pointer;">
    </div>
    <div style="background:#1a1a1a;padding:12px;border-radius:8px;margin-bottom:14px;border:1px solid #333;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <label style="font-size:12px;font-weight:bold;">⚠️ INFRASTRUCTURE</label>
        <input type="checkbox" id="toggleMaint" onchange="updateSim()">
      </div>
      <select id="trashStatus" onchange="updateSim()"
        style="width:100%;background:#000;color:#ffaa00;padding:8px;border-radius:4px;font-size:11px;margin-bottom:8px;">
        <option value="1">TRASH RACKS: CLEAR (1×)</option>
        <option value="1.5">TRASH RACKS: PARTIAL (1.5×)</option>
        <option value="2.5">TRASH RACKS: BLOCKED (2.5×)</option>
      </select>
      <label style="font-size:10px;color:#888;display:block;margin-bottom:4px;">
        Silt Factor: <span id="siltDisp" style="color:#ffaa00;">1.0×</span>
      </label>
      <input type="range" min="1" max="4" value="1" step="0.5" id="siltSlider"
        style="width:100%;cursor:pointer;"
        oninput="document.getElementById('siltDisp').innerText=this.value+'×';updateSim()">
    </div>
  </div>

  <div id="realExtraPanel" style="display:none;">
    <div style="background:#0d1a0d;padding:12px;border-radius:8px;margin-bottom:10px;border:1px solid #00ffcc22;">
      <div style="font-size:9px;color:#00ffcc;letter-spacing:2px;margin-bottom:6px;">🛰️ LIVE SOURCE DETAILS</div>
      <div style="font-size:10px;color:#667;line-height:2;">
        Open-Meteo: <span id="omDetail" style="color:#00ffcc;">—</span><br>
        IMD District: <span id="imdDetail" style="color:#00ffcc;">—</span><br>
        Hathni Kund: <span id="hkDetail" style="color:#00aaff;">Step 4 →</span>
      </div>
    </div>
  </div>

  <button onclick="sendEmergencyDispatch()" id="dispatchBtn"
    style="width:100%;padding:14px;background:linear-gradient(135deg,#8f00ff,#5500aa);
    color:#fff;font-weight:bold;font-size:14px;border:none;border-radius:8px;cursor:pointer;
    display:none;margin-bottom:8px;letter-spacing:1px;animation:pulseBorder 1.5s infinite;">
    🚨 DISPATCH NDRF
  </button>
  <button onclick="sendMorningBrief()"
  style="width:100%;padding:10px;background:#0a1a2a;color:#00aaff;
  border:1px solid #00aaff44;border-radius:6px;font-size:11px;
  cursor:pointer;margin-bottom:8px;letter-spacing:1px;display:none;"
  id="morningBriefBtn">
  📋 MORNING BRIEF
</button>

    <!-- ══ LIVE ENGINE PROOF WIDGET ══ -->
  <div id="liveProofWidget" style="background:#060d14;border:1px solid #00ffcc33;
    border-radius:8px;padding:14px;margin-bottom:10px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <div style="font-size:10px;color:#00ffcc;letter-spacing:2px;
        font-family:'Courier New',monospace;">🛰️ LIVE ENGINE PROOF</div>
      <div id="liveProofBadge" style="font-size:9px;padding:3px 8px;border-radius:3px;
        background:rgba(0,255,204,.1);border:1px solid rgba(0,255,204,.3);
        color:#00ffcc;font-family:'Courier New',monospace;
        animation:badgePulse 2s ease-in-out infinite;">FETCHING...</div>
    </div>
    <div id="liveProofCards" style="display:flex;flex-direction:column;gap:6px;
      margin-bottom:10px;">
      <!-- cards injected by JS -->
      <div style="color:#334;font-size:10px;font-family:'Courier New',monospace;
        text-align:center;padding:10px;">Loading live data...</div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div style="font-size:8px;color:#334;font-family:'Courier New',monospace;"
        id="liveProofSource">Source: Open-Meteo Free API</div>
      <button onclick="refreshLiveProof()"
        style="background:#00ffcc11;border:1px solid #00ffcc44;color:#00ffcc;
        font-size:9px;padding:4px 10px;border-radius:4px;cursor:pointer;
        font-family:'Courier New',monospace;letter-spacing:1px;">
        🔄 REFRESH</button>
    </div>
  </div>

  <button onclick="exportToKepler()" id="keplerBtn"
    style="width:100%;padding:12px;background:#00ffcc;color:#000;font-weight:bold;
    border:none;border-radius:8px;cursor:pointer;font-size:13px;">
    📥 EXPORT FOR KEPLER.GL
  </button>

  <style>
    @keyframes pulseBorder{{0%,100%{{box-shadow:0 0 0 0 rgba(143,0,255,.4)}}50%{{box-shadow:0 0 0 8px rgba(143,0,255,0)}}}}
    #searchSuggestions::-webkit-scrollbar{{width:4px}}
    #searchSuggestions::-webkit-scrollbar-track{{background:#111}}
    #searchSuggestions::-webkit-scrollbar-thumb{{background:#333;border-radius:2px}}
    .search-suggestion{{padding:10px 14px;cursor:pointer;font-size:11px;
      font-family:'Courier New',monospace;border-bottom:1px solid #1a1a1a;
      display:flex;justify-content:space-between;align-items:center;transition:background .15s;}}
    .search-suggestion:hover,.search-suggestion.active{{background:#1a2a1a;}}
    .search-suggestion:last-child{{border-bottom:none;}}
    .sug-digipin{{color:#00ffcc;font-weight:bold;}}
    .sug-loc{{color:#ffaa00;}}
    .sug-meta{{color:#556;font-size:9px;}}
    .nearby-chip{{display:inline-block;background:#111;border:1px solid #333;
      border-radius:4px;padding:3px 8px;margin:3px 3px 0 0;font-size:9px;
      font-family:'Courier New',monospace;cursor:pointer;color:#00ffcc;transition:background .15s;}}
    .nearby-chip:hover{{background:#1a2a1a;border-color:#00ffcc44;}}
    #searchInput::placeholder{{color:#334;}}
  </style>
</div>

<script>
  // ── DATA embedded from Python ──────────────────────────────────────────────
  const NODE_REGISTRY  = {NODE_REGISTRY_JSON};
  const LOCALITIES     = {LOCALITIES_JSON};

  // Runtime state
  window.FLOOD_MODE    = null;
  window.simNodeLookup = {{}};
  window.lastSimData   = {{}};
  window._searchHighlightLayer = null;
  let _suggestIndex = -1;

  setInterval(()=>{{ document.getElementById('liveClock').innerText = new Date().toLocaleTimeString(); }}, 1000);
  window.allDataQueue = []; window.violetQueue = [];

  // ── HAVERSINE (JS) ──────────────────────────────────────────────────────────
  function jsHaversine(lat1,lon1,lat2,lon2){{
    const R=6372.8, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180;
    const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
    return 2*R*Math.asin(Math.sqrt(a));
  }}
  
  

  // ── SEARCH LOGIC ────────────────────────────────────────────────────────────
  function onSearchInput(val){{
    const v = val.trim().toLowerCase();
    document.getElementById('searchClear').style.display = v ? 'block' : 'none';
    if(!v){{ hideSuggestions(); clearResultCard(); return; }}
    const suggestions = getSuggestions(v);
    renderSuggestions(suggestions);
  }}

  function getSuggestions(query){{
    const results = [];

    // 1. DigiPIN prefix/substring match (case insensitive)
    for(const node of NODE_REGISTRY){{
      if(node.digipin.toLowerCase().includes(query)){{
        results.push({{ type:'digipin', node, label: node.digipin,
          meta: node.zone + ' · ' + node.lat.toFixed(3) + ', ' + node.lng.toFixed(3) }});
        if(results.length >= 4) break;
      }}
    }}

    // 2. Locality name match
    for(const [name, coords] of Object.entries(LOCALITIES)){{
      if(name.includes(query)){{
        // Find nearest node to this locality
        let nearest = null, minDist = Infinity;
        for(const node of NODE_REGISTRY){{
          const d = jsHaversine(coords[0], coords[1], node.lat, node.lng);
          if(d < minDist){{ minDist = d; nearest = node; }}
        }}
        if(nearest){{
          results.push({{ type:'locality', node: nearest,
            label: name.replace(/\b\w/g,c=>c.toUpperCase()),
            meta: nearest.digipin + ' · ' + minDist.toFixed(2) + ' km away',
            localityCoords: coords }});
        }}
        if(results.length >= 8) break;
      }}
    }}

    // 3. Raw coordinates: "28.61, 77.24"
    const coordMatch = query.match(/(-?[\d.]+)\s*[,\s]\s*(-?[\d.]+)/);
    if(coordMatch){{
      const qlat = parseFloat(coordMatch[1]), qlng = parseFloat(coordMatch[2]);
      if(qlat > 28.3 && qlat < 28.95 && qlng > 76.8 && qlng < 77.5){{
        let nearest = null, minDist = Infinity;
        for(const node of NODE_REGISTRY){{
          const d = jsHaversine(qlat, qlng, node.lat, node.lng);
          if(d < minDist){{ minDist = d; nearest = node; }}
        }}
        if(nearest) results.unshift({{ type:'coords', node: nearest,
          label: '📍 ' + qlat.toFixed(4) + ', ' + qlng.toFixed(4),
          meta: nearest.digipin + ' · ' + minDist.toFixed(2) + ' km' }});
      }}
    }}

    return results.slice(0, 6);
  }}

  function renderSuggestions(suggestions){{
    const box = document.getElementById('searchSuggestions');
    if(!suggestions.length){{ box.style.display='none'; return; }}
    box.innerHTML = suggestions.map((s,i) => `
      <div class="search-suggestion" data-idx="${{i}}"
        onmousedown="selectSuggestion(${{i}})"
        onmouseover="setActiveSug(${{i}})">
        <div>
          <span class="${{s.type==='digipin'?'sug-digipin':'sug-loc'}}">${{s.label}}</span>
          <div class="sug-meta">${{s.meta}}</div>
        </div>
        <span style="font-size:10px;color:#334;">
          ${{s.type==='digipin'?'📍':s.type==='locality'?'🏙️':'🗺️'}}
        </span>
      </div>`).join('');
    box._suggestions = suggestions;
    _suggestIndex = -1;
    box.style.display = 'block';
  }}

  function setActiveSug(i){{
    _suggestIndex = i;
    document.querySelectorAll('.search-suggestion').forEach((el,j)=>
      el.classList.toggle('active', j===i));
  }}

  function onSearchKey(e){{
    const box = document.getElementById('searchSuggestions');
    const items = document.querySelectorAll('.search-suggestion');
    if(e.key==='ArrowDown'){{ e.preventDefault(); setActiveSug(Math.min(_suggestIndex+1,items.length-1)); }}
    else if(e.key==='ArrowUp'){{ e.preventDefault(); setActiveSug(Math.max(_suggestIndex-1,0)); }}
    else if(e.key==='Enter'){{ e.preventDefault(); if(_suggestIndex>=0) selectSuggestion(_suggestIndex); }}
    else if(e.key==='Escape'){{ hideSuggestions(); clearResultCard(); }}
  }}

  function selectSuggestion(i){{
    const box  = document.getElementById('searchSuggestions');
    const sugg = box._suggestions[i];
    if(!sugg) return;
    document.getElementById('searchInput').value = sugg.label;
    document.getElementById('searchClear').style.display = 'block';
    hideSuggestions();
    flyToNode(sugg.node, sugg.label);
  }}

  function hideSuggestions(){{
    document.getElementById('searchSuggestions').style.display='none';
  }}

  function clearSearch(){{
    document.getElementById('searchInput').value='';
    document.getElementById('searchClear').style.display='none';
    hideSuggestions(); clearResultCard(); removeHighlight();
  }}

  function clearResultCard(){{
    document.getElementById('searchResultCard').style.display='none';
  }}

  // ── FLY TO NODE + HIGHLIGHT ────────────────────────────────────────────────
  function flyToNode(node, label){{
    const map = window._leafletMap || getLeafletMap();
    if(!map) return;

    // Fly to node
    map.flyTo([node.lat, node.lng], 15, {{animate:true, duration:1.2}});

    // Remove old highlight
    removeHighlight();

    // Pulsing highlight ring
    const ring = L.circleMarker([node.lat, node.lng], {{
      radius: 22, color: '#00ffcc', weight: 3,
      fill: false, opacity: 1, className: 'search-highlight-ring'
    }}).addTo(map);

    const ring2 = L.circleMarker([node.lat, node.lng], {{
      radius: 14, color: '#ffffff', weight: 2,
      fill: true, fillColor:'#00ffcc', fillOpacity: 0.25, opacity: 0.8
    }}).addTo(map);

    window._searchHighlightLayer = {{ ring, ring2, map }};

    // Pulse animation via DOM
    setTimeout(()=>{{
      const els = document.querySelectorAll('.search-highlight-ring');
      els.forEach(el=>{{
        el.style.animation='searchPulse 1.2s ease-in-out 3';
      }});
    }}, 100);

    // Show result card
    showResultCard(node, label);
  }}

  function removeHighlight(){{
    if(window._searchHighlightLayer){{
      const {{ring, ring2, map}} = window._searchHighlightLayer;
      try{{ map.removeLayer(ring); map.removeLayer(ring2); }} catch(e){{}}
      window._searchHighlightLayer = null;
    }}
  }}

  // ── RESULT CARD ────────────────────────────────────────────────────────────
  function showResultCard(node, label){{
    const card = document.getElementById('searchResultCard');

    // Get live sim data if available
    const liveKey = node.lat.toFixed(5)+'_'+node.lng.toFixed(5);
    const live = window.simNodeLookup[liveKey] || {{}};

    const fl  = live.flood_load !== undefined ? live.flood_load.toFixed(1)+' mm' : '—';
    const rd  = live.readiness  !== undefined ? live.readiness.toFixed(0)+'%'   : '—';
    const ens = live.ensemble   !== undefined ? live.ensemble.toFixed(1)+'/100' : '—';
    const sr  = live.rain_mm    !== undefined ? live.rain_mm.toFixed(1)+' mm/hr': '—';

    const rdColor = live.readiness !== undefined
      ? (live.readiness < 40 ? '#ff4444' : live.readiness < 75 ? '#ffaa00' : '#00ffcc')
      : '#556';
    const flColor = live.flood_load !== undefined
      ? (live.flood_load > 80 ? '#df00ff' : live.flood_load > 40 ? '#ff4444' : live.flood_load > 10 ? '#ffcc00' : '#00ff00')
      : '#556';

    // Find 3 nearest nodes
    const distances = NODE_REGISTRY
      .filter(n => n.digipin !== node.digipin)
      .map(n => ({{ ...n, dist: jsHaversine(node.lat, node.lng, n.lat, n.lng) }}))
      .sort((a,b) => a.dist - b.dist).slice(0, 3);

    const nearbyChips = distances.map(n =>
      `<span class="nearby-chip" onclick="flyToNode(${{JSON.stringify(n).replace(/'/g,'&apos;')}},'${{n.digipin}}')"
        title="${{n.digipin}} · ${{n.dist.toFixed(2)}} km">${{n.digipin}}</span>`
    ).join('');

    card.innerHTML = `
      <div style="color:#00ffcc;font-size:13px;font-weight:bold;letter-spacing:1px;margin-bottom:6px;">
        📍 ${{node.digipin}}</div>
      <div style="color:#556;font-size:9px;margin-bottom:8px;">${{node.lat}}° N, ${{node.lng}}° E</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:10px;margin-bottom:8px;">
        <div>🏙️ <span style="color:#ffcc00;">${{node.zone}}</span></div>
        <div>⚡ Vuln: <span style="color:#ff6666;">${{(node.vuln*100).toFixed(0)}}%</span></div>
        <div>🚰 Cap: <span style="color:#00ffcc;">${{node.cap}} mm/hr</span></div>
        <div>🌊 River: <span style="color:#00aaff;">${{node.dist_r}} km</span></div>
        <div>💧 Rain: <span style="color:#00aaff;">${{sr}}</span></div>
        <div>🌊 Load: <span style="color:${{flColor}};">${{fl}}</span></div>
        <div>📊 Ens: <span style="color:#ffaa00;">${{ens}}</span></div>
        <div>🛡️ Ready: <span style="color:${{rdColor}};">${{rd}}</span></div>
      </div>
      <div style="font-size:9px;color:#667;border-top:1px solid #1a2a1a;padding-top:6px;margin-bottom:6px;">
        🚁 ${{node.camp}} &nbsp;·&nbsp; ${{node.camp_dist}} km
      </div>
      <div style="font-size:9px;color:#445;margin-bottom:4px;">NEARBY NODES:</div>
      <div>${{nearbyChips}}</div>`;

    card.style.display = 'block';
  }}

  // ── GET LEAFLET MAP INSTANCE ───────────────────────────────────────────────
  function getLeafletMap(){{
    for(const key of Object.keys(window)){{
      if(window[key] && window[key]._leaflet_id !== undefined && window[key].flyTo) {{
        window._leafletMap = window[key]; return window[key];
      }}
    }}
    // fallback: find from container
    const containers = document.querySelectorAll('.leaflet-container');
    if(containers.length){{
      const id = containers[0]._leaflet_id;
      return L._map || null;
    }}
    return null;
  }}

  // try getting map after load
  setTimeout(()=>{{ getLeafletMap(); }}, 2000);

  // ── FLOOD COLOR UTILS ──────────────────────────────────────────────────────
  function floodColor(v){{ if(v>80)return'#df00ff'; if(v>40)return'#ff0000'; if(v>10)return'#ffcc00'; return'#00ff00'; }}
  function riskLabel(v){{
    if(v>80)return'<span style="color:#df00ff">● CRITICAL</span>';
    if(v>40)return'<span style="color:#ff4444">● HIGH</span>';
    if(v>10)return'<span style="color:#ffcc00">● MODERATE</span>';
    return'<span style="color:#00ff00">● LOW</span>';
  }}
  function readinessColor(r){{ return r<40?'#ff0000':r<75?'#ffaa00':'#00ffcc'; }}

  // ── SIMULATED UPDATE ───────────────────────────────────────────────────────
  function updateSim(){{
  if (window.FLOOD_MODE === 'simulated' && document.getElementById('hkScenarioPanel'))
        document.getElementById('hkScenarioPanel').style.display = 'block';
  
    if(window.FLOOD_MODE==='real') return;
    const rain        = parseFloat(document.getElementById('rainSlider').value);
    const river       = parseFloat(document.getElementById('riverSlider').value);
    const silt        = parseFloat(document.getElementById('siltSlider').value);
    const trash       = parseFloat(document.getElementById('trashStatus').value);
    const enableRiver = document.getElementById('toggleRiver').checked;
    const enableMaint = document.getElementById('toggleMaint').checked;
    document.getElementById('rainDisp').innerText  = rain + ' mm/hr';
    document.getElementById('riverDisp').innerText = enableRiver ? river.toFixed(1)+' m' : 'Disabled';

    fetch('/api/sim_rainfall', {{
      method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{base_rain:rain, river_stage:river, silt:silt, trash:trash,
                             enable_river:enableRiver, enable_maint:enableMaint}})
    }})
    .then(r=>r.json())
    .then(data=>{{
      const lookup = {{}};
      (data.nodes||[]).forEach(n=>{{ lookup[n.lat.toFixed(5)+'_'+n.lng.toFixed(5)] = n; }});
      window.simNodeLookup = lookup;
      window.lastSimData   = data;

      const nodes = document.querySelectorAll('.node');
      const currentAll=[], currentViolet=[];

      nodes.forEach(node=>{{
        const cls     = node.className.baseVal.split(' ');
        const nodeIdx = parseInt(cls[5].split('-')[1]);
        const dataTag = node.className.baseVal.split('data-')[1];
        if(!dataTag) return;
        const parts = dataTag.split('_');
        const lat = parseFloat(parts[0]), lng = parseFloat(parts[1]);
        const key = lat.toFixed(5)+'_'+lng.toFixed(5);
        const nd  = lookup[key];
        if(!nd) return;

        node.setAttribute('fill', floodColor(nd.flood_load));
        node.setAttribute('fill-opacity', nd.flood_load>5?'1':'0.7');

        const flEl=document.getElementById('fl_'+nodeIdx);
        const rdEl=document.getElementById('rd_'+nodeIdx);
        const srEl=document.getElementById('sr_'+nodeIdx);
        const esEl=document.getElementById('es_'+nodeIdx);
        if(srEl) srEl.innerText = nd.rain_mm.toFixed(1)+' mm/hr (spatial)';
        if(flEl) flEl.innerHTML = nd.flood_load.toFixed(1)+' — '+riskLabel(nd.flood_load);
        if(esEl) esEl.innerText = nd.ensemble.toFixed(1)+' / 100';
        if(rdEl){{ rdEl.innerText=nd.readiness.toFixed(0)+'%'; rdEl.style.color=readinessColor(nd.readiness); }}

        currentAll.push(nd);
        if(nd.flood_load>80) currentViolet.push(nd);
      }});

      const avgR = data.avg_readiness;
      document.getElementById('avgReadiness').innerText = Math.round(avgR)+'%';
      document.getElementById('avgReadiness').style.color = readinessColor(avgR);
      document.getElementById('ensembleScore').innerText = data.avg_ensemble+' / 100';
      document.getElementById('criticalCount').innerText = data.critical_count+' zones';
      document.getElementById('dataSourceTag').innerHTML = '🧪 SIMULATED · IDW SPATIAL ENGINE ACTIVE';
      document.getElementById('dataSourceTag').style.color = '#00ffcc';
      document.getElementById('sig1val').innerText = rain+' mm/hr (base)';
      document.getElementById('sig2val').innerText = enableRiver ? river.toFixed(1)+' m' : 'Off';
      document.getElementById('sig3val').innerText = (100/data.maint_factor).toFixed(0)+'%';
      document.getElementById('sig4val').innerText = data.avg_ensemble+' / 100';

      window.allDataQueue=currentAll; window.violetQueue=currentViolet;
      const dBtn=document.getElementById('dispatchBtn');
      if(currentViolet.length>0){{
        dBtn.style.display='block';
        dBtn.innerHTML='🚨 DISPATCH NDRF ('+currentViolet.length+' CRITICAL ZONES)';
      }} else dBtn.style.display='none';

      // Refresh result card if open (live data updated)
      const card = document.getElementById('searchResultCard');
      if(card.style.display!=='none'){{
        const inp = document.getElementById('searchInput').value.trim();
        if(inp) onSearchInput(inp);
      }}
    }})
    .catch(err=>console.error('updateSim error:',err));
        updateDispatchLabel(data.critical_count || 0);
    if(typeof initStep4==='function') initStep4();

  }}

  // ── REAL MODE ──────────────────────────────────────────────────────────────
  window.initRealMode = function(){{
    document.getElementById('hkScenarioPanel').style.display  = 'none';
    document.getElementById('hkAutoApplyPanel').style.display = 'block';
    fetchHKData(() => {{ startHKAutoRefresh(); }});
    document.getElementById('sliderPanel').style.display='none';
    document.getElementById('realExtraPanel').style.display='block';
    document.getElementById('dataSourceTag').innerHTML='🛰️ REAL · OPEN-METEO + IMD + ENSEMBLE';
    document.getElementById('dataSourceTag').style.color='#df00ff';
    fetch('/api/live_rainfall').then(r=>r.json()).then(data=>{{
      if(data.error){{ console.error('Rainfall fetch failed:',data.error); return; }}
      document.getElementById('omDetail').innerText  = (data.avg_om_rain||0).toFixed(1)+' mm/hr';
      document.getElementById('imdDetail').innerText = (data.imd_rain||0).toFixed(1)+' mm/hr';
      const lookup={{}};
      (data.nodes||[]).forEach(n=>{{ lookup[n.lat.toFixed(5)+'_'+n.lng.toFixed(5)]=n.rain_mm; }});
      const nodes=document.querySelectorAll('.node');
      const currentAll=[],currentViolet=[];
      let totalScore=0;
      nodes.forEach(node=>{{
        const dataTag=node.className.baseVal.split('data-')[1]; if(!dataTag) return;
        const cls=node.className.baseVal.split(' ');
        const nodeIdx=parseInt(cls[5].split('-')[1]);
        const parts=dataTag.split('_');
        const lat=parseFloat(parts[0]),lng=parseFloat(parts[1]);
        const key=lat.toFixed(5)+'_'+lng.toFixed(5);
        const rain=(lookup[key]!==undefined)?lookup[key]:(data.avg_blended||0);
        node.setAttribute('fill',rain>50?'#df00ff':rain>20?'#ff0000':rain>5?'#ffcc00':'#00ff00');
        node.setAttribute('fill-opacity',rain>5?'1':'0.7');
        const score=Math.min(rain*2,100); const rs=Math.max(0,100-score); totalScore+=score;
        const flEl=document.getElementById('fl_'+nodeIdx);
        const rdEl=document.getElementById('rd_'+nodeIdx);
        const srEl=document.getElementById('sr_'+nodeIdx);
        const esEl=document.getElementById('es_'+nodeIdx);
        if(srEl) srEl.innerText=rain.toFixed(1)+' mm/hr (live)';
        if(flEl) flEl.innerHTML=rain.toFixed(1)+' mm/hr — '+riskLabel(rain*2);
        if(esEl) esEl.innerText=score.toFixed(1)+' / 100';
        if(rdEl){{ rdEl.innerText=rs.toFixed(0)+'%'; rdEl.style.color=readinessColor(rs); }}
        const nd={{lat,lng,load:rain.toFixed(2),readiness:rs.toFixed(0),
          flood_load:rain,rain_mm:rain,ensemble:score,
          digipin:'DL-'+parts[0].toString().substring(3,5)+parts[1].toString().substring(3,5)}};
        window.simNodeLookup[key]=nd;
        currentAll.push(nd); if(rain>50) currentViolet.push(nd);
      }});
      const avgEnsemble=totalScore/Math.max(nodes.length,1); const avgR=100-avgEnsemble;
      document.getElementById('avgReadiness').innerText=Math.round(avgR)+'%';
      document.getElementById('avgReadiness').style.color=readinessColor(avgR);
      document.getElementById('ensembleScore').innerText=avgEnsemble.toFixed(1)+' / 100';
      document.getElementById('criticalCount').innerText=currentViolet.length+' zones';
      document.getElementById('sig1val').innerText=(data.avg_om_rain||0).toFixed(1)+' mm/hr';
      document.getElementById('sig2val').innerText=data.hk_note||'Step 4';
      document.getElementById('sig3val').innerText='100% (live)';
      document.getElementById('sig4val').innerText=avgEnsemble.toFixed(1)+' / 100';
      window.allDataQueue=currentAll; window.violetQueue=currentViolet;
      const dBtn=document.getElementById('dispatchBtn');
      if(currentViolet.length>0){{ dBtn.style.display='block';
        dBtn.innerHTML='🚨 DISPATCH NDRF ('+currentViolet.length+' CRITICAL ZONES)'; }}
      else dBtn.style.display='none';
    }}).catch(err=>console.error('initRealMode error:',err));
  }};

  document.getElementById('rainSlider').oninput  = updateSim;
  document.getElementById('riverSlider').oninput = updateSim;
    // ── LIVE PROOF WIDGET ────────────────────────────────────────────────────
  function fetchLiveProof(){{
    fetch('/api/live_proof')
      .then(r => r.json())
      .then(data => renderLiveProof(data))
      .catch(() => {{
        document.getElementById('liveProofBadge').innerText = 'OFFLINE';
        document.getElementById('liveProofBadge').style.color = '#ff4444';
      }});
  }}

  function renderLiveProof(data){{
    const badge = document.getElementById('liveProofBadge');
    if(data.engine_live){{
      badge.innerText         = '✅ ENGINE LIVE';
      badge.style.color       = '#00ffcc';
      badge.style.background  = 'rgba(0,255,204,.12)';
      badge.style.borderColor = 'rgba(0,255,204,.4)';
      badge.style.animation   = 'none';
    }} else {{
      badge.innerText         = '⚠️ OFFLINE';
      badge.style.color       = '#ff4444';
      badge.style.animation   = 'none';
    }}

    const weatherIcon = (wcode) => {{
      if(wcode === 0)              return '☀️';
      if(wcode <= 3)               return '⛅';
      if(wcode <= 49)              return '🌫️';
      if(wcode <= 67)              return '🌧️';
      if(wcode <= 77)              return '🌨️';
      if(wcode <= 82)              return '🌦️';
      if(wcode <= 99)              return '⛈️';
      return '🌡️';
    }};

    const rainColor = (mm) => {{
      if(mm > 20)  return '#df00ff';
      if(mm > 10)  return '#ff4444';
      if(mm > 3)   return '#ffcc00';
      if(mm > 0)   return '#00aaff';
      return '#445';
    }};

    const cards = data.locations.map(loc => `
      <div style="background:#0a0a12;border:1px solid ${{loc.rain_mm > 0 ? '#1a3a2a' : '#1a1a2a'}};
        border-radius:6px;padding:10px;display:flex;justify-content:space-between;
        align-items:center;transition:border-color .3s;"
        onmouseover="this.style.borderColor='#00ffcc44'"
        onmouseout="this.style.borderColor='${{loc.rain_mm > 0 ? '#1a3a2a' : '#1a1a2a'}}'">
        <div>
          <div style="font-size:11px;font-weight:bold;color:#fff;
            font-family:'Courier New',monospace;">${{weatherIcon(loc.wcode)}} ${{loc.name}}</div>
          <div style="font-size:9px;color:#556;margin-top:2px;">${{loc.place}} · ${{loc.note}}</div>
          <div style="font-size:9px;color:#445;margin-top:2px;">
            🌡️ ${{loc.temp_c}}°C &nbsp; 💧 ${{loc.humidity}}%</div>
          <div style="font-size:8px;color:#334;margin-top:2px;">⏱️ ${{loc.fetched}}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:20px;font-weight:bold;color:${{rainColor(loc.rain_mm)}};">
            ${{loc.rain_mm}}</div>
          <div style="font-size:8px;color:#445;">mm/hr</div>
          <div style="font-size:9px;margin-top:4px;color:${{loc.status==='live'?'#00ffcc':'#ff4444'}};">
            ${{loc.status === 'live' ? '● LIVE' : '● ERROR'}}</div>
        </div>
      </div>`).join('');

    document.getElementById('liveProofCards').innerHTML = cards;
    document.getElementById('liveProofSource').innerText =
      'Source: ' + data.source + ' · ' + data.fetched_at;
  }}

  function refreshLiveProof(){{
    document.getElementById('liveProofBadge').innerText   = 'FETCHING...';
    document.getElementById('liveProofBadge').style.animation = 'badgePulse 1s infinite';
    document.getElementById('liveProofCards').innerHTML =
      '<div style="color:#334;font-size:10px;font-family:Courier New,monospace;text-align:center;padding:10px;">Fetching live data...</div>';
    fetchLiveProof();
  }}


    function exportToKepler() {{
    if(!window.allDataQueue || !window.allDataQueue.length) {{
      alert('Run simulation first — no data to export!'); return;
    }}
    fetch('/export/kepler', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{nodes: window.allDataQueue}})
    }})
    .then(r => r.blob())
    .then(blob => {{
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = 'delhi_flood_nodes.geojson';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      document.getElementById('keplerBtn').innerText = '✅ DOWNLOADED!';
      setTimeout(()=>document.getElementById('keplerBtn').innerText='📥 EXPORT FOR KEPLER.GL', 3000);
    }})
    .catch(()=> alert('Export failed — check console'));
  }}

  function sendEmergencyDispatch(){{
    const score=document.getElementById('avgReadiness').innerText;
    fetch('/trigger_dispatch',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{nodes:window.violetQueue,score:score,mode:window.FLOOD_MODE}})}})
    .then(r=>r.json())
    .then(()=>{{ document.getElementById('dispatchBtn').innerText='✅ NDRF DISPATCHED · ALERTS SENT'; }});
        if(typeof initStep4==='function') initStep4();

  }}

  // Pulse CSS for search highlight
  const styleEl = document.createElement('style');
  styleEl.textContent = `
    @keyframes searchPulse {{
      0%  {{ stroke-opacity:1; r:22; }}
      50% {{ stroke-opacity:0.3; r:30; }}
      100%{{ stroke-opacity:1; r:22; }}
    }}`;
  document.head.appendChild(styleEl);
</script>
"""

m.get_root().html.add_child(folium.Element(modal_html))
m.get_root().html.add_child(folium.Element(dashboard_html))
m.get_root().html.add_child(folium.Element(
    '<script src="/static/hk_widget.js"></script>'

))
m.get_root().html.add_child(folium.Element(
    '<script src="/static/step4.js"></script>'
))


from flask import send_from_directory

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ── FLASK ROUTES ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return m.get_root().render()

@app.route("/api/sim_rainfall", methods=["POST"])
def sim_rainfall():
    body         = request.json
    base_rain    = float(body.get("base_rain", 10))
    river_stage  = float(body.get("river_stage", 204.0))
    silt         = float(body.get("silt", 1.0))
    trash        = float(body.get("trash", 1.0))
    enable_river = bool(body.get("enable_river", False))
    enable_maint = bool(body.get("enable_maint", False))
    result = compute_simulated_idw(base_rain, river_stage, silt, trash, enable_river, enable_maint)
    return jsonify(result)

@app.route("/api/live_rainfall")
def live_rainfall():
    global _rainfall_cache
    if _rainfall_cache["data"] and (time.time()-_rainfall_cache["ts"]) < CACHE_TTL:
        return jsonify(_rainfall_cache["data"])
    try:
        centroid_data, imd_rain = fetch_grid_rainfall()
        om_vals = [c["rain_mm"] for c in centroid_data]
        avg_om  = float(np.mean(om_vals)) if om_vals else 0.0
        real_df = df.head(1250)
        node_rains = idw_interpolate(real_df["lat"].tolist(), real_df["lng"].tolist(), centroid_data)
        nodes_out = [{"lat": round(r["lat"],5), "lng": round(r["lng"],5),
                      "rain_mm": round(float(node_rains[i]),3)}
                     for i, (_, r) in enumerate(real_df.iterrows())]
        result = {"source":"Open-Meteo+IMD","centroids":centroid_data,"nodes":nodes_out,
                  "avg_om_rain":round(avg_om,3),"avg_blended":round(avg_om,3),
                  "imd_rain":round(imd_rain,3),"hk_note":"Hathni Kund CWC — Step 4",
                  "cache_ttl_sec":CACHE_TTL}
        _rainfall_cache = {"data":result,"ts":time.time()}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/export/kepler", methods=["POST"])
def export_kepler():
    from flask import Response
    import io
    data  = request.json["nodes"]
    dfexp = pd.DataFrame(data)
    gdf   = gpd.GeoDataFrame(
        dfexp,
        geometry=gpd.points_from_xy(dfexp.lng, dfexp.lat),
        crs="EPSG:4326"
    )
    buf = io.StringIO()
    gdf.to_file(buf, driver="GeoJSON")
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=delhi_flood_nodes.geojson"}
    )


@app.route("/trigger_dispatch", methods=["POST"])
def trigger_dispatch():
    nodes  = request.json["nodes"]
    score  = request.json["score"]
    mode   = request.json.get("mode","simulated").upper()
    sorted_nodes = sorted(nodes, key=lambda x: float(x.get("load", x.get("flood_load",0))), reverse=True)[:5]
    alert_msg  = (f"🚨 *CRITICAL FLOOD ALERT — {mode} MODE*\n\n"
                  f"Avg Zonal Readiness: *{score}*\n"
                  f"Critical Zones: *{len(nodes)}*\n\n*Top 5 Hotspots:*\n")
    email_body = f"<h2>🚨 MCD Flood Alert [{mode}]</h2><p>Readiness: {score} | Critical: {len(nodes)}</p><ol>"
    for i, node in enumerate(sorted_nodes):
        camp  = min(RELIEF_CAMPS, key=lambda c: haversine(node["lat"],node["lng"],c["lat"],c["lng"]))
        dist  = haversine(node["lat"],node["lng"],camp["lat"],camp["lng"])
        load  = node.get("load", node.get("flood_load","?"))
        rd    = node.get("readiness","?")
        block = (f"{i+1}. DigiPIN: `{node['digipin']}` | Load: {load} | Readiness: {rd}%\n"
                 f"   📍 `{node['lat']:.5f}, {node['lng']:.5f}`\n"
                 f"   🚁 → {camp['name']} ({camp['type']}) — {dist:.1f} km\n\n")
        alert_msg  += block
        email_body += f"<li><b>{node['digipin']}</b> — Load:{load} — Readiness:{rd}% → {camp['name']} ({dist:.1f}km)</li>"
    requests.post("https://api.telegram.org/bot8686433144:AAF2x7pxOHgxndgo45q9aE42ocPc3gzTdSQ/sendMessage",
                  json={"chat_id":"7938650094","text":alert_msg,"parse_mode":"Markdown"})
    try:
        sender,app_pass,receiver = "vk.meta.1092@gmail.com","mlbi pwqh fcnj abgn","vishnujohri11@gmail.com"
        msg = MIMEMultipart()
        msg["Subject"] = f"🚨 FLOOD ALERT [{mode}] — Readiness {score} — {len(nodes)} Critical Zones"
        msg.attach(MIMEText(email_body+"</ol>","html"))
        with smtplib.SMTP("smtp.gmail.com",587) as server:
            server.starttls(); server.login(sender,app_pass)
            server.send_message(msg, from_addr=sender, to_addrs=receiver)
    except Exception:
        pass
    return jsonify({"status":"success","dispatched":len(nodes)})
@app.route("/api/live_proof")
def live_proof():
    """Fetch live rainfall from 4 diverse Indian locations to prove engine is live."""
    proof_locations = [
        {"name": "Cherrapunji",     "place": "Meghalaya",      "lat": 25.3009, "lng": 91.6962, "note": "Wettest place on Earth"},
        {"name": "Mawsynram",       "place": "Meghalaya",      "lat": 25.2972, "lng": 91.5832, "note": "Highest annual rainfall"},
        {"name": "Mumbai (Colaba)", "place": "Maharashtra",    "lat": 18.9067, "lng": 72.8147, "note": "Coastal monsoon city"},
        {"name": "Delhi (Palam)",   "place": "Delhi NCR",      "lat": 28.5665, "lng": 77.1031, "note": "Command HQ region"},
    ]
    results = []
    for loc in proof_locations:
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={loc['lat']}&longitude={loc['lng']}"
                f"&current=precipitation,rain,showers,temperature_2m,"
                f"relative_humidity_2m,weathercode"
                f"&timezone=Asia%2FKolkata"
            )
            r   = requests.get(url, timeout=8)
            r.raise_for_status()
            c   = r.json().get("current", {})
            rain = round(max(
                float(c.get("precipitation", 0) or 0),
                float(c.get("rain",          0) or 0) +
                float(c.get("showers",       0) or 0)
            ), 2)
            results.append({
                "name":     loc["name"],
                "place":    loc["place"],
                "lat":      loc["lat"],
                "lng":      loc["lng"],
                "note":     loc["note"],
                "rain_mm":  rain,
                "temp_c":   round(float(c.get("temperature_2m",        0) or 0), 1),
                "humidity": round(float(c.get("relative_humidity_2m",  0) or 0), 1),
                "wcode":    int(c.get("weathercode", 0) or 0),
                "status":   "live",
                "fetched":  datetime.utcnow().strftime("%H:%M:%S UTC"),
            })
        except Exception as e:
            results.append({
                "name":    loc["name"],
                "place":   loc["place"],
                "lat":     loc["lat"],
                "lng":     loc["lng"],
                "note":    loc["note"],
                "rain_mm": 0.0,
                "temp_c":  0.0,
                "humidity":0.0,
                "wcode":   0,
                "status":  "error",
                "fetched": datetime.utcnow().strftime("%H:%M:%S UTC"),
            })
        time.sleep(0.1)

    any_live = any(r["status"] == "live" for r in results)
    return jsonify({
        "locations":  results,
        "engine_live": any_live,
        "fetched_at": datetime.utcnow().strftime("%H:%M:%S UTC"),
        "source":     "Open-Meteo Free API · No key required",
    })












@app.route("/api/hathni_kund")
def hathni_kund_api():
    data = get_hk_data()
    return jsonify(data)
# ── STEP 4 ROUTES ──────────────────────────────────────────────────────────────
_last_snapshot = {"data": None}

@app.route("/api/dispatch", methods=["POST"])
def api_dispatch():
    body     = request.json
    hk       = get_hk_data()
    snap     = build_snapshot(body.get("sim_data", {}), hk, body.get("mode","simulated"))
    success  = send_ndrf_dispatch(snap)
    _last_snapshot["data"] = snap
    return jsonify({"success": success, "snapshot": snap})


@app.route("/api/snapshot", methods=["POST"])
def api_snapshot():
    body   = request.json
    hk     = get_hk_data()
    snap   = build_snapshot(body.get("sim_data", {}), hk, body.get("mode","simulated"))
    _last_snapshot["data"] = snap
    return jsonify({"success": True, "ts": snap["timestamp"]})


@app.route("/api/morning_briefing", methods=["POST"])
def api_morning_briefing():
    body    = request.json
    hk      = get_hk_data()
    snap    = build_snapshot(body.get("sim_data",{}), hk, body.get("mode","simulated"))
    success = send_morning_briefing(snap)
    return jsonify({"success": success})


@app.route("/api/ensemble_alert", methods=["POST"])
def api_ensemble_alert():
    body = request.json
    hk   = get_hk_data()
    snap = build_snapshot(body.get("sim_data",{}), hk, body.get("mode","simulated"))
    fired = check_ensemble_alert(snap)
    return jsonify({"fired": fired})


@app.route("/report")
def report_page():
    snap = _last_snapshot["data"]
    if not snap:
        hk   = get_hk_data()
        snap = build_snapshot(
            {"nodes":[], "avg_readiness":0, "avg_ensemble":0,
             "base_rain":0, "river_stage":0, "maint_factor":1},
            hk, "pending"
        )
    return generate_report_html(snap)


if __name__ == "__main__":
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
