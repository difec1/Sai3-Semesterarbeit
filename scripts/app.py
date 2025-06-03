from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

# Flask App starten
app = Flask(__name__)
CORS(app)

# ChromaDB-Verbindung
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("gesetzestexte")

# API-Key von Together.ai
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MIXTRAL_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"

# Ollama-Embedding-Funktion
def get_embedding(text):
    response = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    response.raise_for_status()
    return response.json()["embedding"]

# POST /answer
@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    frage = data.get("question", "")

    if not frage:
        return jsonify({"answer": "Keine Frage erhalten."}), 400

    try:
        # 1. Embedding erzeugen
        frage_embedding = get_embedding(frage)

        # 2. Relevante Chunks aus Chroma holen
        result = collection.query(
            query_embeddings=[frage_embedding],
            n_results=5,
            include=["documents", "metadatas"]
        )

        top_docs = result["documents"][0]
        kontext = "\n\n".join(top_docs)

        # 3. Prompt zusammenbauen
        prompt = f"""Beantworte die folgende Frage ausschließlich basierend auf dem gegebenen Kontext.

Frage: {frage}

Kontext:
{kontext}

Antwort:"""

        # 4. Anfrage an Together.ai
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

        response.raise_for_status()
        response_json = response.json()
        antwort = response_json["choices"][0]["text"]

        return jsonify({"answer": antwort.strip()})

    except Exception as e:
        print("❌ Fehler:", e)
        return jsonify({"answer": "Fehler bei der Verarbeitung deiner Frage."}), 500

# Start
if __name__ == "__main__":
    app.run(debug=True)
