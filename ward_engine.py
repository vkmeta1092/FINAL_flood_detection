# ward_engine.py
# ══════════════════════════════════════════════════════════════════════════════
# DELHI DISTRICT-LEVEL PRE-MONSOON READINESS ENGINE
# Aggregates 2500 node scores → 11 Delhi district readiness scores
# Self-contained Blueprint — zero impact on app.py core logic
#
# In app.py add only:
#   from ward_engine import ward_bp, set_node_dataframe, set_last_result
#   app.register_blueprint(ward_bp)
# ══════════════════════════════════════════════════════════════════════════════

from flask import Blueprint, jsonify
import numpy as np

ward_bp = Blueprint("ward_engine", __name__)

# ── Internal state (set by app.py after each compute) ────────────────────────
_last_result = None      # full result dict from compute_simulated_idw()
_node_df     = None      # df from generate_nodes()

def set_last_result(result):
    global _last_result
    _last_result = result

def set_node_dataframe(df):
    global _node_df
    _node_df = df

# ── 11 DELHI DISTRICTS — bounding box definitions ────────────────────────────
# Based on Delhi District boundaries (Revenue Dept, GNCT Delhi)
# Approximate lat/lng polygons — sufficient for node aggregation
DISTRICTS = [
    {
        "name":    "North Delhi",
        "lat_min": 28.75, "lat_max": 28.93,
        "lng_min": 77.14, "lng_max": 77.28,
        "known_risk": "Wazirabad barrage, Yamuna floodplain north"
    },
    {
        "name":    "Northeast Delhi",
        "lat_min": 28.65, "lat_max": 28.88,
        "lng_min": 77.25, "lng_max": 77.35,
        "known_risk": "Mustafabad, Seelampur, Yamuna Pushta, Burari"
    },
    {
        "name":    "Northwest Delhi",
        "lat_min": 28.70, "lat_max": 28.88,
        "lng_min": 76.98, "lng_max": 77.18,
        "known_risk": "Rohini drains, Bhalaswa, Najafgarh drain north"
    },
    {
        "name":    "Shahdara",
        "lat_min": 28.61, "lat_max": 28.72,
        "lng_min": 77.27, "lng_max": 77.35,
        "known_risk": "Shahdara drain, Geeta Colony, Trilokpuri, Gokulpuri"
    },
    {
        "name":    "East Delhi",
        "lat_min": 28.58, "lat_max": 28.68,
        "lng_min": 77.25, "lng_max": 77.35,
        "known_risk": "Patparganj, Mayur Vihar, Kondli drain"
    },
    {
        "name":    "Central Delhi",
        "lat_min": 28.61, "lat_max": 28.70,
        "lng_min": 77.18, "lng_max": 77.27,
        "known_risk": "ITO barrage, Rajghat, Kashmere Gate"
    },
    {
        "name":    "West Delhi",
        "lat_min": 28.62, "lat_max": 28.72,
        "lng_min": 77.07, "lng_max": 77.18,
        "known_risk": "Najafgarh drain, Mangolpuri, Mundka"
    },
    {
        "name":    "New Delhi",
        "lat_min": 28.56, "lat_max": 28.63,
        "lng_min": 77.18, "lng_max": 77.27,
        "known_risk": "India Gate surroundings, Nizamuddin"
    },
    {
        "name":    "South Delhi",
        "lat_min": 28.49, "lat_max": 28.58,
        "lng_min": 77.18, "lng_max": 77.32,
        "known_risk": "Okhla, Badarpur, Sarita Vihar, Agra canal"
    },
    {
        "name":    "Southwest Delhi",
        "lat_min": 28.49, "lat_max": 28.62,
        "lng_min": 77.00, "lng_max": 77.18,
        "known_risk": "Palam drain, Dwarka sectors, Najafgarh basin"
    },
    {
        "name":    "Southeast Delhi",
        "lat_min": 28.40, "lat_max": 28.56,
        "lng_min": 77.18, "lng_max": 77.35,
        "known_risk": "Tughlakabad, Badarpur south, Jasola"
    },
]

def _assign_district(lat, lng):
    """Assign a node to a district by bounding box."""
    for d in DISTRICTS:
        if d["lat_min"] <= lat <= d["lat_max"] and d["lng_min"] <= lng <= d["lng_max"]:
            return d["name"]
    return "Unclassified"

def _risk_label(readiness):
    if readiness < 35:  return "CRITICAL"
    if readiness < 55:  return "HIGH"
    if readiness < 70:  return "MODERATE"
    return "LOW"

def _risk_color(readiness):
    if readiness < 35:  return "#df00ff"
    if readiness < 55:  return "#ff4444"
    if readiness < 70:  return "#ffcc00"
    return "#00ff00"

# ── ROUTE ─────────────────────────────────────────────────────────────────────
@ward_bp.route("/api/ward_scores", methods=["GET"])
def ward_scores():
    if _last_result is None:
        return jsonify({"error": "No simulation data yet. Run simulation first.", "districts": []})

    nodes = _last_result.get("nodes", [])
    if not nodes:
        return jsonify({"error": "Empty node list.", "districts": []})

    # Group nodes by district
    district_buckets = {d["name"]: [] for d in DISTRICTS}
    district_buckets["Unclassified"] = []

    for node in nodes:
        dist = _assign_district(node["lat"], node["lng"])
        district_buckets[dist].append(node)

    scores = []
    for d in DISTRICTS:
        bucket = district_buckets[d["name"]]
        if not bucket:
            continue

        readiness_vals  = [n["readiness"]  for n in bucket]
        ensemble_vals   = [n["ensemble"]   for n in bucket]
        floodload_vals  = [n["flood_load"] for n in bucket]
        rain_vals       = [n["rain_mm"]    for n in bucket]

        avg_readiness   = round(float(np.mean(readiness_vals)),  1)
        avg_ensemble    = round(float(np.mean(ensemble_vals)),   2)
        avg_floodload   = round(float(np.mean(floodload_vals)),  2)
        avg_rain        = round(float(np.mean(rain_vals)),       3)
        critical_nodes  = sum(1 for n in bucket if n["flood_load"] > 80)
        high_nodes      = sum(1 for n in bucket if 40 < n["flood_load"] <= 80)

        scores.append({
            "district":       d["name"],
            "known_risk":     d["known_risk"],
            "total_nodes":    len(bucket),
            "avg_readiness":  avg_readiness,
            "avg_ensemble":   avg_ensemble,
            "avg_flood_load": avg_floodload,
            "avg_rain_mm":    avg_rain,
            "critical_nodes": critical_nodes,
            "high_nodes":     high_nodes,
            "risk_level":     _risk_label(avg_readiness),
            "color":          _risk_color(avg_readiness),
        })

    # Sort worst first
    scores.sort(key=lambda x: x["avg_readiness"])

    return jsonify({
        "districts":      scores,
        "total_districts": len(scores),
        "mode":           _last_result.get("mode", "simulated"),
        "city_readiness": round(float(np.mean([s["avg_readiness"] for s in scores])), 1),
    })
