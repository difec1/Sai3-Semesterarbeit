# 🧠 Gesetzes-Chatbot (RAG-System)

Dieses Projekt ist ein **Retrieval-Augmented Generation (RAG)**-System, das auf lokal gespeicherten Gesetzestexten basiert.
Es kombiniert **Vektorsuche (ChromaDB)**, **lokale Embeddings (Ollama)** und **Antwortgenerierung via Together.ai (Mixtral-Modell)**.
Über das mitgelieferte Frontend kann der Nutzer Fragen zu den enthaltenen PDFs stellen.

---

## 🔧 Voraussetzungen

### 📦 Software

- Python 3.10 oder 3.11
- Ollama (lokaler LLM/Embedding-Server)
- ChromaDB (Vektor-Datenbank, lokal)
- Together.ai API-Key (kostenlos)

### 📁 Verzeichnisstruktur (Auszug)

```
├── data/
│   ├── input/               → Originale PDFs
│   ├── text/                → Extrahierter Text
│   ├── chunks/              → Textblöcke (Chunks)
│   └── embeddings.json      → Generierte Vektor-Daten
├── scripts/                 → Alle Python-Skripte
├── Frontend/                → HTML/CSS/JS-Frontend
├── .env                     → API-Key (nicht committen!)
```

---

## 🚀 Schritt-für-Schritt Inbetriebnahme (lokal)

### 1. Repository klonen

```bash
git clone https://github.com/dein-nutzername/dein-repository.git
cd dein-repository
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # macOS/Linux
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. `.env`-Datei erstellen

```env
# Datei: .env
TOGETHER_API_KEY=sk-...dein-key...
```

> ❗ Die Datei `.env` ist **nicht im Repository enthalten** (siehe `.gitignore`).

---

## 🔁 Daten vorbereiten

### 5. PDFs in den Ordner `data/input/` verschieben

Dann:

```bash
python scripts/extract_text.py
python scripts/chunk_text.py
python scripts/create_embeddings_json.py
```

---

## 🧲 Embeddings in Chroma laden

### 6. Starte Chroma (in neuem Terminal):

```bash
uvicorn chromadb.app:app --host 127.0.0.1 --port 8000
```

Dann in deinem alten Terminal:

```bash
python scripts/import_embeddings_to_chroma_server.py
```

---

## 🧠 Ollama starten (für Embeddings)

```bash
ollama run nomic-embed-text
```

---

## 🌐 Backend starten

```bash
python scripts/app.py
```

---

## 💬 Frontend starten

1. Öffne `Frontend/index.html` in VS Code
2. Rechtsklick → **"Open with Live Server"**
3. Gib im Browser eine Frage ein (z. B. _„Was steht im Arbeitsgesetz über Ruhezeiten?“_)

---

## ✅ Beispielhafte Fragen

- „Welche Ruhezeiten gelten bei Nachtarbeit?“
- „Was regelt das Datenschutzgesetz im Arbeitsverhältnis?“
- „Wie ist ein Werkvertrag im OR definiert?“

---

## 🛡 Sicherheit

- API-Key liegt **nur in `.env`** und ist im `.gitignore` geschützt
- Für Deployment wird empfohlen, den Key über Umgebungsvariablen zu setzen

---

## 🧪 Weitere Skripte

| Script                                  | Beschreibung                          |
| --------------------------------------- | ------------------------------------- |
| `extract_text.py`                       | Extrahiert Text aus PDFs              |
| `chunk_text.py`                         | Teilt Text in überlappende Chunks     |
| `create_embeddings_json.py`             | Erstellt Embeddings via Ollama        |
| `import_embeddings_to_chroma_server.py` | Importiert Embeddings in ChromaDB     |
| `app.py`                                | Flask-API zur Beantwortung von Fragen |

---
