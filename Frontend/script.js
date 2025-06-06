// =============================
// Globale Variablen
// =============================
let isFirstMessage = true;
const API_BASE = "http://localhost:5000";

// =============================
// Initialisierung
// =============================
document.addEventListener("DOMContentLoaded", () => {
  loadTheme();
  setupEventListeners();
  loadAvailableSources();
});

function setupEventListeners() {
  const input = document.getElementById("userInput");
  const sendButton = document.getElementById("sendButton");
  const charCounter = document.getElementById("charCounter");

  // Auto-resize für Textarea
  input.addEventListener("input", () => {
    autoResize(input);
    updateCharCounter();
    toggleSendButton();
  });

  // Enter zum Senden (Shift+Enter für neue Zeile)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Fokus auf Input beim Laden
  input.focus();
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function updateCharCounter() {
  const input = document.getElementById("userInput");
  const counter = document.getElementById("charCounter");
  const length = input.value.length;

  counter.textContent = `${length}/500`;
  counter.classList.toggle("warning", length > 400);
  counter.classList.toggle("error", length >= 500);
}

function toggleSendButton() {
  const input = document.getElementById("userInput");
  const button = document.getElementById("sendButton");
  button.disabled = !input.value.trim();
}

// =============================
// Chat-Funktionalität
// =============================
async function sendMessage() {
  const input = document.getElementById("userInput");
  const message = input.value.trim();

  if (!message) return;

  // Willkommensnachricht ausblenden
  if (isFirstMessage) {
    document.getElementById("welcomeMessage").classList.add("fade-out");
    setTimeout(() => {
      document.getElementById("welcomeMessage").style.display = "none";
    }, 300);
    isFirstMessage = false;
  }

  // Benutzernachricht hinzufügen
  addMessage(message, "user");

  // Input zurücksetzen
  input.value = "";
  input.style.height = "auto";
  updateCharCounter();
  toggleSendButton();

  // Status anzeigen
  showStatus("Suche in Dokumenten...");

  try {
    const response = await fetch(`${API_BASE}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: message }),
    });

    const data = await response.json();

    hideStatus();

    if (response.ok) {
      addBotMessage(data);
    } else {
      addMessage(`Fehler: ${data.error || "Unbekannter Fehler"}`, "bot error");
    }
  } catch (error) {
    hideStatus();
    addMessage(
      "Verbindungsfehler. Bitte versuchen Sie es später erneut.",
      "bot error"
    );
    console.error("API-Fehler:", error);
  }
}

function askExample(question) {
  document.getElementById("userInput").value = question;
  updateCharCounter();
  toggleSendButton();
  sendMessage();
}

function addMessage(text, type) {
  const container = document.getElementById("chatMessages");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}`;

  if (type === "user") {
    messageDiv.innerHTML = `
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;
  }

  container.appendChild(messageDiv);
  messageDiv.scrollIntoView({ behavior: "smooth", block: "end" });
}

function addBotMessage(data) {
  const container = document.getElementById("chatMessages");
  const messageDiv = document.createElement("div");
  messageDiv.className = "message bot";

  // Confidence-Klasse hinzufügen
  messageDiv.classList.add(`confidence-${data.confidence}`);

  let sourcesHtml = "";
  if (data.sources && data.sources.length > 0) {
    sourcesHtml = `
      <div class="sources">
        <h4><i class="fas fa-book"></i> Quellen:</h4>
        ${data.sources
          .map(
            (source) => `
            <div class="source-item">
              <span class="source-name">${escapeHtml(source.quelle)}</span>
              <span class="source-chunk">Abschnitt ${source.chunk_id}</span>
              <span class="source-relevance">${source.relevanz}</span>
            </div>
          `
          )
          .join("")}
      </div>
    `;
  }

  const confidenceIcon = getConfidenceIcon(data.confidence);

  messageDiv.innerHTML = `
    <div class="message-content">
      <i class="fas fa-robot message-icon"></i>
      <div class="message-text">
        <div class="answer-content">
          ${escapeHtml(data.answer)}
        </div>
        ${sourcesHtml}
        <div class="confidence-indicator">
          ${confidenceIcon}
          <span class="confidence-text">${getConfidenceText(
            data.confidence
          )}</span>
        </div>
      </div>
    </div>
  `;

  container.appendChild(messageDiv);
  messageDiv.scrollIntoView({ behavior: "smooth", block: "end" });
}

function getConfidenceIcon(confidence) {
  const icons = {
    high: '<i class="fas fa-check-circle confidence-high"></i>',
    medium: '<i class="fas fa-info-circle confidence-medium"></i>',
    low: '<i class="fas fa-exclamation-triangle confidence-low"></i>',
    honest: '<i class="fas fa-hand-paper confidence-honest"></i>',
    error: '<i class="fas fa-times-circle confidence-error"></i>',
  };
  return icons[confidence] || icons.medium;
}

function getConfidenceText(confidence) {
  const texts = {
    high: "Hohe Relevanz",
    medium: "Mittlere Relevanz",
    low: "Niedrige Relevanz",
    honest: "Keine passenden Dokumente",
    error: "Technischer Fehler",
  };
  return texts[confidence] || "Unbekannt";
}

function showStatus(text) {
  const statusBar = document.getElementById("statusBar");
  const statusText = document.getElementById("statusText");

  statusText.textContent = text;
  statusBar.classList.remove("hidden");
}

function hideStatus() {
  document.getElementById("statusBar").classList.add("hidden");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// =============================
// Theme & UI
// =============================
function loadTheme() {
  const theme = localStorage.getItem("theme") || "dark";
  const body = document.body;
  const themeIcon = document.querySelector(".toggle-theme i");

  body.classList.toggle("light", theme === "light");
  if (themeIcon) {
    themeIcon.className = theme === "light" ? "fas fa-sun" : "fas fa-moon";
  }
}

function toggleTheme() {
  const body = document.body;
  const themeIcon = document.querySelector(".toggle-theme i");
  const isLight = body.classList.toggle("light");

  localStorage.setItem("theme", isLight ? "light" : "dark");
  if (themeIcon) {
    themeIcon.className = isLight ? "fas fa-sun" : "fas fa-moon";
  }
}

function showInfo() {
  document.getElementById("infoModal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("infoModal").classList.add("hidden");
}

async function loadAvailableSources() {
  try {
    const response = await fetch(`${API_BASE}/sources`);
    const data = await response.json();

    const sourcesList = document.getElementById("sourcesList");
    if (data.sources && data.sources.length > 0) {
      sourcesList.innerHTML = data.sources
        .map(
          (source) => `<span class="source-tag">${escapeHtml(source)}</span>`
        )
        .join("");
    } else {
      sourcesList.textContent = "Keine Quellen verfügbar";
    }
  } catch (error) {
    const sourcesList = document.getElementById("sourcesList");
    if (sourcesList) {
      sourcesList.textContent = "Fehler beim Laden der Quellen";
    }
  }
}

// Modal schließen bei Klick außerhalb
window.onclick = function (event) {
  const modal = document.getElementById("infoModal");
  if (event.target === modal) {
    closeModal();
  }
};
