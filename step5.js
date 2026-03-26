let dispatchActive = false;

function injectStep5Panel() {
  if (document.getElementById('step5Panel')) return;
  
  const container = document.querySelector('.leaflet-right.leaflet-pane'); // Map sidebar
  if (!container) return;
  
  const div = document.createElement('div');
  div.id = 'step5Panel';
  div.style.cssText = `
    margin-top: 12px; padding: 12px; background: rgba(10,10,15,0.95);
    border: 1px solid #ff4444; border-radius: 8px; font-family: 'Courier New';
  `;
  div.innerHTML = `
    <div style="color:#ff4444;font-weight:bold;margin-bottom:8px;font-size:12px;">
      🚨 NDRF COMMAND CENTER
    </div>
    <div style="font-size:10px;color:#ff6666;margin-bottom:8px;">
      Critical zones: <span id="critCountLive">0</span>
    </div>
    <button id="dispatchBtn5" class="dispatch-btn" style="
      width:100%; padding:12px; background:linear-gradient(135deg,#ff4444,#cc0000);
      color:white; font-weight:bold; border:none; border-radius:8px; cursor:pointer;
      font-size:13px; letter-spacing:1px;
    ">🚨 DISPATCH NDRF (0)</button>
    <div id="dispatchStatus" style="font-size:9px;color:#ffaa00;margin-top:6px;"></div>
  `;
  container.appendChild(div);
  
  // Wire dispatch button
  document.getElementById('dispatchBtn5').onclick = dispatchNDRF;
}

function updateDispatchCount(count) {
  document.getElementById('critCountLive').textContent = count;
  document.getElementById('dispatchBtn5').textContent = `🚨 DISPATCH NDRF (${count})`;
}

function dispatchNDRF() {
  if (dispatchActive) return;
  
  const critical = window.violetQueue || [];
  if (!critical.length) {
    alert('No critical zones detected');
    return;
  }
  
  dispatchActive = true;
  document.getElementById('dispatchBtn5').textContent = '🚨 SENDING...';
  
  fetch('/api/dispatch_ndrf', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      critical_zones: critical.slice(0, 8),  // Top 8 zones
      simdata: window.lastSimData,
      mode: window.FLOODMODE || 'simulated'
    })
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      document.getElementById('dispatchStatus').innerHTML = 
        `✅ ${res.dispatched} zones dispatched<br>
         ${res.zones.join(', ')}`;
      // Flash success
      document.getElementById('dispatchBtn5').style.background = 
        'linear-gradient(135deg,#00ff88,#00cc66)';
      setTimeout(() => {
        dispatchActive = false;
        updateDispatchCount(critical.length);
      }, 4000);
    }
  })
  .catch(err => {
    document.getElementById('dispatchStatus').textContent = '❌ Dispatch failed';
    dispatchActive = false;
  });
}

function initStep5() {
  injectStep5Panel();
  // Hook into existing dispatch button too
  const existingBtn = document.getElementById('dispatchBtn');
  if (existingBtn) {
    existingBtn.onclick = dispatchNDRF;
  }
}
