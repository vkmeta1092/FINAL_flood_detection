from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return """<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
#map { width:100vw; height:100vh; }
#panel {
  position:fixed; top:15px; left:15px; z-index:9999;
  background:rgba(0,0,0,0.9); color:#fff;
  padding:14px; border-radius:10px;
  border:1px solid #00aaff; width:260px;
  font-family:monospace; font-size:11px;
}
#panel button {
  width:100%; padding:8px; margin-bottom:5px;
  border:none; border-radius:5px;
  cursor:pointer; font-family:monospace;
  font-weight:bold; font-size:11px;
}
#exportBtn { background:#00aaff; color:#000; }
#undoBtn   { background:#332200; color:#ffaa00; border:1px solid #ffaa00; }
#clearBtn  { background:#220000; color:#ff4444; border:1px solid #ff4444; }
#out {
  display:none; margin-top:8px;
  background:#000; border:1px solid #00ffcc;
  border-radius:5px; padding:8px;
}
#out textarea {
  width:100%; height:90px; background:#000;
  color:#00ffcc; border:none; outline:none;
  font-family:monospace; font-size:9px; resize:none;
}
#copyBtn { background:#001a1a; color:#00ffcc; border:1px solid #00ffcc; margin-top:5px; }
</style>
</head><body>
<div id="map"></div>
<div id="panel">
  <div style="color:#00aaff;font-size:13px;font-weight:bold;margin-bottom:6px;">
    YAMUNA TRACER</div>
  <div style="color:#556;font-size:9px;margin-bottom:10px;">
    Click along the river. North to South.</div>
  <div style="text-align:center;margin-bottom:8px;">
    Points: <span id="cnt" style="color:#00ffcc;font-weight:bold;">0</span>
  </div>
  <div id="last" style="color:#445;font-size:9px;text-align:center;margin-bottom:8px;">--</div>
  <button id="undoBtn"   onclick="undoLast()">UNDO LAST</button>
  <button id="clearBtn"  onclick="clearAll()">CLEAR ALL</button>
  <button id="exportBtn" onclick="doExport()">EXPORT</button>
  <div id="out">
    <textarea id="outTxt" readonly></textarea>
    <button id="copyBtn" onclick="doCopy()">COPY TO CLIPBOARD</button>
    <div id="copied" style="color:#00ffcc;font-size:9px;text-align:center;display:none;">
      Copied! Paste into app.py
    </div>
  </div>
</div>
<script>
var map = L.map('map').setView([28.65, 77.23], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution:'OSM', maxZoom:20}).addTo(map);

var pts = [], mks = [], poly = null;

map.on('click', function(e) {
  var lat = parseFloat(e.latlng.lat.toFixed(5));
  var lng = parseFloat(e.latlng.lng.toFixed(5));
  pts.push([lat, lng]);

  var mk = L.circleMarker([lat, lng], {
    radius:5, color:'#ff4444', weight:2,
    fill:true, fillColor:'#ff4444', fillOpacity:0.9
  }).bindTooltip(String(pts.length), {permanent:true, className:'', offset:[8,-8]})
    .addTo(map);
  mks.push(mk);

  if (poly) map.removeLayer(poly);
  if (pts.length > 1) {
    poly = L.polyline(pts, {color:'#00d4ff', weight:4}).addTo(map);
  }

  document.getElementById('cnt').innerText  = pts.length;
  document.getElementById('last').innerText =
    'Last: ' + lat + ', ' + lng;
});

function undoLast() {
  if (!pts.length) return;
  pts.pop();
  if (mks.length) { map.removeLayer(mks.pop()); }
  if (poly) map.removeLayer(poly);
  if (pts.length > 1) {
    poly = L.polyline(pts, {color:'#00d4ff', weight:4}).addTo(map);
  }
  document.getElementById('cnt').innerText = pts.length;
  document.getElementById('last').innerText =
    pts.length ? 'Last: ' + pts[pts.length-1][0] + ', ' + pts[pts.length-1][1] : '--';
}

function clearAll() {
  if (!confirm('Clear all points?')) return;
  pts = [];
  for (var i=0; i<mks.length; i++) map.removeLayer(mks[i]);
  mks = [];
  if (poly) { map.removeLayer(poly); poly = null; }
  document.getElementById('cnt').innerText      = 0;
  document.getElementById('last').innerText     = '--';
  document.getElementById('out').style.display  = 'none';
}

function doExport() {
  if (pts.length < 2) { alert('Need at least 2 points!'); return; }
  var lines = [];
  for (var i=0; i<pts.length; i++) {
    var c = (i < pts.length-1) ? ',' : '';
    lines.push('    (' + pts[i][0] + ', ' + pts[i][1] + ')' + c);
  }
  var txt = 'YAMUNA_POLYLINE = [\\n' + lines.join('\\n') + '\\n]';
  document.getElementById('outTxt').value       = txt;
  document.getElementById('out').style.display  = 'block';
  document.getElementById('copied').style.display = 'none';
}

function doCopy() {
  var ta = document.getElementById('outTxt');
  ta.select();
  document.execCommand('copy');
  document.getElementById('copied').style.display = 'block';
  setTimeout(function() {
    document.getElementById('copied').style.display = 'none';
  }, 3000);
}
</script>
</body></html>"""

if __name__ == '__main__':
    app.run(port=5001, debug=False)
