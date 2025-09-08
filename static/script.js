(function () {
  const buttons = document.querySelectorAll(".buttons .btn[data-mode]");
  const modeLabel = document.getElementById("modeLabel");

  async function switchMode(mode) {
    try {
      const res = await fetch("/switch", {
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
      alert("Network error switching mode");
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
    if (k === "q") fetch("/quit");
  });
})();
