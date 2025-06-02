// =============================
// Initialisierung nach dem Laden
// =============================
document.addEventListener("DOMContentLoaded", () => {
  // Theme anwenden
  loadTheme();

  // Chat-Ansicht sicher verstecken (z. B. nach Seitenaktualisierung)
  document.getElementById("startScreen").classList.remove("hidden");
  document.getElementById("chatScreen").classList.add("hidden");

  // Enter im Startscreen: Chat starten
  const startInput = document.getElementById("initialInput");
  startInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      startChat();
    }
  });

  // Enter im Chat: Nachricht senden
  const chatInput = document.getElementById("userInput");
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
});

// =====================================
// Chat starten & erste Nachricht einfügen
// =====================================
function startChat() {
  const startText = document.getElementById("initialInput").value.trim();
  if (!startText) return;

  // Startscreen animiert ausblenden
  document.getElementById("startScreen").classList.add("fade-out");

  // Nach Animation: Startscreen ausblenden, Chat einblenden
  setTimeout(() => {
    document.getElementById("startScreen").classList.add("hidden");
    document.getElementById("chatScreen").classList.remove("hidden");
    document.getElementById("chatScreen").classList.add("fade-in");

    // Erste Nachricht des Nutzers anzeigen
    addMessage("Du: " + startText, "user");

    // Eingabefeld leeren & Fokus setzen
    document.getElementById("initialInput").value = "";
    document.getElementById("userInput").focus();

    // Simulierte Bot-Antwort
    setTimeout(() => {
      const replies = [
        "Das klingt interessant!",
        "Danke für deine Nachricht.",
        "Lass uns das anschauen.",
        "Erzähl mir mehr darüber.",
      ];
      const reply = replies[Math.floor(Math.random() * replies.length)];
      addMessage("Bot: " + reply, "bot");
    }, 1000);
  }, 400);
}

// ==========================
// Nachricht senden im Chat
// ==========================
function sendMessage() {
  const input = document.getElementById("userInput");
  const msg = input.value.trim();
  if (!msg) return;

  addMessage("Du: " + msg, "user");
  input.value = "";
  input.focus();

  // Simulierte Bot-Antwort
  setTimeout(() => {
    const replies = [
      "Interessanter Punkt!",
      "Das hängt vom Kontext ab.",
      "Möchtest du mehr dazu wissen?",
      "Ich helfe dir gerne weiter.",
    ];
    const reply = replies[Math.floor(Math.random() * replies.length)];
    addMessage("Bot: " + reply, "bot");
  }, 1000);
}

// ==================================
// Nachrichtenelement in Chat einfügen
// ==================================
function addMessage(text, sender) {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}`;
  msgDiv.textContent = text;
  container.appendChild(msgDiv);
  msgDiv.scrollIntoView({ behavior: "smooth" });
}

// =====================
// Dark / Light Mode
// =====================
function loadTheme() {
  const theme = localStorage.getItem("theme") || "dark";
  document.body.classList.toggle("light", theme === "light");
}

function toggleTheme() {
  const isLight = document.body.classList.toggle("light");
  localStorage.setItem("theme", isLight ? "light" : "dark");
}
