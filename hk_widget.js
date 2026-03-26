// static/hk_widget.js
// ── Hathni Kund Widget · JS Engine ────────────────────────────────────────────

window._hkData       = null;
window._etaInterval  = null;
window._hkRefreshInt = null;

// ── RATING CURVE (mirrors Python exactly) ─────────────────────────────────────
const HK_RATING_CURVE = [
    [0,        203.30], [5000,    203.50], [10000,   203.80],
    [30000,    204.30], [50000,   204.80], [75000,   205.20],
    [100000,   205.80], [150000,  206.20], [200000,  206.50],
    [300000,   207.00], [350000,  207.50], [500000,  208.20],
    [700000,   208.80], [1000000, 209.50],
];

const HK_TRAVEL_CURVE = [
    [0, 84], [10000, 78], [50000, 72], [100000, 65],
    [200000, 56], [350000, 48], [700000, 42], [1000000, 36],
];

const HK_ALERT_LEVELS = [
    [350000, "🔴 SEVERE",   "#ff0000", 4],
    [200000, "🟠 DANGER",   "#ff6600", 3],
    [100000, "🟡 WARNING",  "#ffcc00", 2],
    [50000,  "🔵 ADVISORY", "#00aaff", 1],
    [0,      "🟢 NORMAL",   "#00ffcc", 0],
];


// ── INTERPOLATION ──────────────────────────────────────────────────────────────
function jsInterpCurve(curve, x) {
    if (x <= curve[0][0])           return curve[0][1];
    if (x >= curve[curve.length-1][0]) return curve[curve.length-1][1];
    for (let i = 0; i < curve.length - 1; i++) {
        const [x0, y0] = curve[i], [x1, y1] = curve[i+1];
        if (x0 <= x && x <= x1) return y0 + (y1-y0)*(x-x0)/(x1-x0);
    }
    return curve[curve.length-1][1];
}

function jsDischargeToStage(cusecs) {
    return parseFloat(jsInterpCurve(HK_RATING_CURVE, cusecs).toFixed(2));
}

function jsDischargeToAlert(cusecs) {
    for (const [threshold, label, color, level] of HK_ALERT_LEVELS) {
        if (cusecs >= threshold) return { label, color, level };
    }
    return { label: "🟢 NORMAL", color: "#00ffcc", level: 0 };
}

function hexToRgb(hex) {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return `${r},${g},${b}`;
}


// ── FETCH FROM FLASK BACKEND ───────────────────────────────────────────────────
function fetchHKData(callback) {
    fetch('/api/hathni_kund')
        .then(r => r.json())
        .then(data => {
            window._hkData = data;
            renderHKWidget(data);
            if (callback) callback(data);
        })
        .catch(() => {
            renderHKWidget(null);
        });
}


// ── RENDER WIDGET ──────────────────────────────────────────────────────────────
function renderHKWidget(data) {

    // Handle fetch failure gracefully
    if (!data) {
        _setEl('hkDischarge',   'N/A');
        _setEl('hkLakh',        '—');
        _setEl('hkStage',       'N/A');
        _setEl('hkTrend',       '—');
        _setEl('hkETA',         '—');
        _setEl('hkETACountdown','Scrape failed — fallback active');
        _setEl('hkSource',      'offline');
        _setEl('hkFetchedAt',   '—');
        const badge = document.getElementById('hkAlertBadge');
        if (badge) { badge.innerText = 'OFFLINE'; badge.style.color = '#556'; }
        return;
    }

    // ── Discharge cell ─────────────────────────────────────────────────────────
    _setEl('hkDischarge', data.discharge_cusecs.toLocaleString() + ' cusecs');
    _setEl('hkLakh',      data.discharge_lakh + ' lakh cusecs');

    // ── Stage cell ─────────────────────────────────────────────────────────────
    const stageEl = document.getElementById('hkStage');
    if (stageEl) {
        stageEl.innerText = data.predicted_stage + ' m';
        stageEl.style.color = data.predicted_stage > 205.3 ? '#ff6600' : '#ffcc00';
    }

    // ── Trend cell ─────────────────────────────────────────────────────────────
    const trendEl = document.getElementById('hkTrend');
    if (trendEl) {
        trendEl.innerText  = data.trend;
        trendEl.style.color =
            data.trend.includes('↑') ? '#ff6666' :
            data.trend.includes('↓') ? '#00ffcc' : '#aaa';
    }

    // ── Alert badge ────────────────────────────────────────────────────────────
    const badge = document.getElementById('hkAlertBadge');
    if (badge) {
        badge.innerText          = data.alert;
        badge.style.color        = data.alert_color;
        badge.style.background   = `rgba(${hexToRgb(data.alert_color)},.12)`;
        badge.style.borderColor  = `rgba(${hexToRgb(data.alert_color)},.4)`;
        if (data.alert_level >= 2) {
            badge.style.animation = 'badgePulse 1.2s ease-in-out infinite';
        } else {
            badge.style.animation = 'none';
        }
    }

    // ── ETA cell ───────────────────────────────────────────────────────────────
    _setEl('hkETA', data.travel_hrs + ' hrs');
    startETACountdown(data.eta_iso);

    // ── Source + timestamp ─────────────────────────────────────────────────────
    _setEl('hkSource',    data.source.substring(0, 30));
    _setEl('hkFetchedAt', 'Fetched: ' + data.fetched_at);

    // ── Alert banner ───────────────────────────────────────────────────────────
    renderAlertBanner(data);

    // ── Real mode: update hkDetail signal line ─────────────────────────────────
    const hkDetail = document.getElementById('hkDetail');
    if (hkDetail) {
        hkDetail.innerText =
            data.discharge_cusecs.toLocaleString() +
            ' cusecs · Stage ' + data.predicted_stage + 'm';
    }

    // ── Auto-apply stage to Yamuna slider if real mode ─────────────────────────
    if (window.FLOOD_MODE === 'real') applyHKToEngine();
}


// ── ALERT BANNER ───────────────────────────────────────────────────────────────
function renderAlertBanner(data) {
    const banner = document.getElementById('hkAlertBanner');
    if (!banner) return;

    if (data.alert_level >= 1) {
        const rgb = hexToRgb(data.alert_color);
        banner.style.display     = 'block';
        banner.style.color       = data.alert_color;
        banner.style.borderColor = `rgba(${rgb},.5)`;
        banner.style.background  = `rgba(${rgb},.08)`;

        let msg = `${data.alert} &nbsp;·&nbsp; `;
        msg    += `${data.discharge_cusecs.toLocaleString()} cusecs &nbsp;·&nbsp; `;
        msg    += `Stage <b>${data.predicted_stage}m</b>`;
        if (data.stage_above_danger > 0) {
            msg += ` <span style="color:#ff4444">(+${data.stage_above_danger}m above danger)</span>`;
        }
        msg += ` &nbsp;·&nbsp; Delhi impact in <b>${data.travel_hrs} hrs</b>`;
        banner.innerHTML = msg;

        // Shake animation for severe/danger
        if (data.alert_level >= 3) {
            banner.style.animation = 'hkShake 0.5s ease-in-out, pulseBorder 1.5s infinite';
        } else {
            banner.style.animation = 'pulseBorder 2s infinite';
        }
    } else {
        banner.style.display = 'none';
    }
}


// ── ETA COUNTDOWN TIMER ────────────────────────────────────────────────────────
function startETACountdown(etaISO) {
    if (window._etaInterval) clearInterval(window._etaInterval);

    // etaISO is already IST — parse as local-ish
    const etaDate = new Date(etaISO + '+05:30');

    function tick() {
        const now  = new Date();
        const diff = etaDate - now;

        const el = document.getElementById('hkETACountdown');
        if (!el) return;

        if (diff <= 0) {
            el.innerText = '⚠️ IMPACT WINDOW REACHED';
            el.style.color = '#ff0000';
            clearInterval(window._etaInterval);
            return;
        }

        const h = Math.floor(diff / 3600000);
        const mn = Math.floor((diff % 3600000) / 60000);
        const s  = Math.floor((diff % 60000)   / 1000);

        el.innerText = `Impact in ${h}h ${mn}m ${s}s`;
        el.style.color = diff < 6 * 3600000 ? '#ff6666' :
                         diff < 24 * 3600000 ? '#ffaa00' : '#556';
    }

    tick();
    window._etaInterval = setInterval(tick, 1000);
}


// ── SCENARIO PRESET (simulated mode) ─────────────────────────────────────────
function applyHKScenario() {
    const select  = document.getElementById('hkScenario');
    if (!select) return;
    const cusecs  = parseInt(select.value) || 0;
    const stage   = parseFloat(jsDischargeToStage(cusecs).toFixed(2));
    const alert   = jsDischargeToAlert(cusecs);

    // Travel time
    const travelHrs = parseFloat(jsInterpCurve(HK_TRAVEL_CURVE, cusecs).toFixed(1));

    // ── Update Yamuna overflow slider ──────────────────────────────────────────
    const riverSlider = document.getElementById('riverSlider');
    const toggleRiver = document.getElementById('toggleRiver');
    const riverDisp   = document.getElementById('riverDisp');
    if (riverSlider) {
        const clampedStage = Math.min(Math.max(stage, 203), 209);
        riverSlider.value  = clampedStage;
        if (riverDisp) riverDisp.innerText = clampedStage.toFixed(1) + ' m';
    }
    if (toggleRiver) toggleRiver.checked = (stage > 205.3);

    // ── Update widget display ──────────────────────────────────────────────────
    _setEl('hkDischarge', cusecs.toLocaleString() + ' cusecs');
    _setEl('hkLakh',      (cusecs / 100000).toFixed(2) + ' lakh cusecs');

    const stageEl = document.getElementById('hkStage');
    if (stageEl) {
        stageEl.innerText    = stage.toFixed(2) + ' m';
        stageEl.style.color  = stage > 205.3 ? '#ff6600' : '#ffcc00';
    }

    _setEl('hkETA', travelHrs + ' hrs');

    // Compute ETA from now
    const etaDt  = new Date(Date.now() + travelHrs * 3600000);
    const etaISO = etaDt.toISOString().slice(0,19);
    startETACountdown(etaISO);

    // ── Alert badge + banner ───────────────────────────────────────────────────
    const badge = document.getElementById('hkAlertBadge');
    if (badge) {
        badge.innerText         = alert.label;
        badge.style.color       = alert.color;
        badge.style.background  = `rgba(${hexToRgb(alert.color)},.12)`;
        badge.style.borderColor = `rgba(${hexToRgb(alert.color)},.4)`;
        badge.style.animation   = alert.level >= 2 ? 'badgePulse 1.2s ease-in-out infinite' : 'none';
    }

    // Synthetic data obj for banner
    renderAlertBanner({
        alert:             alert.label,
        alert_color:       alert.color,
        alert_level:       alert.level,
        discharge_cusecs:  cusecs,
        predicted_stage:   stage,
        stage_above_danger: Math.max(0, stage - 205.3).toFixed(2),
        travel_hrs:        travelHrs,
    });

    // ── Trigger IDW engine update ──────────────────────────────────────────────
    if (typeof updateSim === 'function') updateSim();
}


// ── AUTO-APPLY HK STAGE TO ENGINE (real mode) ─────────────────────────────────
function applyHKToEngine() {
    if (!window._hkData) return;

    const autoApply = document.getElementById('hkAutoApply');
    if (autoApply && !autoApply.checked) return;

    const stage       = window._hkData.predicted_stage;
    const riverSlider = document.getElementById('riverSlider');
    const toggleRiver = document.getElementById('toggleRiver');
    const riverDisp   = document.getElementById('riverDisp');

    if (riverSlider) {
        riverSlider.value = Math.min(Math.max(stage, 203), 209);
    }
    if (toggleRiver) toggleRiver.checked = (stage > 205.3);
    if (riverDisp)   riverDisp.innerText  = stage.toFixed(1) + ' m';
}


// ── START AUTO-REFRESH (every 5 min) ──────────────────────────────────────────
function startHKAutoRefresh() {
    if (window._hkRefreshInt) clearInterval(window._hkRefreshInt);
    window._hkRefreshInt = setInterval(() => {
        fetchHKData(data => {
            // In real mode — re-apply stage after refresh
            if (window.FLOOD_MODE === 'real' && typeof updateSim === 'function') {
                applyHKToEngine();
                updateSim();
            }
        });
    }, 5 * 60 * 1000);  // 5 minutes
}


// ── UTILITY ────────────────────────────────────────────────────────────────────
function _setEl(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}


// ── CSS INJECTED BY THIS MODULE ────────────────────────────────────────────────
(function injectHKStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes hkScan {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(400%);  }
        }
        @keyframes hkShake {
            0%,100% { transform: translateX(0);    }
            20%     { transform: translateX(-4px);  }
            40%     { transform: translateX(4px);   }
            60%     { transform: translateX(-3px);  }
            80%     { transform: translateX(3px);   }
        }
        @keyframes badgePulse {
            0%,100% { opacity: 1;   }
            50%     { opacity: 0.4; }
        }
        @keyframes pulseBorder {
            0%,100% { box-shadow: 0 0 0 0   rgba(143,0,255,.4); }
            50%     { box-shadow: 0 0 0 8px rgba(143,0,255,0);  }
        }
        #hkWidget:hover {
            border-color: rgba(0,170,255,.6) !important;
            transition: border-color .3s;
        }
        #hkScenario option { background: #0a0a12; }
        #hkAlertBanner {
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 11px;
            font-family: 'Courier New', monospace;
            border: 1px solid;
            line-height: 1.8;
        }
    `;
    document.head.appendChild(style);
})();
