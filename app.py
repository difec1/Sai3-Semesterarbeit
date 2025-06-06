# app.py - WORKING UNIVERSAL LEGAL SYSTEM - FIXED OLLAMA CONNECTION

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import chromadb
import os
import logging
import sys
import signal
import threading
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import requests
import json
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Global shutdown flag
shutdown_flag = threading.Event()

# =============================
# OLLAMA HOST CONFIGURATION - FIXED!
# =============================
# Lese Ollama Host aus Umgebung oder verwende Default
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost:11434")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}"

logger.info(f"🦙 Ollama configured for: {OLLAMA_BASE_URL}")

# HuggingFace Model laden
logger.info("🤗 Lade HuggingFace Embedding Model...")
try:
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    logger.info("✅ HuggingFace Model geladen!")
except Exception as e:
    logger.error(f"❌ Fehler beim Laden des HuggingFace Models: {e}")
    embedding_model = None

def get_embedding(text):
    """Embedding mit HuggingFace all-MiniLM-L6-v2"""
    try:
        if embedding_model is None:
            logger.error("❌ HuggingFace Model nicht verfügbar!")
            return None
        
        embedding = embedding_model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()
        
    except Exception as e:
        logger.error(f"❌ HuggingFace Embedding-Fehler: {e}")
        return None

def get_chromadb_client():
    """ChromaDB-Client mit Docker-optimierter Fallback-Strategie"""
    
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        logger.info("✅ ChromaDB HTTP-Verbindung OK")
        return client
    except Exception as e:
        logger.warning(f"⚠️ HTTP ChromaDB fehlgeschlagen: {e}")
    
    try:
        client = chromadb.PersistentClient(path="./chroma_data")
        logger.info("✅ ChromaDB lokale Verbindung OK")
        return client
    except Exception as e:
        logger.error(f"❌ Alle ChromaDB-Verbindungen fehlgeschlagen: {e}")
        return None

def _test_ollama_connection():
    """Schneller Ollama-Test - FIXED für Docker"""
    try:
        # Verwende die konfigurierte Ollama-URL
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": "Antworte nur: OK",
                "stream": False,
                "options": {"num_predict": 5}
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"🦙 Ollama nicht erreichbar: {e}")
        return False

def _detect_legal_area(question):
    """Einfache Rechtsbereicherkennung"""
    question_lower = question.lower()
    
    # Einfache Keywords
    if any(kw in question_lower for kw in ['arbeitszeit', 'arbeit', 'ruhezeit', 'pause', 'nacht', 'überstunden', 'urlaub', 'ferien']):
        return 'arbeitsrecht'
    elif any(kw in question_lower for kw in ['strafe', 'strafbar', 'mord', 'diebstahl', 'delikt', 'verbrechen']):
        return 'strafrecht'
    elif any(kw in question_lower for kw in ['vertrag', 'obligation', 'haftung', 'schadenersatz', 'eigentum']):
        return 'zivilrecht'
    elif any(kw in question_lower for kw in ['ehe', 'scheidung', 'familie', 'kind', 'unterhalt']):
        return 'familienrecht'
    else:
        return 'allgemein'

def _extract_relevant_content(docs, question):
    """BEWÄHRTE Content-Extraktion - einfach aber effektiv"""
    
    question_lower = question.lower()
    question_words = set(re.findall(r'\b\w{3,}\b', question_lower))
    
    # Rechtliche Signalwörter
    legal_signals = [
        'darf', 'muss', 'kann', 'soll', 'haben', 'sind', 'wird',
        'berechtigt', 'verpflichtet', 'verboten', 'erlaubt', 'zulässig',
        'bestimmt', 'regelt', 'gilt', 'mindestens', 'höchstens',
        'artikel', 'absatz', 'stunden', 'tage', 'wochen', 'monate'
    ]
    
    relevant_sentences = []
    
    for doc in docs[:3]:  # Top 3 Dokumente
        # Sanfte Bereinigung
        cleaned_doc = re.sub(r'BBl \d{4}.*?(?=\n|$)', '', doc)
        cleaned_doc = re.sub(r'AS \d{4}.*?(?=\n|$)', '', cleaned_doc)
        cleaned_doc = re.sub(r'---.*?---', '', cleaned_doc)
        cleaned_doc = re.sub(r'\s+', ' ', cleaned_doc).strip()
        
        sentences = re.split(r'[.!?]+', cleaned_doc)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            sentence_lower = sentence.lower()
            score = 0
            
            # Score berechnen
            for word in question_words:
                if word in sentence_lower:
                    score += 2
            
            for signal in legal_signals:
                if signal in sentence_lower:
                    score += 1
            
            # Zahlen und Artikel-Referenzen
            if re.search(r'\b\d+\b', sentence):
                score += 1
            
            if score >= 2:
                relevant_sentences.append((sentence, score))
    
    # Nach Score sortieren
    relevant_sentences.sort(key=lambda x: x[1], reverse=True)
    return [sent[0] for sent in relevant_sentences[:4]]

def _generate_ollama_answer(question, docs, metas, legal_area):
    """Einfache aber effektive Ollama-Antwort - FIXED für Docker"""
    
    logger.info(f"🧠 Generiere {legal_area}-Antwort mit Ollama...")
    
    relevant_sentences = _extract_relevant_content(docs, question)
    
    if not relevant_sentences:
        return _generate_fallback_answer(question, docs, metas, legal_area)
    
    # Kompakter Kontext
    context = ". ".join(relevant_sentences[:2])[:400]
    sources = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas[:3]))
    
    # Einfacher Prompt
    prompt = f"""Beantworte diese Rechtsfrage kurz und präzise basierend auf dem Schweizer Recht.

FRAGE: {question}

RECHTLICHE GRUNDLAGE: {context}

ANTWORT (1-2 präzise Sätze):"""

    try:
        # Verwende die konfigurierte Ollama-URL
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "num_predict": 100,
                    "num_ctx": 1000,
                    "repeat_penalty": 1.1,
                    "stop": ["\n\nFRAGE:", "RECHTLICHE GRUNDLAGE:"]
                }
            },
            timeout=45
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "").strip()
            
            # Einfache Bereinigung
            answer = re.sub(r'^(ANTWORT:?|Antwort:?)\s*', '', answer).strip()
            
            if len(answer) > 20:
                logger.info("✅ Ollama-Antwort erhalten!")
                return f"{answer}\n\nQuellen: {sources}"
        
        logger.warning("⚠️ Ollama-Antwort unvollständig, verwende Fallback")
        return _generate_fallback_answer(question, docs, metas, legal_area)
        
    except Exception as e:
        logger.error(f"❌ Ollama Fehler: {e}")
        return _generate_fallback_answer(question, docs, metas, legal_area)

def _generate_fallback_answer(question, docs, metas, legal_area):
    """Einfacher aber guter Fallback"""
    
    relevant_sentences = _extract_relevant_content(docs, question)
    sources_text = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas[:3]))
    
    if relevant_sentences:
        best_content = relevant_sentences[0]
        
        # Einfache Templates
        if legal_area == 'arbeitsrecht':
            answer = f"Das Schweizer Arbeitsrecht bestimmt: {best_content}"
        elif legal_area == 'strafrecht':
            answer = f"Nach dem Schweizer Strafgesetzbuch: {best_content}"
        elif legal_area == 'zivilrecht':
            answer = f"Das Schweizer Zivilrecht regelt: {best_content}"
        elif legal_area == 'familienrecht':
            answer = f"Das Schweizer Familienrecht bestimmt: {best_content}"
        else:
            answer = f"Gemäß dem Schweizer Recht: {best_content}"
        
        # Zusätzliche Info
        if len(relevant_sentences) > 1:
            answer += f" Zusätzlich gilt: {relevant_sentences[1][:80]}..."
    
    else:
        answer = f"Zu Ihrer Frage zum Schweizer {legal_area.replace('recht', 'recht')} finden sich spezifische Regelungen in den entsprechenden Gesetzen. Für eine detaillierte Auskunft empfehle ich die Konsultation der relevanten Gesetzesartikel."
    
    answer += f"\n\nQuellen: {sources_text}"
    return answer

@app.route("/")
def serve_frontend():
    return send_from_directory("frontend", "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("frontend", filename)

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    question = data.get("question", "")
    
    logger.info(f"📝 Neue Frage: {question}")
    
    if not question:
        return jsonify({"error": "Keine Frage erhalten."}), 400
    
    try:
        # 1. Rechtsbereich erkennen
        legal_area = _detect_legal_area(question)
        logger.info(f"🏛️ Rechtsbereich: {legal_area}")
        
        # 2. Embedding erstellen
        question_embedding = get_embedding(question)
        if not question_embedding:
            return jsonify({
                "answer": "Entschuldigung, es gab ein technisches Problem. Bitte versuchen Sie es erneut.", 
                "sources": [], 
                "confidence": "error"
            })
        
        # 3. ChromaDB-Verbindung
        client = get_chromadb_client()
        if not client:
            return jsonify({
                "answer": "Die Datenbank ist momentan nicht verfügbar. Bitte versuchen Sie es später erneut.",
                "sources": [],
                "confidence": "error"
            })
        
        # 4. Collection prüfen
        try:
            collection = client.get_collection("gesetzestexte")
            doc_count = collection.count()
            logger.info(f"📊 Collection: {doc_count} Dokumente")
            
            if doc_count == 0:
                return jsonify({
                    "answer": "Die Datenbank ist leer. Bitte wenden Sie sich an den Administrator.",
                    "sources": [],
                    "confidence": "error"
                })
                
        except Exception as e:
            logger.error(f"❌ Collection-Fehler: {e}")
            return jsonify({
                "answer": "Datenbankfehler. Bitte versuchen Sie es später erneut.",
                "sources": [],
                "confidence": "error"
            })
        
        # 5. Similarity Search
        try:
            result = collection.query(
                query_embeddings=[question_embedding],
                n_results=6,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"🔍 Suche: {len(result['documents'][0])} Ergebnisse")
            
            if result["distances"][0]:
                best_distance = min(result["distances"][0])
                logger.info(f"📏 Beste Distanz: {best_distance:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Suche fehlgeschlagen: {e}")
            return jsonify({
                "answer": "Suchfehler. Bitte versuchen Sie es erneut.",
                "sources": [],
                "confidence": "error"
            })
        
        # 6. Relevanz prüfen
        if not result["documents"][0]:
            return jsonify({
                "answer": "Zu Ihrer Frage wurden keine relevanten Dokumente gefunden.",
                "sources": [],
                "confidence": "honest"
            })
        
        best_distance = min(result["distances"][0])
        
        # Einfache Relevanz-Prüfung
        question_lower = question.lower()
        legal_keywords = ['recht', 'gesetz', 'legal', 'strafe', 'arbeit', 'vertrag', 'ehe', 'eigentum', 'haftung', 'erlaubt', 'verboten', 'darf', 'muss']
        has_legal_keywords = any(kw in question_lower for kw in legal_keywords)
        
        if not has_legal_keywords and best_distance > 1.8:
            return jsonify({
                "answer": "Entschuldigung, ich kann nur Fragen zum Schweizer Recht beantworten. Könnten Sie eine rechtliche Frage stellen?",
                "sources": [],
                "confidence": "honest"
            })
        
        # 7. Relevante Dokumente filtern
        relevant_docs = []
        relevant_metas = []
        relevant_distances = []
        
        threshold = 2.0
        if best_distance < 1.0:
            threshold = 2.2
        elif best_distance < 1.5:
            threshold = 2.0
        else:
            threshold = 1.8
        
        for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            if dist < threshold:
                relevant_docs.append(doc)
                relevant_metas.append(meta)
                relevant_distances.append(dist)
        
        if not relevant_docs:
            return jsonify({
                "answer": "Zu Ihrer spezifischen Frage konnte ich keine ausreichend relevanten Informationen finden. Versuchen Sie eine allgemeinere Formulierung.",
                "sources": [],
                "confidence": "honest"
            })
        
        logger.info(f"✅ {len(relevant_docs)} relevante Dokumente (Distanz: {min(relevant_distances):.3f})")
        
        # 8. Antwort generieren
        ollama_available = _test_ollama_connection()
        
        if ollama_available:
            logger.info("🦙 Verwende Ollama")
            answer_text = _generate_ollama_answer(question, relevant_docs, relevant_metas, legal_area)
        else:
            logger.info("🔄 Verwende Fallback")
            answer_text = _generate_fallback_answer(question, relevant_docs, relevant_metas, legal_area)
        
        # 9. Quellen und Confidence
        sources = []
        for meta, distance in zip(relevant_metas[:4], relevant_distances[:4]):
            relevance_score = max(0, (2.5-distance)/2.5)*100
            sources.append({
                "quelle": meta.get("quelle", "Unbekannt"),
                "chunk_id": meta.get("chunk_id", "N/A"),
                "relevanz": f"{relevance_score:.1f}%"
            })
        
        # Einfache Confidence-Berechnung
        if ollama_available and best_distance < 0.8:
            confidence = "high"
        elif ollama_available and best_distance < 1.2:
            confidence = "medium"
        elif best_distance < 1.0:
            confidence = "medium"
        elif best_distance < 1.6:
            confidence = "low"
        else:
            confidence = "low"
        
        return jsonify({
            "answer": answer_text,
            "sources": sources,
            "confidence": confidence
        })
        
    except Exception as e:
        logger.error(f"❌ Unerwarteter Fehler: {e}")
        return jsonify({
            "answer": "Es ist ein unerwarteter Fehler aufgetreten. Bitte versuchen Sie es erneut.", 
            "sources": [], 
            "confidence": "error"
        })

@app.route("/health")
def health_check():
    """Gesundheitscheck"""
    try:
        client = get_chromadb_client()
        if not client:
            return jsonify({
                "status": "unhealthy",
                "error": "ChromaDB nicht erreichbar"
            }), 500
        
        collection = client.get_collection("gesetzestexte")
        doc_count = collection.count()
        model_status = "loaded" if embedding_model is not None else "not_loaded"
        ollama_status = _test_ollama_connection()
        
        return jsonify({
            "status": "healthy",
            "chromadb": "connected",
            "documents": doc_count,
            "embedding_model": model_status,
            "ollama": "connected" if ollama_status else "disconnected",
            "ollama_host": OLLAMA_BASE_URL  # Debug info
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route("/sources")
def get_available_sources():
    """Verfügbare Quellen anzeigen"""
    try:
        client = get_chromadb_client()
        if not client:
            return jsonify({"sources": []})
        
        collection = client.get_collection("gesetzestexte")
        result = collection.get(include=["metadatas"])
        sources = set()
        for meta in result["metadatas"]:
            sources.add(meta.get("quelle", "Unbekannt"))
        
        return jsonify({"sources": sorted(list(sources))})
    except Exception as e:
        logger.error(f"Fehler beim Laden der Quellen: {e}")
        return jsonify({"sources": []})

def signal_handler(sig, frame):
    """Graceful shutdown"""
    logger.info("🛑 Shutting down gracefully...")
    shutdown_flag.set()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    logger.info("🚀 Working Universal Legal Chatbot startet...")
    
    if embedding_model:
        logger.info("✅ HuggingFace Model: Geladen")
    else:
        logger.error("❌ HuggingFace Model: Fehler")
    
    client = get_chromadb_client()
    if client:
        try:
            collection = client.get_collection("gesetzestexte")
            doc_count = collection.count()
            logger.info(f"📊 ChromaDB bereit: {doc_count} Dokumente")
        except:
            logger.warning("⚠️ ChromaDB Collection nicht gefunden")
    
    logger.info("🌐 Legal Server startet auf http://0.0.0.0:5000")
    
    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server gestoppt durch Benutzer")
    except Exception as e:
        logger.error(f"❌ Server-Fehler: {e}")
        sys.exit(1)