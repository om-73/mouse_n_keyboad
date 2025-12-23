# Gesture Mouse & Keyboard

A web-based gesture control system using OpenCV and MediaPipe. Originally designed for local desktop control, this project has been adapted for cloud deployment with a split architecture.

## 🚀 Features
- **Mouse Mode**: Control cursor with Left Hand (Index finger moves, Thumb-Pinky pinch clicks).
- **Keyboard Mode**: Press keys with Right Hand fingertips.
- **Headless Support**: Backend runs on servers without cameras/screens (Render friendly).

## 🛠 Project Structure
- **Backend (`/`)**: Flask app handling logic and hosting the video stream API.
- **Frontend (`/frontend`)**: Static HTML/JS/CSS acting as the user interface.

## 📦 Deployment Guide

### 1. Backend (Render)
1.  Create a new **Blueprint** or **Web Service** on [Render](https://render.com).
2.  Connect this repository.
3.  Render will auto-detect `render.yaml` and deploy.
4.  **Note**: On Render, the video feed will show a "Headless Mode" placeholder since there is no physical webcam.

### 2. Frontend (Vercel)
1.  Create a new project on [Vercel](https://vercel.com).
2.  Import this repository.
3.  **Crucial Step**: Set the **Root Directory** to `frontend`.
4.  Deploy.

### 3. Connect Frontend to Backend
Once deployed, update the backend URL in `frontend/index.html`:
```javascript
<script>
    window.BACKEND_URL = "https://your-render-app-name.onrender.com"; 
</script>
```

## 💻 Local Developement
1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run Backend**:
    ```bash
    python app.py
    ```
3.  **Run Frontend**:
    Open `frontend/index.html` in your browser.
    (Or servce it with `npx serve frontend`)
