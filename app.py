# app.py - FIXED VERSION WITH PROPER FLASK SERVER STARTUP

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Global shutdown flag
shutdown_flag = threading.Event()

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
    
    # Zuerst HTTP Client (für Docker)
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        logger.info("✅ ChromaDB HTTP-Verbindung OK")
        return client
    except Exception as e:
        logger.warning(f"⚠️ HTTP ChromaDB fehlgeschlagen: {e}")
    
    # Fallback: Persistent Client
    try:
        client = chromadb.PersistentClient(path="./chroma_data")
        logger.info("✅ ChromaDB lokale Verbindung OK")
        return client
    except Exception as e:
        logger.error(f"❌ Alle ChromaDB-Verbindungen fehlgeschlagen: {e}")
        return None

def _test_ollama_connection():
    """Schneller Ollama-Test"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": "Antworte nur: OK",
                "stream": False,
                "options": {"num_predict": 5}
            },
            timeout=15
        )
        return response.status_code == 200
    except:
        return False

def _generate_intelligent_ollama_answer(question, docs, metas):
    """Debug-Version mit detailliertem Logging"""
    
    logger.info("🧠 Generiere universelle Rechts-Antwort...")
    
    # Kontext-Aufbereitung (wie vorher)
    relevant_content = []
    for doc in docs[:4]:
        cleaned_doc = doc.replace("Art.", "Artikel").replace("Abs.", "Absatz")
        lines = cleaned_doc.split('\n')
        for line in lines:
            line = line.strip()
            if (len(line) > 25 and 
                any(keyword in line.lower() for keyword in 
                    ['darf', 'muss', 'kann', 'wird', 'haben', 'gelten', 'ist', 'sind',
                     'berechtigt', 'verpflichtet', 'bestimmt', 'regelt', 'vorgesehen']) and
                not line.startswith(('---', 'Seite', 'BBl', 'AS', 'Fassung', 'Eingefügt'))):
                relevant_content.append(line)
    
    context = " ".join(relevant_content[:4])[:800]  # Reduzierter Kontext
    sources = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas))
    
    # VEREINFACHTER Prompt
    prompt = f"""Du bist ein Rechtsexperte für die Schweiz. Beantworte die Frage kurz und verständlich auf Deutsch.

Frage: {question}

Rechtlicher Kontext: {context}

Antwort (2-3 Sätze):"""

    try:
        logger.info("📡 Sende vereinfachte Anfrage an Ollama...")
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,        # Weniger kreativ
                    "top_p": 0.8,
                    "num_predict": 150,        # REDUZIERT für Stabilität
                    "num_ctx": 2048,          # Kleinerer Kontext
                    "repeat_penalty": 1.1,
                    "stop": ["\n\nFrage:", "Kontext:"]
                }
            },
            timeout=60  # Kürzerer Timeout
        )
        
        logger.info(f"📡 Ollama Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "").strip()
            
            logger.info(f"📄 Ollama Raw Answer Length: {len(answer)}")
            logger.info(f"📄 Ollama Raw Answer Preview: '{answer[:100]}...'")
            
            if answer and len(answer) > 10:  # Niedrigere Schwelle
                logger.info("✅ Ollama-Antwort akzeptiert!")
                
                # Minimale Bereinigung
                lines = answer.split('\n')
                first_paragraph = lines[0].strip() if lines else answer
                
                # Nur offensichtlich schlechte Antworten ablehnen
                if (len(first_paragraph) > 20 and 
                    not first_paragraph.startswith(('Frage:', 'Kontext:', 'Du bist'))):
                    
                    logger.info("✅ Antwort-Qualität OK - verwende Ollama")
                    return f"{first_paragraph}\n\nQuellen: {sources}"
                else:
                    logger.warning("⚠️ Antwort-Qualität schlecht - verwende Fallback")
                    logger.info(f"🔍 Abgelehnte Antwort: '{first_paragraph}'")
                    return _generate_universal_fallback(question, docs, metas)
            else:
                logger.warning(f"⚠️ Ollama-Antwort zu kurz: '{answer}'")
                return _generate_universal_fallback(question, docs, metas)
        else:
            logger.error(f"❌ Ollama API Fehler: {response.status_code} - {response.text}")
            return _generate_universal_fallback(question, docs, metas)
            
    except requests.exceptions.Timeout:
        logger.error("⏰ Ollama Timeout nach 60s")
        return _generate_universal_fallback(question, docs, metas)
    except Exception as e:
        logger.error(f"❌ Ollama Fehler: {e}")
        return _generate_universal_fallback(question, docs, metas)

def _generate_universal_fallback(question, docs, metas):
    """Verbesserter universeller Fallback"""
    
    logger.info("🔄 Generiere universellen Fallback...")
    
    question_lower = question.lower()
    sources_text = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas))
    
    # Bessere Informationsextraktion - keine technischen Referenzen
    clean_content = []
    for doc in docs[:2]:
        lines = doc.split('\n')
        for line in lines:
            line = line.strip()
            # Nur inhaltliche Zeilen, keine Metadaten
            if (len(line) > 40 and 
                any(keyword in line.lower() for keyword in 
                    ['arbeitnehmer', 'arbeitgeber', 'arbeitszeit', 'ruhezeit', 'nachtarbeit',
                     'stunden', 'tage', 'wochen', 'darf', 'muss', 'kann', 'berechtigt']) and
                not any(unwanted in line for unwanted in 
                       ['BBl', 'AS', 'März 1998', 'Aug. 2000', 'Fassung gemäss', 
                        'in Kraft seit', '---', 'Seite', 'Ziff.', '822.11'])):
                clean_content.append(line)
                if len(clean_content) >= 2:
                    break
    
    # Spezifische Antworten je nach Fragetyp
    if any(keyword in question_lower for keyword in ["ruhezeit", "ruhe", "pause"]):
        if any(keyword in question_lower for keyword in ["nachtarbeit", "nacht"]):
            answer = "Bei Nachtarbeit in der Schweiz gelten besondere Ruhezeiten. "
            answer += "Zwischen zwei Arbeitsperioden müssen mindestens 11 zusammenhängende Stunden Ruhe liegen. "
            answer += "Zusätzlich haben Nachtarbeiter Anspruch auf verlängerte Erholungszeiten."
        else:
            answer = "Die tägliche Ruhezeit beträgt in der Schweiz mindestens 11 zusammenhängende Stunden. "
            answer += "Diese Zeit darf nur in Ausnahmefällen verkürzt werden."
    
    elif any(keyword in question_lower for keyword in ["nachtarbeit", "nachts", "nacht"]):
        if any(keyword in question_lower for keyword in ["stunden", "lange", "dauer"]):
            answer = "Nachtarbeit in der Schweiz darf grundsätzlich 9 Stunden täglich nicht überschreiten. "
            answer += "Bei vorübergehender Nachtarbeit sind unter bestimmten Bedingungen bis zu 10 Stunden möglich."
        else:
            answer = "Nachtarbeit ist in der Schweiz grundsätzlich beschränkt und erfordert die Zustimmung des Arbeitnehmers. "
            answer += "Es gelten besondere Schutzbestimmungen und Zuschläge."
    
    elif clean_content:
        # Verwende den besten verfügbaren Content
        best_info = clean_content[0][:200]
        answer = f"Gemäß dem Schweizer Arbeitsrecht: {best_info} "
        answer += "Diese Bestimmungen sind verbindlich einzuhalten."
    
    else:
        answer = "Zu deiner Frage finden sich spezifische Regelungen im Schweizer Arbeitsrecht. "
        answer += "Für eine detaillierte Auskunft empfehle ich dir, die entsprechenden Gesetzesartikel zu konsultieren."
    
    answer += f"\n\nQuellen: {sources_text}"
    return answer

def _check_question_relevance(question, best_distance):
    """Prüft ob die Frage überhaupt legal-relevant ist"""
    question_lower = question.lower()
    
    # Legal-relevante Keywords
    legal_keywords = [
        'arbeitszeit', 'arbeitsrecht', 'gesetz', 'recht', 'vertrag', 'arbeit', 
        'lohn', 'gehalt', 'urlaub', 'kündigung', 'pause', 'ruhezeit',
        'nachtarbeit', 'überstunden', 'schicht', 'arbeitgeber', 'arbeitnehmer',
        'legal', 'erlaubt', 'verboten', 'bestimmung', 'regelung'
    ]
    
    # Nicht-relevante Keywords  
    irrelevant_keywords = [
        'redbull', 'coca cola', 'pepsi', 'sport', 'auto', 'handy', 
        'computer', 'spiel', 'musik', 'film', 'essen', 'trinken'
    ]
    
    has_legal_keywords = any(keyword in question_lower for keyword in legal_keywords)
    has_irrelevant_keywords = any(keyword in question_lower for keyword in irrelevant_keywords)
    
    # Wenn eindeutig irrelevant oder Distanz zu hoch
    if has_irrelevant_keywords or (not has_legal_keywords and best_distance > 1.5):
        return False
    
    return True

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
        # 1. Embedding für Frage erstellen
        question_embedding = get_embedding(question)
        if not question_embedding:
            return jsonify({
                "answer": "Entschuldigung, es gab ein technisches Problem. Bitte versuchen Sie es erneut.", 
                "sources": [], 
                "confidence": "error"
            })
        
        # 2. ChromaDB-Verbindung
        client = get_chromadb_client()
        if not client:
            return jsonify({
                "answer": "Die Datenbank ist momentan nicht verfügbar. Bitte versuchen Sie es später erneut.",
                "sources": [],
                "confidence": "error"
            })
        
        # 3. Collection prüfen
        try:
            collection = client.get_collection("gesetzestexte")
            doc_count = collection.count()
            logger.info(f"📊 Collection hat {doc_count} Dokumente")
            
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
        
        # 4. Similarity Search
        try:
            result = collection.query(
                query_embeddings=[question_embedding],
                n_results=5,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"🔍 Suche ergab {len(result['documents'][0])} Ergebnisse")
            
            if result["distances"][0]:
                distances = result["distances"][0]
                logger.info(f"📏 Beste Distanz: {min(distances):.4f}")
            
        except Exception as e:
            logger.error(f"❌ Suche fehlgeschlagen: {e}")
            return jsonify({
                "answer": "Suchfehler. Bitte versuchen Sie es erneut.",
                "sources": [],
                "confidence": "error"
            })
        
        # 5. Relevanz prüfen
        if not result["documents"][0]:
            return jsonify({
                "answer": "Zu Ihrer Frage wurden keine relevanten Dokumente gefunden.",
                "sources": [],
                "confidence": "honest"
            })
        
        best_distance = min(result["distances"][0])
        
        # Relevanz-Check für die Frage
        if not _check_question_relevance(question, best_distance):
            return jsonify({
                "answer": "Entschuldigung, ich kann nur Fragen zum deutschen Arbeitsrecht und verwandten Gesetzen beantworten. Könnten Sie eine entsprechende Frage stellen?",
                "sources": [],
                "confidence": "honest"
            })
        
        # 6. Relevante Dokumente filtern
        relevant_docs = []
        relevant_metas = []
        relevant_distances = []
        
        # Strengere Filterung für bessere Qualität
        for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            if dist < 1.8:  # Strenger Schwellwert
                relevant_docs.append(doc)
                relevant_metas.append(meta)
                relevant_distances.append(dist)
        
        if not relevant_docs:
            return jsonify({
                "answer": f"Zu Ihrer spezifischen Frage konnte ich keine ausreichend relevanten Informationen finden. Versuchen Sie eine allgemeinere Formulierung oder eine andere Frage zum Arbeitsrecht.",
                "sources": [],
                "confidence": "honest"
            })
        
        logger.info(f"✅ {len(relevant_docs)} relevante Dokumente (beste Distanz: {min(relevant_distances):.3f})")
        
        # 7. Intelligente Antwort generieren
        # Erst Ollama versuchen, dann Fallback
        ollama_available = _test_ollama_connection()
        
        if ollama_available:
            logger.info("🦙 Verwende Ollama für intelligente Antwort")
            answer_text = _generate_intelligent_ollama_answer(question, relevant_docs, relevant_metas)
        else:
            logger.info("🔄 Ollama nicht verfügbar - verwende verbesserten Fallback")
            answer_text = _generate_universal_fallback(question, relevant_docs, relevant_metas)
        
        # 8. Quellen und Confidence
        sources = []
        for meta, distance in zip(relevant_metas[:3], relevant_distances[:3]):
            sources.append({
                "quelle": meta.get("quelle", "Unbekannt"),
                "chunk_id": meta.get("chunk_id", "N/A"),
                "relevanz": f"{max(0, (1.8-distance)/1.8)*100:.1f}%"
            })
        
        # Confidence basierend auf Distanz und Ollama-Verfügbarkeit
        if ollama_available and best_distance < 1.0:
            confidence = "high"
        elif best_distance < 1.2:
            confidence = "medium"
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
            "ollama": "connected" if ollama_status else "disconnected"
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
    logger.info("🚀 Docker Gesetzestext-Chatbot startet...")
    
    # Startup-Checks
    if embedding_model:
        logger.info("✅ HuggingFace Model: Geladen")
    else:
        logger.error("❌ HuggingFace Model: Fehler")
    
    # ChromaDB Connection Test
    client = get_chromadb_client()
    if client:
        try:
            collection = client.get_collection("gesetzestexte")
            doc_count = collection.count()
            logger.info(f"📊 ChromaDB bereit: {doc_count} Dokumente")
        except:
            logger.warning("⚠️ ChromaDB Collection nicht gefunden - wird bei erster Nutzung erstellt")
    
    logger.info("🌐 Server startet auf http://0.0.0.0:5000")
    
    # CRITICAL FIX: Tatsächlich den Flask-Server starten!
    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,           # Kein Debug in Production
            threaded=True,         # Multi-threading aktivieren
            use_reloader=False     # Reloader deaktivieren in Docker
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server gestoppt durch Benutzer")
    except Exception as e:
        logger.error(f"❌ Server-Fehler: {e}")
        sys.exit(1)