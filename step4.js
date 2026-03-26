// static/step4.js
// ── Step 4 · Report Page · NDRF Dispatch · Snapshot API · Auto-Alert ─────────

window._step4_ensemble_watching = false;
window._step4_last_snap         = null;
window._dispatch_count          = 0;

// ── NDRF DISPATCH ──────────────────────────────────────────────────────────────
function sendNDRFDispatch() {
    const btn = document.getElementById('dispatchBtn');
    if (!btn) return;

    if (!window.lastSimData || !window.lastSimData.nodes) {
        alert('No simulation data yet — run simulation first!');
        return;
    }

    btn.innerText   = '📡 DISPATCHING...';
    btn.style.opacity = '0.7';
    btn.disabled    = true;

    fetch('/api/dispatch', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({
            sim_data: window.lastSimData,
            mode:     window.FLOOD_MODE || 'simulated'
        })
    })
    .then(r => r.json())
    .then(data => {
       if (data.success) {
    // increment counter
    window._dispatch_count++;

    // update counter display
    const counter = document.getElementById('dispatchCounter');
    if (counter) {
        counter.innerText = `📡 ${window._dispatch_count} alert${window._dispatch_count > 1 ? 's' : ''} sent`;
        counter.style.display = 'block';
    }

    btn.innerText        = '✅ DISPATCHED TO NDRF';
    btn.style.background = 'linear-gradient(135deg,#00aa44,#006622)';
    btn.style.opacity    = '1';
    btn.disabled         = false;
    showDispatchConfirm(data.snapshot);

    // ← RESET back to purple after 5 seconds
    setTimeout(() => {
        btn.innerText        = `🚨 DISPATCH NDRF (${window.lastSimData?.critical_count || ''} CRITICAL ZONES)`;
        btn.style.background = 'linear-gradient(135deg,#8f00ff,#5500aa)';
    }, 5000);
}
 else {
            btn.innerText    = '❌ DISPATCH FAILED';
            btn.style.opacity = '1';
            btn.disabled      = false;
        }
        setTimeout(() => {
            btn.innerText        = '🚨 DISPATCH NDRF';
            btn.style.background = 'linear-gradient(135deg,#8f00ff,#5500aa)';
        }, 5000);
    })
    .catch(() => {
        btn.innerText    = '❌ NETWORK ERROR';
        btn.style.opacity = '1';
        btn.disabled      = false;
        setTimeout(() => { btn.innerText = '🚨 DISPATCH NDRF'; }, 4000);
    });
}


// ── DISPATCH CONFIRM CARD ──────────────────────────────────────────────────────
function showDispatchConfirm(snap) {
    const existing = document.getElementById('dispatchConfirmCard');
    if (existing) existing.remove();

    const card = document.createElement('div');
    card.id    = 'dispatchConfirmCard';
    card.style.cssText = `
        background:#060d14;border:1px solid #00aa4466;border-radius:8px;
        padding:14px;margin-top:8px;font-family:'Courier New',monospace;
        font-size:10px;animation:fadeUp .4s ease;
    `;
    card.innerHTML = `
        <div style="color:#00ff88;font-size:11px;font-weight:bold;margin-bottom:8px;">
            ✅ TELEGRAM DISPATCH SENT</div>
        <div style="color:#556;line-height:2;">
            🕐 ${snap.timestamp_ist}<br>
            ⚠️ Critical Zones: <span style="color:#ff4444">${snap.critical_count}</span><br>
            🛡️ Readiness: <span style="color:#ffaa00">${snap.avg_readiness}%</span><br>
            🌊 HK Status: <span style="color:#00aaff">${snap.hk_alert}</span>
        </div>
        <div style="margin-top:8px;text-align:right;">
            <span onclick="this.parentElement.parentElement.remove()"
              style="color:#334;cursor:pointer;font-size:9px;">✕ dismiss</span>
        </div>`;

    const dispatchBtn = document.getElementById('dispatchBtn');
    if (dispatchBtn) dispatchBtn.after(card);
}


// ── OPEN REPORT PAGE ──────────────────────────────────────────────────────────
function openReport() {
    if (!window.lastSimData) {
        alert('Run simulation first to generate report!');
        return;
    }
    fetch('/api/snapshot', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({
            sim_data: window.lastSimData,
            mode:     window.FLOOD_MODE || 'simulated'
        })
    })
    .then(r => r.json())
    .then(data => {
        window.open('/report?ts=' + data.ts, '_blank');
    })
    .catch(() => {
        window.open('/report', '_blank');
    });
}


// ── ENSEMBLE WATCHER (auto-alert when crosses 70) ─────────────────────────────
function startEnsembleWatcher() {
    if (window._step4_ensemble_watching) return;
    window._step4_ensemble_watching = true;

    setInterval(() => {
        if (!window.lastSimData) return;
        const ens = window.lastSimData.avg_ensemble || 0;
        if (ens >= 70) {
            fetch('/api/ensemble_alert', {
                method:  'POST',
                headers: {'Content-Type': 'application/json'},
                body:    JSON.stringify({
                    sim_data: window.lastSimData,
                    mode:     window.FLOOD_MODE || 'simulated'
                })
            }).catch(() => {});
        }
    }, 60 * 1000); // check every 1 minute
}


// ── INJECT REPORT BUTTON ──────────────────────────────────────────────────────
function injectReportButton() {
    if (document.getElementById('reportBtn')) return;

    const keplerBtn = document.getElementById('keplerBtn');
    if (!keplerBtn) return;

    const btn       = document.createElement('button');
    btn.id          = 'reportBtn';
    btn.onclick     = openReport;
    btn.innerText   = '📄 VIEW FULL REPORT';
    btn.style.cssText = `
        width:100%;padding:12px;
        background:linear-gradient(135deg,#0a2a4a,#061830);
        color:#00aaff;font-weight:bold;border:1px solid #00aaff44;
        border-radius:8px;cursor:pointer;font-size:13px;
        margin-bottom:8px;letter-spacing:1px;
        transition:background .2s;
    `;
    btn.onmouseover = () => btn.style.background = 'linear-gradient(135deg,#0d3a6a,#091f40)';
    btn.onmouseout  = () => btn.style.background = 'linear-gradient(135deg,#0a2a4a,#061830)';

    keplerBtn.before(btn);
}


// ── MORNING BRIEFING BUTTON ────────────────────────────────────────────────────
function sendMorningBriefing() {
    fetch('/api/morning_briefing', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({
            sim_data: window.lastSimData || {},
            mode:     window.FLOOD_MODE  || 'simulated'
        })
    })
    .then(r => r.json())
    .then(data => {
        const el = document.getElementById('briefingStatus');
        if (el) {
            el.innerText  = data.success ? '✅ Briefing sent' : '❌ Failed';
            el.style.color = data.success ? '#00ffcc' : '#ff4444';
            setTimeout(() => { el.innerText = ''; }, 4000);
        }
    })
    .catch(() => {});
}


// ── INJECT STEP 4 CONTROLS PANEL ──────────────────────────────────────────────
function injectStep4Panel() {
    if (document.getElementById('step4Panel')) return;

    const keplerBtn = document.getElementById('keplerBtn');
    if (!keplerBtn) return;

    const panel       = document.createElement('div');
    panel.id          = 'step4Panel';
    panel.style.cssText = `
        background:#080810;border:1px solid #1a1a2a;border-radius:8px;
        padding:14px;margin-bottom:10px;font-family:'Courier New',monospace;
    `;
    panel.innerHTML = `
        <div style="font-size:9px;color:#334;letter-spacing:2px;margin-bottom:10px;">
            ⚡ COMMAND ACTIONS</div>

        <button onclick="openReport()"
          style="width:100%;padding:10px;background:linear-gradient(135deg,#0a2a4a,#061830);
          color:#00aaff;font-weight:bold;border:1px solid #00aaff44;border-radius:6px;
          cursor:pointer;font-size:11px;margin-bottom:6px;letter-spacing:1px;">
          📄 FULL REPORT PAGE
        </button>

        <button onclick="sendMorningBriefing()"
          style="width:100%;padding:10px;background:linear-gradient(135deg,#1a1a0a,#0d0d06);
          color:#ffcc00;font-weight:bold;border:1px solid #ffcc0044;border-radius:6px;
          cursor:pointer;font-size:11px;margin-bottom:6px;letter-spacing:1px;">
          🌅 SEND MORNING BRIEFING
        </button>

        <div style="font-size:9px;text-align:center;margin-top:4px;"
          id="briefingStatus"></div>
          <div id="dispatchCounter"
  style="font-size:9px;text-align:center;
  font-family:'Courier New',monospace;color:#8f00ff;
  letter-spacing:1px;margin-top:6px;padding:4px 8px;
  background:#1a0030;border:1px solid #8f00ff44;
  border-radius:4px;">
  📡 0 alerts sent
</div>

    `;

    keplerBtn.before(panel);
}


// ── UPDATE DISPATCH BUTTON LABEL ──────────────────────────────────────────────
function updateDispatchLabel(criticalCount) {
    const btn = document.getElementById('dispatchBtn');
    if (!btn) return;

    if (criticalCount > 0) {
        btn.style.display = 'block';
        btn.innerText     = `🚨 DISPATCH NDRF (${criticalCount} CRITICAL ZONES)`;
        btn.onclick       = sendNDRFDispatch;
    } else {
        btn.style.display = 'none';
    }
}


// ── INIT (called after mode selected) ─────────────────────────────────────────
function initStep4() {
    // Retry until keplerBtn exists
    const tryInject = setInterval(() => {
        if (document.getElementById('keplerBtn')) {
            clearInterval(tryInject);
            injectStep4Panel();
            startEnsembleWatcher();
        }
    }, 300);
}



// ── CSS INJECTED BY THIS MODULE ────────────────────────────────────────────────
(function injectStep4Styles() {
    const style       = document.createElement('style');
    style.textContent = `
        @keyframes fadeUp {
            from { opacity:0; transform:translateY(8px); }
            to   { opacity:1; transform:translateY(0);   }
        }
        #dispatchConfirmCard {
            animation: fadeUp .4s ease;
        }
        #step4Panel button:active {
            transform: scale(0.98);
        }
    `;
    document.head.appendChild(style);
    window.sendEmergencyDispatch = sendNDRFDispatch;
    // ── AUTO-INIT after modal dismissed ──
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initStep4, 3500); // wait for modal to finish
});
})();
