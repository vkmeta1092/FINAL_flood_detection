# hathni_kund.py
# ── Hathni Kund Barrage · Live Scraper + Rating Curves + Alert Engine ─────────

import re
import time
import threading
import requests
from bs4 import BeautifulSoup
from math import floor
from datetime import datetime, timedelta

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
TELEGRAM_BOT   = "8686433144:AAF2x7pxOHgxndgo45q9aE42ocPc3gzTdSQ"
TELEGRAM_CHAT  = "7938650094"
HK_CACHE_TTL   = 300   # seconds — refresh every 5 min

# ── RATING CURVE: discharge (cusecs) → ITO gauge stage (metres) ───────────────
# Based on CWC historical correlation Delhi ITO gauge vs Hathni Kund release
HK_RATING_CURVE = [
    (0,        203.30),
    (5_000,    203.50),
    (10_000,   203.80),
    (30_000,   204.30),
    (50_000,   204.80),
    (75_000,   205.20),
    (1_00_000, 205.80),
    (1_50_000, 206.20),
    (2_00_000, 206.50),
    (3_00_000, 207.00),
    (3_50_000, 207.50),
    (5_00_000, 208.20),
    (7_00_000, 208.80),
    (10_00_000,209.50),
]

# ── TRAVEL TIME CURVE: discharge (cusecs) → hrs to reach Delhi ────────────────
# Higher discharge = channel runs faster = shorter travel time
HK_TRAVEL_CURVE = [
    (0,         84),
    (10_000,    78),
    (50_000,    72),
    (1_00_000,  65),
    (2_00_000,  56),
    (3_50_000,  48),
    (7_00_000,  42),
    (10_00_000, 36),
]

# ── ALERT THRESHOLDS ──────────────────────────────────────────────────────────
# (min_cusecs, label, hex_color, numeric_level)
HK_ALERT_LEVELS = [
    (3_50_000, "🔴 SEVERE",    "#ff0000", 4),
    (2_00_000, "🟠 DANGER",    "#ff6600", 3),
    (1_00_000, "🟡 WARNING",   "#ffcc00", 2),
    (50_000,   "🔵 ADVISORY",  "#00aaff", 1),
    (0,        "🟢 NORMAL",    "#00ffcc", 0),
]

# ── INTERNAL CACHE ─────────────────────────────────────────────────────────────
_hk_cache        = {"data": None, "ts": 0}
_last_alert_sent = {"level": -1}   # prevents repeat Telegram spam


# ── INTERPOLATION ──────────────────────────────────────────────────────────────
def _interp(curve, x):
    """Linear interpolation on sorted list of (x, y) tuples."""
    if x <= curve[0][0]:     return curve[0][1]
    if x >= curve[-1][0]:    return curve[-1][1]
    for i in range(len(curve) - 1):
        x0, y0 = curve[i]
        x1, y1 = curve[i + 1]
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def discharge_to_stage(cusecs: float) -> float:
    """Map Hathni Kund discharge → predicted ITO gauge stage (m)."""
    return round(_interp(HK_RATING_CURVE, cusecs), 2)


def discharge_to_travel_hrs(cusecs: float) -> float:
    """Map discharge → travel time to Delhi in hours."""
    return round(_interp(HK_TRAVEL_CURVE, cusecs), 1)


def discharge_to_alert(cusecs: float):
    """Return (label, hex_color, numeric_level) for given discharge."""
    for threshold, label, color, level in HK_ALERT_LEVELS:
        if cusecs >= threshold:
            return label, color, level
    return "🟢 NORMAL", "#00ffcc", 0


# ── CWC SCRAPER ────────────────────────────────────────────────────────────────
def scrape_hathni_kund() -> dict:
    """
    Attempt to scrape live Hathni Kund discharge from CWC public sources.
    Tries 3 strategies. Falls back to 0 cusecs (dry / no data) on failure.
    Returns a fully populated data dict regardless of scrape outcome.
    """
    discharge    = None
    source_used  = "fallback"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # ── Strategy 1: CWC flood forecasting page ────────────────────────────────
    try:
        r = requests.get(
            "https://cwc.gov.in/flood-forecasting",
            headers=headers, timeout=8
        )
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True).upper()
        m = re.search(
            r"HATHNI[^0-9]{0,50}([\d,]+)\s*(?:CUSECS|CUMECS|M3/S)?",
            text
        )
        if m:
            val = int(m.group(1).replace(",", ""))
            if 0 < val < 2_000_000:
                discharge   = val
                source_used = "CWC flood page"
    except Exception:
        pass

    # ── Strategy 2: CWC plain-text data file ─────────────────────────────────
    if discharge is None:
        try:
            r = requests.get(
                "https://cwc.gov.in/sites/default/files/hathnikund.txt",
                headers=headers, timeout=6
            )
            if r.status_code == 200:
                m = re.search(r"([\d,]+)", r.text.strip())
                if m:
                    val = int(m.group(1).replace(",", ""))
                    if 0 < val < 2_000_000:
                        discharge   = val
                        source_used = "CWC text file"
        except Exception:
            pass

    # ── Strategy 3: India-WRIS API endpoint ───────────────────────────────────
    if discharge is None:
        try:
            r = requests.get(
                "https://indiawris.gov.in/wris/#/RiverMonitoring",
                headers=headers, timeout=6
            )
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True).upper()
            m = re.search(
                r"HATHNI[^0-9]{0,50}([\d,]+)",
                text
            )
            if m:
                val = int(m.group(1).replace(",", ""))
                if 0 < val < 2_000_000:
                    discharge   = val
                    source_used = "India-WRIS"
        except Exception:
            pass

    # ── Fallback ───────────────────────────────────────────────────────────────
    if discharge is None:
        discharge   = 0
        source_used = "fallback — dry season / scrape failed"

    # ── Trend vs previous cached value ────────────────────────────────────────
    prev = (_hk_cache["data"] or {}).get("discharge_cusecs", 0)
    if   discharge > prev * 1.05:  trend = "↑ Rising"
    elif discharge < prev * 0.95:  trend = "↓ Falling"
    else:                           trend = "→ Stable"

    # ── Derived values ─────────────────────────────────────────────────────────
    stage       = discharge_to_stage(discharge)
    travel_hrs  = discharge_to_travel_hrs(discharge)
    alert, alert_color, alert_level = discharge_to_alert(discharge)

    # ETA in IST (UTC+5:30)
    eta_dt  = datetime.utcnow() + timedelta(hours=travel_hrs + 5.5)
    eta_iso = eta_dt.strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "discharge_cusecs": discharge,
        "discharge_lakh":   round(discharge / 1_00_000, 2),
        "predicted_stage":  stage,
        "travel_hrs":       travel_hrs,
        "alert":            alert,
        "alert_color":      alert_color,
        "alert_level":      alert_level,
        "trend":            trend,
        "eta_iso":          eta_iso,
        "source":           source_used,
        "fetched_at":       datetime.utcnow().strftime("%H:%M UTC"),
        "danger_threshold": 205.3,
        "stage_above_danger": round(max(0.0, stage - 205.3), 2),
    }


# ── PUBLIC API ─────────────────────────────────────────────────────────────────
def get_hk_data(force: bool = False) -> dict:
    """
    Return cached Hathni Kund data, refreshing every HK_CACHE_TTL seconds.
    Auto-fires Telegram alert if alert level rises above previous level.
    """
    global _hk_cache, _last_alert_sent

    if (not force
            and _hk_cache["data"] is not None
            and (time.time() - _hk_cache["ts"]) < HK_CACHE_TTL):
        return _hk_cache["data"]

    data = scrape_hathni_kund()
    _hk_cache = {"data": data, "ts": time.time()}

    # Auto-alert — only escalate, never repeat same level
    lvl = data["alert_level"]
    if lvl >= 2 and lvl > _last_alert_sent["level"]:
        threading.Thread(
            target=_send_telegram_alert,
            args=(data,),
            daemon=True
        ).start()
        _last_alert_sent["level"] = lvl

    # Reset tracker when situation improves back to normal
    if lvl == 0:
        _last_alert_sent["level"] = -1

    return data


# ── TELEGRAM AUTO-ALERT ────────────────────────────────────────────────────────
def _send_telegram_alert(hk: dict):
    """Send Hathni Kund escalation alert to Telegram. Non-blocking (runs in thread)."""
    msg = (
        f"⚠️ *AUTO HATHNI KUND ALERT*\n\n"
        f"Status: *{hk['alert']}*\n"
        f"Discharge: *{hk['discharge_cusecs']:,} cusecs* "
        f"({hk['discharge_lakh']} lakh)\n"
        f"Predicted Delhi Stage: *{hk['predicted_stage']} m*\n"
        f"Above Danger Mark: *+{hk['stage_above_danger']} m*\n"
        f"Trend: {hk['trend']}\n"
        f"⏱️ Delhi Impact ETA: *{hk['travel_hrs']} hrs*\n\n"
        f"Source: _{hk['source']}_\n"
        f"🚨 Pre-position NDRF teams immediately."
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
    except Exception:
        pass


# ── QUICK TEST (run directly: python hathni_kund.py) ──────────────────────────
if __name__ == "__main__":
    print("Fetching Hathni Kund data...")
    data = get_hk_data(force=True)
    print(f"\n{'='*50}")
    print(f"  Discharge   : {data['discharge_cusecs']:,} cusecs ({data['discharge_lakh']} lakh)")
    print(f"  Delhi Stage : {data['predicted_stage']} m  (danger > 205.3m)")
    print(f"  Travel Time : {data['travel_hrs']} hrs")
    print(f"  Alert       : {data['alert']}")
    print(f"  Trend       : {data['trend']}")
    print(f"  ETA (IST)   : {data['eta_iso']}")
    print(f"  Source      : {data['source']}")
    print(f"  Fetched at  : {data['fetched_at']}")
    print(f"{'='*50}")