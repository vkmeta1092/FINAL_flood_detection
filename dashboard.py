# dashboard.py

def get_dashboard(node_registry_json, localities_json):
    # Fixed indentation: this block must be indented inside the function
    data_script = f"""
    <script>
      const NODE_REGISTRY = {node_registry_json};
      const LOCALITIES = {localities_json};
    </script>
    """

    # ── DASHBOARD (with search bar) ───────────────────────────────────────────────
    # Ensure the multi-line string starts at the correct indentation level
    dashboard_html = """
   <div style="position:fixed;top:15px;left:15px;width:375px;max-height:94vh;overflow-y:auto;
     background:rgba(10,10,15,0.98);color:#fff;z-index:999999 !important;padding:20px;
     border-radius:12px;font-family:'Segoe UI',sans-serif;border:1px solid #444;
     box-shadow:0 10px 30px rgba(0,0,0,.5);">

     <div style="font-size:24px;font-weight:bold;color:#00ffcc;margin-bottom:2px;" id="liveClock">00:00:00</div>
     <div style="font-size:10px;color:#888;letter-spacing:1px;margin-bottom:10px;">URBAN FLOODING &amp; HYDROLOGY ENGINE</div>

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
       <div id="searchSuggestions"
         style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;
                background:#0d0d14;border:1px solid #333;border-radius:8px;
                z-index:9999999;max-height:220px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.6);">
       </div>
     </div>

     <div style="margin-bottom:12px;">
       <button id="modeToggleBtn" onclick="toggleFloodMode()"
         style="width:100%;padding:10px;background:#0d1f1a;color:#00ffcc;
         border:1px solid #00ffcc;border-radius:6px;font-weight:bold;
         font-size:12px;cursor:pointer;letter-spacing:1px;transition:all 0.3s;">
         ⚡ SIMULATED MODE
       </button>
     </div>

     <div id="modeBadge" style="position:fixed;top:15px;right:15px;z-index:999999;
       font-family:'Courier New';font-size:10px;letter-spacing:2px;padding:8px 14px;
       border-radius:6px;border:1px solid rgba(0,255,204,0.4);
       background:rgba(0,255,204,0.08);color:#00ffcc;">
       ⚡ SIMULATED
     </div>

     <div id="searchResultCard" style="display:none;background:#0d1a14;border:1px solid #00ffcc44;
       border-radius:8px;padding:12px;margin-bottom:10px;font-size:11px;font-family:'Courier New',monospace;">
     </div>

     <div id="dataSourceTag" style="font-size:9px;font-family:'Courier New',monospace;color:#556;
       letter-spacing:2px;margin-bottom:12px;padding:6px 10px;background:#111;
       border-radius:4px;border:1px solid #222;">⬛ SELECT MODE TO BEGIN</div>

     <div style="background:linear-gradient(90deg,#111,#222);padding:15px;border-radius:8px;
       margin-bottom:8px;border:1px solid #00ffcc;text-align:center;">
       <div style="font-size:10px;color:#00ffcc;text-transform:uppercase;letter-spacing:1px;">Avg Zonal Readiness</div>
       <div style="font-size:38px;font-weight:bold;margin:4px 0;" id="avgReadiness">—</div>
       <div style="font-size:9px;color:#556;">Structural + Maintenance + Spatial Load</div>
     </div>

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
       </div>
       <div id="hkScenarioPanel">
         <select id="hkScenario" onchange="applyHKScenario()"
           style="width:100%;background:#0a0a12;color:#00aaff;padding:8px;
           border-radius:4px;font-size:10px;font-family:'Courier New',monospace;
           border:1px solid #1a3a5a;cursor:pointer;">
           <option value="0">🟢 NORMAL — &lt;10k cusecs</option>
           <option value="50000">🔵 ADVISORY — 50k cusecs</option>
           <option value="100000">🟡 WARNING — 1 lakh cusecs</option>
           <option value="200000">🟠 DANGER — 2 lakh cusecs</option>
           <option value="350000">🔴 SEVERE — 3.5 lakh cusecs</option>
         </select>
       </div>
     </div>

     <div id="sliderPanel">
       <div style="background:#1a1a1a;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #333;">
         <label style="font-size:12px;font-weight:bold;display:block;margin-bottom:5px;">
           🌧️ BASE RAINFALL: <span id="rainDisp" style="color:#00ffcc">10 mm/hr</span>
         </label>
         <input type="range" min="0" max="150" value="10" id="rainSlider" style="width:100%;cursor:pointer;">
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
       #searchSuggestions::-webkit-scrollbar-thumb{{background:#333;border-radius:2px}}
     </style>
   </div>
"""

    # Ensure the return statement is indented exactly the same as data_script
    return data_script + dashboard_html