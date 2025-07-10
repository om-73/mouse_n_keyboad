import cv2
import mediapipe as mp
import pyautogui
from flask import Flask, render_template, Response, request
import threading

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(3, 1280)  # Wider frame
cap.set(4, 720)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

mode = 'mouse'  # Default mode
running = True
typed_text = ""

keys = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
]

keyboard_rects = []
pressed = {}

def draw_keyboard(img):
    h, w, _ = img.shape
    key_w = w // 12
    key_h = 80
    keyboard_rects.clear()
    y_start = h - 3 * key_h - 40

    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            x = j * (key_w + 5) + 30
            y = y_start + i * (key_h + 5)
            rect = (x, y, key_w, key_h, key)
            keyboard_rects.append(rect)
            cv2.rectangle(img, (x, y), (x + key_w, y + key_h), (50, 50, 255), 2)
            cv2.putText(img, key, (x + 20, y + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

def get_finger_points(hand_landmarks):
    points = {}
    for id in [4, 8, 12, 16, 20]:
        cx = int(hand_landmarks.landmark[id].x * 1280)
        cy = int(hand_landmarks.landmark[id].y * 720)
        points[id] = (cx, cy)
    return points

def check_click(landmarks):
    thumb = landmarks[4]
    pinky = landmarks[20]
    dist = ((thumb[0] - pinky[0])**2 + (thumb[1] - pinky[1])**2) ** 0.5
    return dist < 40

def generate_frames():
    global mode, running, typed_text

    while running:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if mode == 'keyboard':
            draw_keyboard(frame)

        if results.multi_hand_landmarks:
            for handLms, handType in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handType.classification[0].label  # "Left" or "Right"
                points = get_finger_points(handLms)

                # Draw fingertip circles and labels
                for id, (x, y) in points.items():
                    cv2.circle(frame, (x, y), 10, (0, 255, 255), -1)
                    cv2.putText(frame, str(id), (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                if mode == 'mouse' and label == 'Left':
                    index = points[8]
                    pyautogui.moveTo(index[0], index[1])
                    if check_click(points):
                        pyautogui.click()

                elif mode == 'keyboard' and label == 'Right':
                    index_finger = points[8]
                    x, y = index_finger
                    key_pressed = None

                    for rect in keyboard_rects:
                        rx, ry, rw, rh, key = rect
                        if rx < x < rx + rw and ry < y < ry + rh:
                            key_pressed = key
                            cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), -1)
                            cv2.putText(frame, key, (rx + 20, ry + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
                            break

                    if key_pressed:
                        if key_pressed not in pressed:
                            pressed[key_pressed] = True
                            pyautogui.press(key_pressed.lower())
                            typed_text += key_pressed
                    else:
                        pressed.clear()

                mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)

        # Draw typed text input field
        cv2.rectangle(frame, (30, 20), (900, 80), (0, 0, 0), -1)
        cv2.putText(frame, typed_text[-50:], (40, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html', mode=mode)

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/switch/<m>')
def switch_mode(m):
    global mode
    if m in ['mouse', 'keyboard']:
        mode = m
    return ('', 204)

@app.route('/quit')
def quit():
    global running
    running = False
    cap.release()
    return ('', 204)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
