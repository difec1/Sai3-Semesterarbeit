import chromadb
import requests

# === Frage, die beantwortet werden soll ===
frage = "Welche Ruhezeiten gelten laut Arbeitsgesetz für Nachtarbeit?"

# === Ollama: Embedding für die Frage erzeugen ===
response = requests.post("http://localhost:11434/api/embeddings", json={
    "model": "nomic-embed-text",
    "prompt": frage
})
frage_embedding = response.json()["embedding"]

# === Mit Chroma-Server verbinden ===
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("gesetzestexte")

# === Ähnlichste Chunks abfragen ===
result = collection.query(
    query_embeddings=[frage_embedding],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

# === Ergebnisse anzeigen ===
for i, (doc, meta, dist) in enumerate(zip(result["documents"][0], result["metadatas"][0], result["distances"][0])):
    print(f"\n🔹 Ergebnis {i+1} (Distanz: {dist:.4f})")
    print(f"Quelle: {meta['quelle']}  |  Chunk-ID: {meta['chunk_id']}")
    print(f"Text:\n{doc[:500]}...")  # nur ersten 500 Zeichen anzeigen
