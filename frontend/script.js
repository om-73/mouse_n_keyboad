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

// UI Elements
const loadingOverlay = document.getElementById("loadingOverlay");
const errorMsg = document.getElementById("errorMsg");
const backendInput = document.getElementById("backendUrlInput");
const saveUrlBtn = document.getElementById("saveUrlBtn");
const statusSpan = document.getElementById("connectionStatus");

// Configuration
// Configuration
let defaultUrl = "http://localhost:5050";
if (window.location.protocol === 'https:') {
  defaultUrl = ""; // Force user input on production to avoid Mixed Content
}
let API_BASE = localStorage.getItem("BACKEND_URL") || window.BACKEND_URL || defaultUrl;
backendInput.value = API_BASE;

// Update API Base when user clicks Save
saveUrlBtn.addEventListener("click", () => {
  let url = backendInput.value.trim();
  // Remove trailing slash
  if (url.endsWith("/")) url = url.slice(0, -1);

  if (url) {
    API_BASE = url;
    localStorage.setItem("BACKEND_URL", API_BASE);
    window.BACKEND_URL = API_BASE; // Update global for other scripts
    checkConnection();
    alert("URL Updated! Try performing a gesture to see if logs work.");
  }
});

async function checkConnection() {
  statusSpan.textContent = "Checking...";
  statusSpan.style.color = "yellow";
  try {
    const res = await fetch(API_BASE + "/");
    if (res.ok) {
      statusSpan.textContent = "Connected (API OK)";
      statusSpan.style.color = "#4ade80"; // green
    } else {
      throw new Error(res.statusText);
    }
  } catch (e) {
    statusSpan.textContent = "Disconnected (Check URL)";
    statusSpan.style.color = "#ef4444"; // red
    console.warn("Backend check failed:", e);
  }
}
// Check on load
checkConnection();


let handLandmarker = undefined;
let webcamRunning = false;
let lastVideoTime = -1;
let results = undefined;
let mode = "mouse"; // 'mouse' or 'keyboard'

// Virtual Mouse State
let cursorX = 0;
let cursorY = 0;
const SMOOTHING = 0.5;

// Initialize MediaPipe
const createHandLandmarker = async () => {
  try {
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
    loadingOverlay.style.display = "none"; // Hide loading screen
    enableCam();
  } catch (e) {
    console.error(e);
    errorMsg.textContent = "Failed to load AI Model: " + e.message;
  }
};

const enableCam = () => {
  if (!handLandmarker) return;

  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
      video.srcObject = stream;
      video.addEventListener("loadeddata", predictWebcam);
      webcamRunning = true;
    }).catch(err => {
      console.error(err);
      errorMsg.textContent = "Camera Access Denied: " + err.message;
      loadingOverlay.style.display = "flex"; // Show error
    });
  } else {
    errorMsg.textContent = "Webcam not supported in this browser.";
    loadingOverlay.style.display = "flex";
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
    try {
      results = handLandmarker.detectForVideo(video, startTimeMs);
    } catch (e) {
      console.error("Detection error:", e);
    }
  }

  canvasCtx.save();
  canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

  if (mode === 'keyboard') {
    drawKeyboard(canvasCtx);
  }

  if (results && results.landmarks) {
    for (const landmarks of results.landmarks) {
      drawLandmarks(landmarks);
      drawSkeleton(landmarks); // Add skeleton for visibility
      processGestures(landmarks);
    }
  }

  canvasCtx.restore();

  if (webcamRunning === true) {
    window.requestAnimationFrame(predictWebcam);
  }
};

function drawLandmarks(landmarks) {
  canvasCtx.fillStyle = "#00FF00";
  for (const point of landmarks) {
    const x = point.x * canvasElement.width;
    const y = point.y * canvasElement.height;
    canvasCtx.beginPath();
    canvasCtx.arc(x, y, 4, 0, 2 * Math.PI);
    canvasCtx.fill();
  }
}

function drawSkeleton(landmarks) {
  canvasCtx.strokeStyle = "#00FF00";
  canvasCtx.lineWidth = 2;
  // Connections from MediaPipe Hands
  // Thumb
  connect(landmarks, 0, 1); connect(landmarks, 1, 2); connect(landmarks, 2, 3); connect(landmarks, 3, 4);
  // Index
  connect(landmarks, 0, 5); connect(landmarks, 5, 6); connect(landmarks, 6, 7); connect(landmarks, 7, 8);
  // Middle
  connect(landmarks, 5, 9); connect(landmarks, 9, 10); connect(landmarks, 10, 11); connect(landmarks, 11, 12);
  // Ring
  connect(landmarks, 9, 13); connect(landmarks, 13, 14); connect(landmarks, 14, 15); connect(landmarks, 15, 16);
  // Pinky
  connect(landmarks, 13, 17); connect(landmarks, 17, 18); connect(landmarks, 18, 19); connect(landmarks, 19, 20);
  // Palm
  connect(landmarks, 0, 17);
}
function connect(landmarks, i, j) {
  const p1 = landmarks[i];
  const p2 = landmarks[j];
  canvasCtx.beginPath();
  canvasCtx.moveTo(p1.x * canvasElement.width, p1.y * canvasElement.height);
  canvasCtx.lineTo(p2.x * canvasElement.width, p2.y * canvasElement.height);
  canvasCtx.stroke();
}


function processGestures(landmarks) {
  const indexTip = landmarks[8];
  const thumbTip = landmarks[4];

  // FLIP X
  const x = (1 - indexTip.x) * canvasElement.width;
  const y = indexTip.y * canvasElement.height;

  if (mode === 'mouse') {
    // Smoothing
    cursorX = cursorX * SMOOTHING + x * (1 - SMOOTHING);
    cursorY = cursorY * SMOOTHING + y * (1 - SMOOTHING);

    cursor.style.display = "block";
    cursor.style.left = `${cursorX}px`;
    cursor.style.top = `${cursorY}px`;

    // Click Detection (Pinch Thumb + Index)
    // NOTE: Previous logic used Pinky(20). Let's support both or stick to standard.
    // Standard Pinch is Thumb(4) to Index(8).
    // Let's use Thumb-Index for clearer web interaction.
    // Original requirement: "pinch thumb–pinky". Keeping mostly compatible.
    const clickFinger = landmarks[20]; // Pinky

    // Normalized distance
    const dist = Math.hypot(thumbTip.x - clickFinger.x, thumbTip.y - clickFinger.y);

    if (dist < 0.08) { // Relaxed threshold slightly
      cursor.style.backgroundColor = "blue";
      logGesture("Click", x, y, "mouse");
    } else {
      cursor.style.backgroundColor = "red";
    }

  } else if (mode === 'keyboard') {
    checkKeyboardHit(x, y);
  }
}

async function logGesture(text, x, y, mode) {
  try {
    // Only log if we have a valid non-localhost URL or we really intend to log
    await fetch(API_BASE + "/api/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, x: x | 0, y: y | 0, mode })
    });
    console.log(`Logged: ${text}`);
  } catch (e) {
    // Silent fail to not spam console too much, or use status indicator
  }
}

// ... Keyboard Logic (Unchanged) ...
const keys = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["Z", "X", "C", "V", "B", "N", "M"]
];
function drawKeyboard(ctx) {
  ctx.font = "20px Arial";
  let startY = 300;
  const keyW = 40; const keyH = 40; const padding = 10;
  keys.forEach((row, rIdx) => {
    let startX = 50 + (rIdx * 20);
    row.forEach((key, kIdx) => {
      const kx = startX + kIdx * (keyW + padding);
      const ky = startY + rIdx * (keyH + padding);
      ctx.fillStyle = "rgba(0,0,0,0.5)"; ctx.fillRect(kx, ky, keyW, keyH);
      ctx.strokeStyle = "white"; ctx.strokeRect(kx, ky, keyW, keyH);
      ctx.fillStyle = "white"; ctx.fillText(key, kx + 10, ky + 28);
    });
  });
}
function checkKeyboardHit(x, y) {
  // TODO: Implement hit testing
}

buttons.forEach((btn) => {
  btn.addEventListener("click", () => {
    mode = btn.getAttribute("data-mode");
    modeLabel.textContent = mode;
    if (mode === 'keyboard') cursor.style.display = 'none';
  });
});

createHandLandmarker();
