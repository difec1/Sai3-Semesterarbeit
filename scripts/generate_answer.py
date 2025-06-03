import os
import requests
import chromadb
from dotenv import load_dotenv


load_dotenv()


# === Together.ai Setup ===
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MIXTRAL_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
assert TOGETHER_API_KEY, "Bitte TOGETHER_API_KEY als Umgebungsvariable setzen."

# === Frage abfragen ===
frage = input("Was möchtest du wissen?\n> ").strip()
if not frage:
    print("Keine Frage eingegeben.")
    exit()

# === Embedding mit nomic-embed-text via Ollama ===
print("Erzeuge Embedding für die Frage...")
embed_response = requests.post("http://localhost:11434/api/embeddings", json={
    "model": "nomic-embed-text",
    "prompt": frage
})
if embed_response.status_code != 200:
    print("Fehler beim Embedding:", embed_response.text)
    exit()

frage_embedding = embed_response.json()["embedding"]

# === ChromaDB: relevante Chunks abrufen ===
print("📚 Suche relevante Chunks in Chroma...")
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("gesetzestexte")
result = collection.query(
    query_embeddings=[frage_embedding],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

top_docs = result["documents"][0]

# === Welche Dokumente & Abschnitte wurden verwendet? ===
print("\n---Verwendete Dokumente / Quellen ---")
for i, meta in enumerate(result["metadatas"][0]):
    quelle = meta.get("quelle", "Unbekannt")
    chunk_id = meta.get("chunk_id", "N/A")
    print(f"{i+1}. {quelle} – Chunk {chunk_id}")

kontext = "\n\n".join(top_docs)


# === Prompt für Mixtral bauen ===
prompt = f"""Beantworte die folgende Frage ausschließlich basierend auf dem gegebenen Kontext.

Frage: {frage}

Kontext:
{kontext}

Antwort:"""

# === Anfrage an Mixtral senden ===
print("Anfrage wird an Together.ai gesendet...")
response = requests.post(
    "https://api.together.xyz/v1/completions",
    headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
    json={
        "model": MIXTRAL_MODEL,
        "prompt": prompt,
        "max_tokens": 1024,
        "temperature": 0.1
    }
)

# === Fehlerbehandlung & Parsing ===
if response.status_code != 200:
    print("Fehler bei LLM-Request:", response.status_code)
    print(response.text)
    exit()

response_json = response.json()

if "choices" not in response_json:
    print("Unerwartete Antwortstruktur:")
    print(response_json)
    exit()

antwort = response_json["choices"][0]["text"]

# === Ausgabe ===
print("\n--- Antwort ---")
print(antwort.strip())
