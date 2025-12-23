import {
  HandLandmarker,
  FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm";

const video = document.getElementById("webcam");
const canvasElement = document.getElementById("output_canvas");
const canvasCtx = canvasElement.getContext("2d");
const cursor = document.getElementById("virtual-cursor");
const modeLabel = document.getElementById("modeLabel");
const buttons = document.querySelectorAll(".buttons .btn[data-mode]");

// API Configuration
// CRITICAL: Update this to your HTTPS Render URL for production!
// e.g., "https://my-app.onrender.com"
const API_BASE = window.BACKEND_URL || "http://localhost:5050";

let handLandmarker = undefined;
let webcamRunning = false;
let lastVideoTime = -1;
let results = undefined;
let mode = "mouse"; // 'mouse' or 'keyboard'

// Virtual Mouse State
let cursorX = 0;
let cursorY = 0;
const SMOOTHING = 0.5; // Simple exponential smoothing

// Initialize MediaPipe Hand Landmarker
const createHandLandmarker = async () => {
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
  );
  handLandmarker = await HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`,
      delegate: "GPU"
    },
    runningMode: "VIDEO",
    numHands: 2
  });
  console.log("HandLandmarker loaded");
  enableCam();
};

const enableCam = () => {
  if (!handLandmarker) {
    console.log("Wait! objectDetector not loaded yet.");
    return;
  }

  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
      video.srcObject = stream;
      video.addEventListener("loadeddata", predictWebcam);
      webcamRunning = true;
    });
  }
};

const predictWebcam = async () => {
  canvasElement.style.width = video.videoWidth;
  canvasElement.style.height = video.videoHeight;
  canvasElement.width = video.videoWidth;
  canvasElement.height = video.videoHeight;

  let startTimeMs = performance.now();
  if (lastVideoTime !== video.currentTime) {
    lastVideoTime = video.currentTime;
    results = handLandmarker.detectForVideo(video, startTimeMs);
  }

  canvasCtx.save();
  canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

  // Draw Virtual Keyboard if in keyboard mode
  if (mode === 'keyboard') {
    drawKeyboard(canvasCtx);
  }

  if (results.landmarks) {
    for (const landmarks of results.landmarks) {
      drawLandmarks(landmarks);
      processGestures(landmarks);
    }
  }

  canvasCtx.restore();

  if (webcamRunning === true) {
    window.requestAnimationFrame(predictWebcam);
  }
};

function drawLandmarks(landmarks) {
  // Simple drawing of landmarks
  canvasCtx.fillStyle = "#00FF00";
  for (const point of landmarks) {
    const x = point.x * canvasElement.width;
    const y = point.y * canvasElement.height;
    canvasCtx.beginPath();
    canvasCtx.arc(x, y, 4, 0, 2 * Math.PI);
    canvasCtx.fill();
  }
}

function processGestures(landmarks) {
  // Index tip is landmark 8
  const indexTip = landmarks[8];
  const thumbTip = landmarks[4];
  const middleTip = landmarks[12];

  // FLIP X to match the mirrored video ("Selfie View")
  // If video is scaleX(-1), then x=0 (left) is visually Right.
  // We want logic to match visual.
  const x = (1 - indexTip.x) * canvasElement.width;
  const y = indexTip.y * canvasElement.height;

  if (mode === 'mouse') {
    // --- Virtual Mouse Logic ---

    // Smoothing
    cursorX = cursorX * SMOOTHING + x * (1 - SMOOTHING);
    cursorY = cursorY * SMOOTHING + y * (1 - SMOOTHING);

    // Update virtual cursor position
    cursor.style.display = "block";
    cursor.style.left = `${cursorX}px`;
    cursor.style.top = `${cursorY}px`;

    // Click detection (Pinch Thumb + Index) - typically landmark 4 and 8
    // Using Thumb (4) and Pinky (20) as per original python code usually triggers 'click'
    // But original code used Thumb(4) - Pinky(20). Let's stick closer to standard pinch.
    // Let's use Thumb (4) and Index (8) for easier web pinch.
    // WAIT, original python code: "pinch thumb–pinky to click". Okay, let's replicate that.
    const pinkyTip = landmarks[20];

    // Calculate distance between Thumb and Pinky
    const dist = Math.hypot(
      (thumbTip.x - pinkyTip.x),
      (thumbTip.y - pinkyTip.y)
    );

    // Threshold check (normalized coordinates, so logic is slightly diff from pixels)
    // 0.05 is roughly "close" in normalized space
    if (dist < 0.05) {
      console.log("Click detected!");
      cursor.style.backgroundColor = "blue";
      // Optional: Trigger actual click on element under cursor
      // elementFromPoint uses clientX/Y, which needs mapping from video to screen
      // For now just visual feedback
      logGesture("Click", x, y, "mouse");
    } else {
      cursor.style.backgroundColor = "red";
    }

  } else if (mode === 'keyboard') {
    // --- Virtual Keyboard Logic ---
    // Simple hit test against drawn keys
    // Because we flipped 'x' above, it should match the logic keys drawn on canvas
    checkKeyboardHit(x, y);
  }
}
async function logGesture(text, x, y, mode) {
  // Debounce or limit logging
  try {
    await fetch(API_BASE + "/api/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        x: x | 0,
        y: y | 0,
        mode: mode
      })
    });
    console.log(`Logged: ${text} at ${x | 0},${y | 0}`);
  } catch (e) {
    console.error("Error logging gesture:", e);
  }
}

// --- Keyboard Drawing & Logic (Simplified) ---
const keys = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["Z", "X", "C", "V", "B", "N", "M"]
];
function drawKeyboard(ctx) {
  ctx.font = "20px Arial";
  let startY = 300;
  const keyW = 40;
  const keyH = 40;
  const padding = 10;

  keys.forEach((row, rIdx) => {
    let startX = 50 + (rIdx * 20); // indent rows
    row.forEach((key, kIdx) => {
      const kx = startX + kIdx * (keyW + padding);
      const ky = startY + rIdx * (keyH + padding);

      ctx.fillStyle = "rgba(0,0,0,0.5)";
      ctx.fillRect(kx, ky, keyW, keyH);
      ctx.strokeStyle = "white";
      ctx.strokeRect(kx, ky, keyW, keyH);
      ctx.fillStyle = "white";
      ctx.fillText(key, kx + 10, ky + 28);
    });
  });
}
function checkKeyboardHit(x, y) {
  // Basic hit testing implementation would go here
  // checking if x,y is inside any key rect
}

// Mode Switching
buttons.forEach((btn) => {
  btn.addEventListener("click", () => {
    mode = btn.getAttribute("data-mode");
    modeLabel.textContent = mode;
    if (mode === 'keyboard') {
      cursor.style.display = 'none';
    }
  });
});

createHandLandmarker();
