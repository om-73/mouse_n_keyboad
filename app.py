import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# -------------------------
# Flask app & DB setup
# -------------------------
basedir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(basedir, "data")
os.makedirs(data_dir, exist_ok=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for Vercel frontend

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(data_dir, "gesture_data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class GestureLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String)
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)
    mode = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# -------------------------
# Flask routes
# -------------------------
@app.route("/")
def index():
    # Only acts as API or simple health check
    return "Backend is running. Use the Frontend to interact."

@app.route("/logs")
def logs_page():
    logs = GestureLog.query.order_by(GestureLog.timestamp.desc()).all()
    return render_template("log.html", logs=logs)

# GET endpoint to fetch logs
@app.route("/api/logs", methods=["GET"])
def get_logs_json():
    logs = GestureLog.query.order_by(GestureLog.timestamp.desc()).all()
    return jsonify([{
        "id": l.id,
        "text": l.text,
        "x": l.x,
        "y": l.y,
        "mode": l.mode,
        "timestamp": l.timestamp.isoformat()
    } for l in logs])

# POST endpoint to save logs from Frontend
@app.route("/api/logs", methods=["POST"])
def create_log():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    
    log = GestureLog(
        text=data.get("text"),
        x=data.get("x"),
        y=data.get("y"),
        mode=data.get("mode")
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "created"}), 201

# -------------------------
# Remote Cursor State (In-Memory)
# -------------------------
cursor_state = {
    "x": 0, 
    "y": 0, 
    "click": False,
    "last_updated": datetime.utcnow()
}

@app.route("/api/cursor", methods=["GET", "POST"])
def cursor_api():
    global cursor_state
    if request.method == "POST":
        data = request.json
        if data:
            cursor_state["x"] = data.get("x", cursor_state["x"])
            cursor_state["y"] = data.get("y", cursor_state["y"])
            if data.get("click"):
                cursor_state["click"] = True
            cursor_state["last_updated"] = datetime.utcnow()
        return jsonify({"status": "updated"}), 200
    
    else: # GET
        # reading state (for local script)
        # We return the state and reset 'click' to False so it triggers only once
        resp = cursor_state.copy()
        cursor_state["click"] = False 
        return jsonify(resp), 200

@app.route("/delete/<int:log_id>", methods=["POST"])
def delete_log(log_id):
    log = GestureLog.query.get(log_id)
    if log:
        db.session.delete(log)
        db.session.commit()
    return redirect(url_for("logs_page"))

@app.route("/delete_all", methods=["POST"])
def delete_all_logs():
    db.session.query(GestureLog).delete()
    db.session.commit()
    return redirect(url_for("logs_page"))

# Legacy route for compatibility, though frontend handles mode state now
@app.route("/switch", methods=["POST"])
def switch_mode():
    data = request.get_json(silent=True) or {}
    return jsonify({"status": "ok", "mode": data.get("mode", "mouse")})

@app.route("/quit")
def quit_app():
    # Only relevant for local, but keeping endpoint to not break frontend links
    return ("", 204)

# -------------------------
# Run Flask app
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True, use_reloader=False)
