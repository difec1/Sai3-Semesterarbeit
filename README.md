# 🧠 RAG-Bot – Schweizer Gesetzestexte einfach erklärt

Ein intelligenter Chatbot auf Basis von Retrieval-Augmented Generation (RAG), der Fragen zu Schweizer Gesetzen beantwortet. Der Bot durchsucht vektorbasierte Embeddings von Gesetzestexten (wie ZGB, OR, Arbeitsgesetz etc.) und liefert präzise Antworten mit Quellenangabe.

---

## 🚀 Funktionen

- Nutzt ChromaDB für schnelle semantische Suche
- Arbeitet mit lokalem Sprachmodell über Ollama
- Beantwortet Fragen auf natürlicher Sprache
- Zeigt verwendete Gesetzesabschnitte als Quellen an
- Vertrauensindikator für jede Antwort
- Lokale Ausführung – keine externen APIs erforderlich

---

## 📦 Projektstruktur

```
├── app.py                  # Hauptserver mit Flask
├── data/                   # Gesetzestexte (PDF)
├── Frontend/               # Webinterface (HTML, JS, CSS)
├── scripts/                # .env und Hilfsskripte
├── process_pdfs.py         # PDF-Verarbeitung
├── import_to_chroma.py     # Embedding-Import in ChromaDB
├── start_docker.sh         # Automatischer Start (alternativ zu docker-compose)
├── docker-compose.yml      # Container-Orchestrierung
├── Dockerfile              # Build-Anweisungen
├── requirements.txt        # Python-Abhängigkeiten
```

---

## 🛠️ Voraussetzungen

- **Docker** und **Docker Compose** installiert  
  (Download: [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop))
- Ein GitHub-Konto zum Klonen des Repositories

---

## 🧑‍💻 Schritt-für-Schritt Anleitung zur Inbetriebnahme

### 1. Projekt klonen

```bash
git clone https://github.com/DEIN_NUTZERNAME/Sai3-Semesterarbeit.git
cd rag-gesetzesbot
```

### 2. Docker-Login ausführen

```bash
docker login
```

> Melde dich mit deinem Docker Hub-Konto an. Wenn du noch keines hast, kannst du es kostenlos erstellen unter: [https://hub.docker.com/](https://hub.docker.com/)

### 3. Container starten und Build ausführen

```bash
docker-compose up --build
```

> Der Chatbot wird auf [http://localhost:5000](http://localhost:5000) verfügbar sein.

---

### 4. System-Status prüfen und Ollama konfigurieren

```bash
# Health-Check ausführen
curl http://localhost:5000/health
```

Falls die Antwort `"ollama": "disconnected"` zeigt, muss das Sprachmodell installiert werden:

```bash
# Llama 3.2 Model installieren (einmalig erforderlich)
docker exec -it ollama ollama pull llama3.2:3b

# Installation verifizieren
docker exec -it ollama ollama list
```

Nach erfolgreicher Installation sollte der Health-Check `"ollama": "connected"` anzeigen.

---

## 🌐 Webinterface aufrufen

Öffne nach dem Start in deinem Browser den localhost:5000

---

## 📁 Eigene Gesetzestexte hinzufügen

Lege deine PDF-Dateien in den Ordner `data/` ab. Beim nächsten Start werden die Inhalte automatisch verarbeitet und eingebunden.

---

## 🧪 Beispiel-Fragen

- Was regelt das Arbeitsgesetz bei Nachtarbeit?
- Welche Ruhezeiten gelten laut Gesetz?
- Was steht im ZGB zur Handlungsfähigkeit?

---

## 📫 Kontakt / Mitwirkende

Gruppe F – SAI3 Modul FS25  
Aziri Arber, Beutler Florian, di Fede Carmelo, Vidakovic Milos

---

## ⚖️ Lizenz

Dieses Projekt dient rein zu Studienzwecken im Modul SAI3. Keine kommerzielle Nutzung.
