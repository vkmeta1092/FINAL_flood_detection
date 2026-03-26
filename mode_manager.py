# mode_manager.py
# ── Mode Manager ─────────────────────────────────────────────────────────────
# Handles SIMULATED <-> REAL mode switching via Blueprint
# Register in app.py with:
#   from mode_manager import mode_bp, get_current_mode
#   app.register_blueprint(mode_bp)
# Then in your /api/simulate route, call get_current_mode() to branch logic
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify

mode_bp = Blueprint('mode_manager', __name__)

# ── Global State ──────────────────────────────────────────────────────────────
_current_mode = "simulated"   # "simulated" | "real"
_mode_switched_at = None      # timestamp of last switch (for UI display)

# ── Public Getter (call from app.py) ─────────────────────────────────────────
def get_current_mode():
    return _current_mode

def is_real_mode():
    return _current_mode == "real"

def is_simulated_mode():
    return _current_mode == "simulated"

# ── Routes ────────────────────────────────────────────────────────────────────

@mode_bp.route('/set_mode', methods=['POST'])
def set_mode():
    global _current_mode, _mode_switched_at
    from datetime import datetime

    data = request.get_json(silent=True) or {}
    requested = data.get('mode', '').lower().strip()

    if requested not in ('simulated', 'real'):
        return jsonify({
            'success': False,
            'error': f'Invalid mode "{requested}". Use "simulated" or "real".'
        }), 400

    previous = _current_mode
    _current_mode = requested
    _mode_switched_at = datetime.now().strftime('%H:%M:%S')

    return jsonify({
        'success':    True,
        'mode':       _current_mode,
        'previous':   previous,
        'switched_at': _mode_switched_at,
        'message':    f'Switched from {previous} → {_current_mode} at {_mode_switched_at}'
    })


@mode_bp.route('/get_mode', methods=['GET'])
def get_mode():
    from datetime import datetime
    return jsonify({
        'mode':         _current_mode,
        'is_real':      _current_mode == 'real',
        'switched_at':  _mode_switched_at,
        'server_time':  datetime.now().strftime('%H:%M:%S')
    })
