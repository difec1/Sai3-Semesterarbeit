import os
import uuid
import json
import requests

# === Konfiguration ===
CHUNK_DIR = "../data/chunks"
OUTPUT_FILE = "../data/embeddings.json"
MODEL = "nomic-embed-text"

all_embeddings = []

# === Embedding-Funktion via Ollama ===
def get_embedding(text):
    response = requests.post("http://localhost:11434/api/embeddings", json={
        "model": MODEL,
        "prompt": text
    })
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        print("❌ Fehler bei Embedding:", response.text)
        return None

# === Alle Chunks verarbeiten ===
for filename in sorted(os.listdir(CHUNK_DIR)):
    if not filename.endswith(".txt"):
        continue

    filepath = os.path.join(CHUNK_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    embedding = get_embedding(text)
    if not embedding:
        continue

    quelle, chunk_id = filename.replace(".txt", "").split("_chunk_")

    all_embeddings.append({
        "id": str(uuid.uuid4()),
        "text": text,
        "quelle": quelle,
        "chunk_id": chunk_id,
        "filename": filename,
        "embedding": embedding
    })

    print(f"✅ Gespeichert: {filename}")

# === JSON-Datei schreiben ===
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_embeddings, f, ensure_ascii=False, indent=2)

print(f"\n🎉 Alle Embeddings gespeichert in {OUTPUT_FILE}")
