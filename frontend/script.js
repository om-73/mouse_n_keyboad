(function () {
  const buttons = document.querySelectorAll(".buttons .btn[data-mode]");
  const modeLabel = document.getElementById("modeLabel");

  // Use the backend URL defined in index.html (window.BACKEND_URL)
  // or fallback to localhost if not defined
  const API_BASE = window.BACKEND_URL || "http://localhost:5050";

  console.log("Using Backend URL:", API_BASE);

  async function switchMode(mode) {
    try {
      const res = await fetch(API_BASE + "/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        modeLabel.textContent = data.mode;
      } else {
        alert("Switch failed: " + (data.message || "unknown error"));
      }
    } catch (e) {
      console.error(e);
      alert("Network error switching mode. properties check console");
    }
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const m = btn.getAttribute("data-mode");
      switchMode(m);
    });
  });

  document.addEventListener("keydown", (ev) => {
    const k = ev.key.toLowerCase();
    if (k === "k") switchMode("keyboard");
    if (k === "m") switchMode("mouse");
    if (k === "q") fetch(API_BASE + "/quit");
  });

  // Initialize Video Stream
  const videoImg = document.getElementById("videoStream");
  if (videoImg) {
    // Connect to the video stream endpoint
    videoImg.src = API_BASE + "/video";
  }
})();
