# ========================
# Flask-Anwendung (Backend-API)
# ========================
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import numpy as np

# OPTIONAL: Später durch Embedding-Modell ersetzen
from sklearn.metrics.pairwise import cosine_similarity

# ========================
# Anwendung starten
# ========================
app = Flask(__name__)
CORS(app)  # Erlaubt Zugriff von deinem Frontend (Cross-Origin)

# ========================
# Dummy-Daten (simulierte Embeddings & Texte)
# ========================
# In der echten Version wird hier z. B. 'data/embeddings.json' geladen
documents = [
    {
        "text": "Gemäß Artikel 5 der Bundesverfassung ist die Rechtsstaatlichkeit ein zentrales Prinzip.",
        "embedding": [0.1, 0.3, 0.5, 0.2]
    },
    {
        "text": "Das Datenschutzgesetz schützt die Persönlichkeit und die Grundrechte bei der Bearbeitung von Personendaten.",
        "embedding": [0.4, 0.2, 0.6, 0.1]
    },
    {
        "text": "Das Obligationenrecht regelt allgemeine Vertragsbestimmungen und besondere Vertragstypen.",
        "embedding": [0.6, 0.1, 0.3, 0.2]
    }
]

# ========================
# Hilfsfunktion: Dummy-Embedding
# ========================
def embed_question_dummy(question):
    # Platzhalter für OpenAI oder SentenceTransformer
    # Hier: einfach Länge & Vokalanzahl als Vektor (nur für Beispiel)
    length = len(question)
    vowels = sum(1 for c in question if c in "aeiouäöü")
    return np.array([length % 10, vowels % 5, length % 7, vowels % 3])


# ========================
# Route: POST /answer
# ========================
@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"answer": "Keine Frage erhalten."}), 400

    # === Embedding erzeugen ===
    question_vec = embed_question_dummy(question).reshape(1, -1)

    # === Ähnlichsten Textabschnitt suchen ===
    best_match = None
    highest_sim = -1

    for doc in documents:
        doc_vec = np.array(doc["embedding"]).reshape(1, -1)
        sim = cosine_similarity(question_vec, doc_vec)[0][0]

        if sim > highest_sim:
            highest_sim = sim
            best_match = doc["text"]

    # === Antwort zusammenbauen ===
    if best_match:
        antwort = f"Ich habe folgendes gefunden:\n\n„{best_match}“"
    else:
        antwort = "Ich konnte leider keinen passenden Gesetzestext finden."

    return jsonify({"answer": antwort})


# ========================
# Startpunkt
# ========================
if __name__ == "__main__":
    app.run(debug=True)
