# report_engine.py
# ── Step 4 · Report Engine · Telegram Dispatch · Snapshot ─────────────────────

import requests
from datetime import datetime

# ── CONFIG (same as hathni_kund.py) ───────────────────────────────────────────
TELEGRAM_BOT  = "8686433144:AAF2x7pxOHgxndgo45q9aE42ocPc3gzTdSQ"
TELEGRAM_CHAT = "7938650094"

# ── ENSEMBLE AUTO-ALERT THRESHOLD ─────────────────────────────────────────────
ENSEMBLE_ALERT_THRESHOLD = 70   # fires Telegram when avg ensemble > this
_last_ensemble_alert     = {"val": 0}


# ── SNAPSHOT ───────────────────────────────────────────────────────────────────
def build_snapshot(sim_data: dict, hk_data: dict, mode: str) -> dict:
    """
    Combine sim engine output + HK data into one clean snapshot dict.
    sim_data = output of compute_simulated_idw() or compute_real_idw()
    hk_data  = output of get_hk_data()
    """
    nodes    = sim_data.get("nodes", [])
    critical = [n for n in nodes if n.get("flood_load", 0) > 80]
    critical_sorted = sorted(critical, key=lambda x: x["flood_load"], reverse=True)

    return {
        "timestamp":       datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "timestamp_ist":   datetime.utcnow().strftime("%d %b %Y · %H:%M IST"),
        "mode":            mode.upper(),
        "avg_readiness":   sim_data.get("avg_readiness", 0),
        "avg_ensemble":    sim_data.get("avg_ensemble",  0),
        "critical_count":  len(critical),
        "total_nodes":     len(nodes),
        "base_rain":       sim_data.get("base_rain",     0),
        "river_stage":     sim_data.get("river_stage",   0),
        "maint_factor":    sim_data.get("maint_factor",  1),
        "top_critical":    critical_sorted[:10],
        "hk_discharge":    hk_data.get("discharge_cusecs", 0),
        "hk_stage":        hk_data.get("predicted_stage",  0),
        "hk_alert":        hk_data.get("alert",            "🟢 NORMAL"),
        "hk_alert_level":  hk_data.get("alert_level",      0),
        "hk_travel_hrs":   hk_data.get("travel_hrs",       84),
        "hk_trend":        hk_data.get("trend",            "→ Stable"),
        "hk_source":       hk_data.get("source",           "fallback"),
    }


# ── FORMAT NDRF DISPATCH MESSAGE ───────────────────────────────────────────────
def format_ndrf_dispatch(snapshot: dict) -> str:
    """
    Format a full NDRF Telegram dispatch message from snapshot.
    """
    now    = snapshot["timestamp_ist"]
    ccount = snapshot["critical_count"]
    top    = snapshot["top_critical"][:5]

    # Build critical node lines
    node_lines = ""
    for i, n in enumerate(top, 1):
        node_lines += (
            f"\n  {i}. {n['digipin']} · {n['zone_type']}"
            f"\n     📍 {n['lat']:.4f}°N {n['lng']:.4f}°E"
            f"\n     💧 Load: {n['flood_load']} mm · Ensemble: {n['ensemble']}"
        )

    # Readiness color
    r = snapshot["avg_readiness"]
    readiness_tag = "🔴 CRITICAL" if r < 40 else "🟠 STRESSED" if r < 75 else "🟢 STABLE"

    msg = (
        f"🚨 *NDRF FLOOD DISPATCH — DELHI NCR*\n"
        f"{'─'*35}\n"
        f"🕐 {now}\n"
        f"⚙️  Mode: *{snapshot['mode']}*\n\n"
        f"📊 *ENGINE STATUS*\n"
        f"  Readiness:     *{r}%* — {readiness_tag}\n"
        f"  Ensemble Score: *{snapshot['avg_ensemble']} / 100*\n"
        f"  Critical Zones: *{ccount} nodes*\n"
        f"  Base Rainfall:  *{snapshot['base_rain']} mm/hr*\n"
        f"  River Stage:    *{snapshot['river_stage']} m*\n\n"
        f"🌊 *HATHNI KUND STATUS*\n"
        f"  Alert:     *{snapshot['hk_alert']}*\n"
        f"  Discharge: *{snapshot['hk_discharge']:,} cusecs*\n"
        f"  Pred Stage: *{snapshot['hk_stage']} m* at ITO\n"
        f"  ETA Delhi:  *{snapshot['hk_travel_hrs']} hrs*\n"
        f"  Trend:      {snapshot['hk_trend']}\n\n"
        f"📍 *TOP {min(5,len(top))} CRITICAL NODES*"
        f"{node_lines}\n\n"
        f"{'─'*35}\n"
        f"⚡ Deploy NDRF teams to critical zones immediately.\n"
        f"📡 Source: Open-Meteo + CWC + IDW Engine\n"
        f"🏛️ Command: Bharat Mandapam, Delhi"
    )
    return msg


# ── SEND NDRF DISPATCH ─────────────────────────────────────────────────────────
def send_ndrf_dispatch(snapshot: dict) -> bool:
    """Send NDRF dispatch Telegram message. Returns True on success."""
    msg = format_ndrf_dispatch(snapshot)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT,
                "text":       msg,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


# ── MORNING BRIEFING ───────────────────────────────────────────────────────────
def format_morning_briefing(snapshot: dict) -> str:
    """Format a concise 6AM daily briefing message."""
    r = snapshot["avg_readiness"]
    readiness_tag = "🔴 CRITICAL" if r < 40 else "🟠 STRESSED" if r < 75 else "🟢 STABLE"

    return (
        f"🌅 *DELHI FLOOD ENGINE — MORNING BRIEFING*\n"
        f"{'─'*35}\n"
        f"📅 {snapshot['timestamp_ist']}\n\n"
        f"🛡️ City Readiness:    *{r}%* {readiness_tag}\n"
        f"📊 Ensemble Score:    *{snapshot['avg_ensemble']} / 100*\n"
        f"⚠️  Critical Zones:   *{snapshot['critical_count']} nodes*\n\n"
        f"🌊 Hathni Kund:       *{snapshot['hk_alert']}*\n"
        f"   Discharge: {snapshot['hk_discharge']:,} cusecs\n"
        f"   ETA Delhi: {snapshot['hk_travel_hrs']} hrs\n\n"
        f"{'─'*35}\n"
        f"📡 Auto-briefing · Delhi Flood Intelligence Engine\n"
        f"🏛️ Bharat Mandapam Command"
    )


def send_morning_briefing(snapshot: dict) -> bool:
    """Send morning briefing to Telegram."""
    msg = format_morning_briefing(snapshot)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT,
                "text":       msg,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


# ── ENSEMBLE AUTO-ALERT ────────────────────────────────────────────────────────
def check_ensemble_alert(snapshot: dict) -> bool:
    """
    Fire Telegram alert if ensemble crosses ENSEMBLE_ALERT_THRESHOLD.
    Won't repeat same alert level. Returns True if alert was sent.
    """
    global _last_ensemble_alert
    val = snapshot["avg_ensemble"]

    if val >= ENSEMBLE_ALERT_THRESHOLD and val > _last_ensemble_alert["val"]:
        _last_ensemble_alert["val"] = val
        msg = (
            f"⚠️ *ENSEMBLE THRESHOLD CROSSED*\n\n"
            f"Score: *{val} / 100*\n"
            f"Critical Zones: *{snapshot['critical_count']}*\n"
            f"Readiness: *{snapshot['avg_readiness']}%*\n"
            f"Hathni Kund: *{snapshot['hk_alert']}*\n\n"
            f"🕐 {snapshot['timestamp_ist']}\n"
            f"⚡ Review deployment status immediately."
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
                json={
                    "chat_id":    TELEGRAM_CHAT,
                    "text":       msg,
                    "parse_mode": "Markdown"
                },
                timeout=8
            )
            return True
        except Exception:
            return False

    if val < ENSEMBLE_ALERT_THRESHOLD * 0.8:
        _last_ensemble_alert["val"] = 0  # reset when situation improves

    return False


# ── GENERATE REPORT HTML ───────────────────────────────────────────────────────
def generate_report_html(snapshot: dict) -> str:
    """Generate a complete printable HTML report page."""

    r     = snapshot["avg_readiness"]
    r_col = "#ff4444" if r < 40 else "#ffaa00" if r < 75 else "#00ffcc"
    e     = snapshot["avg_ensemble"]
    e_col = "#ff4444" if e > 70 else "#ffaa00" if e > 40 else "#00ffcc"

    # Critical nodes table rows
    rows = ""
    for i, n in enumerate(snapshot["top_critical"], 1):
        fl_col = "#df00ff" if n["flood_load"] > 80 else "#ff4444"
        rows += f"""
        <tr>
          <td>{i}</td>
          <td style="color:#00ffcc">{n['digipin']}</td>
          <td>{n['lat']:.4f}°N</td>
          <td>{n['lng']:.4f}°E</td>
          <td style="color:#ffcc00">{n['zone_type']}</td>
          <td style="color:{fl_col};font-weight:bold">{n['flood_load']} mm</td>
          <td style="color:#ffaa00">{n['ensemble']}</td>
          <td style="color:#00ffcc">{n['readiness']}%</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Delhi Flood Intelligence Report</title>
  <style>
    body {{
      background:#0a0a12;color:#ccc;
      font-family:'Courier New',monospace;
      padding:30px;max-width:960px;margin:0 auto;
    }}
    h1 {{ color:#00ffcc;letter-spacing:3px;font-size:22px;margin-bottom:4px; }}
    h2 {{ color:#00aaff;font-size:13px;letter-spacing:2px;margin:24px 0 10px; }}
    .meta {{ color:#556;font-size:11px;margin-bottom:24px; }}
    .grid {{ display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px; }}
    .card {{ background:#111;border:1px solid #222;border-radius:8px;padding:14px;text-align:center; }}
    .card-val {{ font-size:28px;font-weight:bold;margin:6px 0; }}
    .card-lbl {{ font-size:9px;color:#556;letter-spacing:2px; }}
    table {{ width:100%;border-collapse:collapse;font-size:11px; }}
    th {{ background:#111;color:#556;padding:8px;text-align:left;
          letter-spacing:1px;font-size:9px;border-bottom:1px solid #222; }}
    td {{ padding:8px;border-bottom:1px solid #1a1a1a; }}
    tr:hover td {{ background:#111; }}
    .hk-box {{ background:#060d14;border:1px solid #00aaff33;
               border-radius:8px;padding:16px;margin-bottom:24px; }}
    .footer {{ color:#334;font-size:9px;margin-top:32px;
               border-top:1px solid #1a1a1a;padding-top:16px; }}
    @media print {{
      body {{ background:#fff;color:#000; }}
      .card {{ border:1px solid #ccc; }}
      h1,h2 {{ color:#000; }}
    }}
  </style>
</head>
<body>
  <h1>🏛️ DELHI FLOOD INTELLIGENCE ENGINE</h1>
  <h1 style="font-size:14px;color:#556;font-weight:normal;">
    Predictive Micro-Hotspot Report · Bharat Mandapam Command
  </h1>
  <div class="meta">
    Generated: {snapshot['timestamp_ist']} &nbsp;·&nbsp;
    Mode: {snapshot['mode']} &nbsp;·&nbsp;
    Nodes Evaluated: {snapshot['total_nodes']}
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-lbl">READINESS</div>
      <div class="card-val" style="color:{r_col}">{r}%</div>
      <div style="font-size:10px;color:#556">City avg</div>
    </div>
    <div class="card">
      <div class="card-lbl">ENSEMBLE</div>
      <div class="card-val" style="color:{e_col}">{e}</div>
      <div style="font-size:10px;color:#556">/ 100</div>
    </div>
    <div class="card">
      <div class="card-lbl">CRITICAL ZONES</div>
      <div class="card-val" style="color:#ff4444">{snapshot['critical_count']}</div>
      <div style="font-size:10px;color:#556">nodes &gt;80mm</div>
    </div>
    <div class="card">
      <div class="card-lbl">BASE RAINFALL</div>
      <div class="card-val" style="color:#00aaff">{snapshot['base_rain']}</div>
      <div style="font-size:10px;color:#556">mm/hr</div>
    </div>
  </div>

  <div class="hk-box">
    <h2 style="margin-top:0">🌊 HATHNI KUND BARRAGE STATUS</h2>
    <table>
      <tr>
        <td>Alert Level</td>
        <td style="font-weight:bold">{snapshot['hk_alert']}</td>
        <td>Discharge</td>
        <td>{snapshot['hk_discharge']:,} cusecs</td>
      </tr>
      <tr>
        <td>Predicted Delhi Stage</td>
        <td style="color:#ffcc00">{snapshot['hk_stage']} m</td>
        <td>ETA to Delhi</td>
        <td style="color:#ff6666">{snapshot['hk_travel_hrs']} hrs</td>
      </tr>
      <tr>
        <td>Trend</td>
        <td>{snapshot['hk_trend']}</td>
        <td>Data Source</td>
        <td style="color:#556">{snapshot['hk_source']}</td>
      </tr>
    </table>
  </div>

  <h2>📍 TOP {len(snapshot['top_critical'])} CRITICAL NODES</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>DIGIPIN</th><th>LAT</th><th>LNG</th>
        <th>ZONE</th><th>FLOOD LOAD</th><th>ENSEMBLE</th><th>READINESS</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="footer">
    Delhi Urban Flood Intelligence Engine · Step 4 Report ·
    Open-Meteo + IMD + CWC · IDW Spatial Engine ·
    Bharat Mandapam National Command Centre ·
    {snapshot['timestamp']}
  </div>
</body>
</html>"""


# ── QUICK TEST ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    dummy_snap = build_snapshot(
        sim_data={
            "nodes":          [],
            "avg_readiness":  62.4,
            "avg_ensemble":   34.1,
            "base_rain":      15,
            "river_stage":    204.5,
            "maint_factor":   1.2,
        },
        hk_data={
            "discharge_cusecs": 85000,
            "predicted_stage":  205.1,
            "alert":            "🔵 ADVISORY",
            "alert_level":      1,
            "travel_hrs":       70,
            "trend":            "↑ Rising",
            "source":           "test",
        },
        mode="simulated"
    )
    print(format_ndrf_dispatch(dummy_snap))
