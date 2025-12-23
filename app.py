import os
import cv2
import time
import threading
import numpy as np
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Try importing pyautogui, handling failure for headless servers
try:
    import pyautogui
    # On Linux/Render headless, this might still import but fail on .size()
    # verify connection to X server if possible or catch later
    _screen_w, _screen_h = pyautogui.size()
    HEADLESS = False
except (ImportError, KeyError, Exception):
    print("WARNING: PyAutoGUI not available (Headless mode). Mouse control disabled.")
    pyautogui = None
    HEADLESS = True

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
# Webcam & screen setup
# -------------------------
# Attempt to open camera
cap = None
if not HEADLESS:
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = None
    except Exception:
        cap = None

if cap:
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
else:
    frame_w, frame_h = 640, 480

if not HEADLESS and pyautogui:
    try:
        screen_w, screen_h = pyautogui.size()
    except Exception:
        screen_w, screen_h = 1920, 1080
        HEADLESS = True
else:
    screen_w, screen_h = 1920, 1080

# -------------------------
# Mediapipe hands
# -------------------------
try:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    mp_draw = mp.solutions.drawing_utils
except Exception:
    print("WARNING: Mediapipe not available or failed to init.")
    hands = None
    mp_draw = None


# -------------------------
# App state
# -------------------------
mode = "mouse"        # 'mouse' or 'keyboard'
running = True
typed_text = ""

keys = [
    ["Q","W","E","R","T","Y","U","I","O","P"],
    ["A","S","D","F","G","H","J","K","L"],
    ["Z","X","C","V","B","N","M"]
]
keyboard_rects = []
last_press_time = {}
pyautogui_lock = threading.Lock()

# -------------------------
# Helper functions
# -------------------------
def save_gesture(text=None, x=None, y=None, mode="mouse"):
    if not any([text, x, y]):
        return
    try:
        with app.app_context():
            log = GestureLog(text=text, x=x, y=y, mode=mode)
            db.session.add(log)
            db.session.commit()
    except Exception as e:
        print(f"DB Error: {e}")

def draw_keyboard(img):
    h, w, _ = img.shape
    key_w = max(w // 12, 40)
    key_h = max(h // 11, 38)
    keyboard_rects.clear()
    y_start = h - 3 * (key_h + 10) - 20
    y_start = max(y_start, 100)

    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            x = j * (key_w + 6) + 30
            y = y_start + i * (key_h + 6)
            rect = (x, y, key_w, key_h, key)
            keyboard_rects.append(rect)
            cv2.rectangle(img, (x, y), (x + key_w, y + key_h), (50, 50, 255), 2)
            cv2.putText(img, key, (x + key_w // 4, y + int(key_h * 0.7)),
                        cv2.FONT_HERSHEY_SIMPLEX, max(key_h / 50, 0.8), (255, 255, 255), 2)

def get_finger_points(hand_landmarks):
    points = {}
    for idx in [4, 8, 12, 16, 20]:
        cx = int(hand_landmarks.landmark[idx].x * frame_w)
        cy = int(hand_landmarks.landmark[idx].y * frame_h)
        points[idx] = (cx, cy)
    return points

def move_mouse_safe(point):
    if HEADLESS or not pyautogui: return
    with pyautogui_lock:
        x_ratio = screen_w / frame_w
        y_ratio = screen_h / frame_h
        try:
            pyautogui.moveTo(int(point[0] * x_ratio), int(point[1] * y_ratio))
        except: pass

def press_key_safe(key):
    if HEADLESS or not pyautogui: return
    with pyautogui_lock:
        try:
            pyautogui.press(key.lower())
        except: pass

def check_click(landmarks):
    thumb = landmarks[4]
    pinky = landmarks[20]
    dist = ((thumb[0]-pinky[0])**2 + (thumb[1]-pinky[1])**2) ** 0.5
    return dist < 40

# -------------------------
# Video frame generator
# -------------------------
def generate_frames():
    global mode, running, typed_text
    while running:
        frame = None
        ok = False
        
        if cap:
            ok, frame = cap.read()
        
        if not ok or frame is None:
            # Generate a placeholder "No Camera" frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "NO CAMERA / HEADLESS MODE", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            # Sleep to prevent tight loop in headless
            time.sleep(0.1)

        if ok:
             frame = cv2.flip(frame, 1)
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = None
        if hands:
            results = hands.process(rgb)

        if mode == "keyboard":
            draw_keyboard(frame)
            
        if results and results.multi_hand_landmarks:
            for handLms, handType in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handType.classification[0].label
                points = get_finger_points(handLms)

                for pid, (px, py) in points.items():
                    cv2.circle(frame, (px, py), 8, (0, 255, 255), -1)

                if mode == "mouse" and label == "Left":
                    if 8 in points:
                        move_mouse_safe(points[8])
                    if check_click(points):
                        with pyautogui_lock:
                            pyautogui.click()
                        save_gesture(text="Click", x=points[8][0], y=points[8][1], mode="mouse")

                elif mode == "keyboard" and label == "Right":
                    # --- MODIFIED: allow all five fingertips to press keys ---
                    for fid in [4, 8, 12, 16, 20]:  # Thumb, Index, Middle, Ring, Pinky
                        if fid in points:
                            x, y = points[fid]
                            key_pressed = None
                            for rx, ry, rw, rh, key in keyboard_rects:
                                if rx < x < rx + rw and ry < y < ry + rh:
                                    key_pressed = key
                                    cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), -1)
                                    cv2.putText(frame, key, (rx + rw // 4, ry + int(rh * 0.7)),
                                                cv2.FONT_HERSHEY_SIMPLEX, max(rh / 50, 0.8), (0, 0, 0), 2)
                                    break
                            if key_pressed:
                                now = time.time()
                                if key_pressed not in last_press_time or now - last_press_time[key_pressed] > 0.3:
                                    last_press_time[key_pressed] = now
                                    press_key_safe(key_pressed)
                                    typed_text += key_pressed
                                    save_gesture(text=key_pressed, x=x, y=y, mode="keyboard")

                mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)

        cv2.rectangle(frame, (30, 20), (900, 80), (0, 0, 0), -1)
        cv2.putText(frame, typed_text[-50:], (40, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

# -------------------------
# Flask routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html", mode=mode)

@app.route("/video")
def video():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/switch", methods=["POST"])
def switch_mode():
    global mode
    data = request.get_json(silent=True) or {}
    new_mode = data.get("mode")
    if new_mode in ("mouse", "keyboard"):
        mode = new_mode
        return jsonify({"status": "ok", "mode": mode})
    return jsonify({"status": "error", "message": "mode must be 'mouse' or 'keyboard'"}), 400

@app.route("/logs")
def logs_page():
    logs = GestureLog.query.order_by(GestureLog.timestamp.desc()).all()
    return render_template("log.html", logs=logs)

@app.route("/api/logs")
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

@app.route("/quit")
def quit_app():
    global running
    running = False
    try:
        cap.release()
    except Exception:
        pass
    try:
        hands.close()
    except Exception:
        pass
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    return ("", 204)

# -------------------------
# Run Flask app
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True, use_reloader=False)
