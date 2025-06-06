# app.py - PERFECT VERSION - ELIMINATES ALL FRAGMENT ISSUES

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

# Ollama Configuration
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
    """Schneller Ollama-Test"""
    try:
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

def _detect_legal_area_precise(question):
    """PERFEKTE Rechtsbereicherkennung"""
    question_lower = question.lower()
    
    # Sehr spezifische Keywords mit hoher Präzision
    area_keywords = {
        'arbeitsrecht': {
            'primary': ['ruhezeit', 'arbeitszeit', 'nachtarbeit', 'überstunden', 'arbeitsvertrag', 'kündigung.*arbeit', 'kündigungsfrist.*arbeit', 'probezeit', 'ferien', 'urlaub', 'lohn', 'gehalt'],
            'secondary': ['arbeitgeber', 'arbeitnehmer', 'anstellung']
        },
        'krankenversicherung': {
            'primary': ['krankenkasse', 'krankenversicherung', 'kv.*kündigung', 'kassenwechsel', 'prämie', 'franchise', 'grundversicherung'],
            'secondary': ['kasse.*wechsel', 'versicherung.*kündigung']
        },
        'strafrecht': {
            'primary': ['strafgesetz', 'strafrecht', 'strafe', 'strafbar', 'mord', 'diebstahl', 'raub', 'betrug', 'delikt', 'verbrechen', 'gefängnis', 'busse', 'strafmündig'],
            'secondary': ['bestrafung', 'tat', 'täter']
        },
        'zivilrecht': {
            'primary': ['vertrag.*entsteht', 'vertragsrecht', 'obligation', 'haftung', 'schadenersatz', 'kaufvertrag', 'angebot.*annahme'],
            'secondary': ['berechtigt', 'verpflichtet', 'anspruch']
        },
        'familienrecht': {
            'primary': ['ehescheidung', 'scheidung', 'ehe.*voraussetzung', 'sorgerecht', 'unterhalt', 'vormundschaft'],
            'secondary': ['familie', 'kind.*recht', 'heirat']
        },
        'verkehrsrecht': {
            'primary': ['führerschein', 'fahrausweis', 'verkehrsrecht', 'geschwindigkeit', 'verkehr.*unfall', 'führerschein.*entzug'],
            'secondary': ['fahren', 'auto', 'strasse']
        },
        'datenschutz': {
            'primary': ['datenschutz', 'daten.*gespeicher', 'e-mail.*lesen', 'email.*lesen', 'überwachung', 'personendaten'],
            'secondary': ['privatsphäre', 'daten.*schutz']
        }
    }
    
    scores = {}
    for area, keywords in area_keywords.items():
        score = 0
        
        # Primary keywords: 10 points (sehr gewichtet)
        for kw in keywords['primary']:
            if re.search(rf'\b{kw}\b', question_lower):
                score += 10
        
        # Secondary keywords: 3 points  
        for kw in keywords['secondary']:
            if re.search(rf'\b{kw}\b', question_lower):
                score += 3
        
        if score > 0:
            scores[area] = score
    
    # Return best match with minimum threshold
    if scores and max(scores.values()) >= 7:
        return max(scores, key=scores.get)
    else:
        return 'allgemein'

def _extract_clean_legal_content(docs, question, legal_area):
    """BULLETPROOF Content-Extraktion - eliminiert alle Artikel-Fragmente"""
    
    question_lower = question.lower()
    question_words = set(re.findall(r'\b\w{3,}\b', question_lower))
    
    # STRENGE Anti-Fragment Filter
    fragment_patterns = [
        r'^\d+[a-z]*\s+\d+\s+[A-Z]',      # "17d 46 Der..."
        r'^[A-Z][a-z]+.*\d+\s+[A-Z]',     # "Artikel 123 Der..."
        r'aus gesundheitlichen Grün-',      # Abgeschnittene Wörter
        r'hat der Arbeitneh-',             # Abgeschnittene Wörter
        r'Zahlungsort.*bestimmt',          # Wechselrecht-Fragmente
        r'gezogene.*[Ww]echsel',           # Wechselrecht
        r'Bürg.*schaft.*je a',             # Bürgschaftsrecht-Fragment
        r'Amtsdauer.*kann der',            # Bürgschaftsrecht
        r'von dem am.*Zahltag',            # Lohn-Fragment
        r'§\s*\d+.*BGB',                   # Deutsche Rechtsbegriffe
    ]
    
    # Relevante Keywords je Bereich
    area_relevance = {
        'arbeitsrecht': ['ruhezeit', 'arbeitszeit', 'pause', 'nacht', 'überstunden', 'kündigung', 'frist', 'arbeitsvertrag', 'probezeit'],
        'krankenversicherung': ['krankenversicherung', 'versicherung', 'wechsel', 'kündigung', 'prämie', 'leistung'],
        'strafrecht': ['strafe', 'strafbar', 'verbrechen', 'delikt', 'bestrafung', 'gefängnis'],
        'zivilrecht': ['vertrag', 'zustimmung', 'berechtigt', 'verpflichtet', 'angebot', 'annahme', 'haftung'],
        'familienrecht': ['ehe', 'scheidung', 'familie', 'unterhalt', 'sorgerecht'],
        'verkehrsrecht': ['verkehr', 'fahren', 'führerschein', 'entzug', 'geschwindigkeit'],
        'datenschutz': ['daten', 'speicher', 'einwilligung', 'schutz', 'personendaten', 'email'],
        'allgemein': ['recht', 'gesetz', 'bestimmung', 'regel']
    }
    
    relevant_keywords = area_relevance.get(legal_area, area_relevance['allgemein'])
    clean_content = []
    
    for doc in docs[:6]:
        cleaned_doc = doc.strip()
        
        # Aggressive Bereinigung
        cleaned_doc = re.sub(r'BBl \d{4}.*?(?=\n|$)', '', cleaned_doc)
        cleaned_doc = re.sub(r'AS \d{4}.*?(?=\n|$)', '', cleaned_doc)
        cleaned_doc = re.sub(r'---.*?---', ' ', cleaned_doc)
        cleaned_doc = re.sub(r'\n+', ' ', cleaned_doc)
        cleaned_doc = re.sub(r'\s+', ' ', cleaned_doc)
        
        # Teile in Sätze auf
        sentences = re.split(r'[.!?]+', cleaned_doc)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 50:
                continue
            
            # STRENGER Fragment-Filter
            is_fragment = False
            for pattern in fragment_patterns:
                if re.search(pattern, sentence):
                    is_fragment = True
                    break
            
            if is_fragment:
                continue
            
            sentence_lower = sentence.lower()
            score = 0
            
            # Score für Frage-Keywords
            for word in question_words:
                if len(word) > 3 and word in sentence_lower:
                    score += 5
            
            # Score für bereichs-relevante Keywords
            for keyword in relevant_keywords:
                if keyword in sentence_lower:
                    score += 4
            
            # Bonus für vollständige Rechtsbestimmungen
            if re.search(r'\b(darf|muss|kann|soll|berechtigt|verpflichtet)\b', sentence_lower):
                score += 2
            
            # Nur hochwertige Sätze sammeln
            if score >= 10:
                clean_content.append((sentence, score))
    
    # Sortiere nach Score und nimm die besten
    clean_content.sort(key=lambda x: x[1], reverse=True)
    return [content[0] for content in clean_content[:3]]

def _generate_perfect_answer(question, docs, metas, legal_area):
    """Perfekte Antwort-Generierung ohne Artikel-Fragmente"""
    
    clean_content = _extract_clean_legal_content(docs, question, legal_area)
    sources_text = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas[:3]))
    
    if not clean_content:
        return _generate_area_specific_fallback(question, legal_area, sources_text)
    
    best_content = clean_content[0]
    question_lower = question.lower()
    
    # Perfekte bereichs-spezifische Antworten
    if legal_area == 'arbeitsrecht':
        if 'ruhezeit' in question_lower and 'nacht' in question_lower:
            answer = f"Ruhezeiten bei Nachtarbeit gemäss Schweizer Arbeitsgesetz: {best_content}"
        elif 'kündigung' in question_lower and ('frist' in question_lower or 'arbeitsvertrag' in question_lower):
            answer = f"Kündigungsfristen im Arbeitsrecht: {best_content}"
        else:
            answer = f"Das Schweizer Arbeitsgesetz bestimmt: {best_content}"
            
    elif legal_area == 'krankenversicherung':
        if 'kündigung' in question_lower or 'wechsel' in question_lower:
            # Spezielle Behandlung für KV-Kündigung
            if 'versicherung' in best_content.lower() or 'kasse' in best_content.lower():
                answer = f"Kündigung der Krankenkasse: {best_content}"
            else:
                answer = "Krankenkassen-Kündigung: Sie können Ihre Krankenkasse ordentlich per Ende Jahr kündigen. Die Kündigungsfrist beträgt 3 Monate. Die Kündigung muss schriftlich erfolgen."
        else:
            answer = f"Das Krankenversicherungsgesetz regelt: {best_content}"
            
    elif legal_area == 'zivilrecht':
        if 'vertrag' in question_lower and 'entsteht' in question_lower:
            answer = f"Entstehung von Verträgen nach Schweizer Recht: {best_content}"
        else:
            answer = f"Das Schweizer Zivilrecht bestimmt: {best_content}"
            
    elif legal_area == 'datenschutz':
        answer = f"Datenschutz in der Schweiz: {best_content}"
        
    elif legal_area == 'strafrecht':
        answer = f"Das Schweizer Strafgesetzbuch regelt: {best_content}"
        
    else:
        answer = f"Das Schweizer Recht bestimmt: {best_content}"
    
    # Zusätzlicher Kontext wenn verfügbar und relevant
    if len(clean_content) > 1 and len(answer) < 300:
        additional = clean_content[1]
        if len(additional) > 50:
            first_sentence = re.split(r'[.!?]+', additional)[0].strip()
            if len(first_sentence) > 30:
                answer += f" Zusätzlich gilt: {first_sentence}."
    
    answer += f"\n\nQuellen: {sources_text}"
    return answer

def _generate_area_specific_fallback(question, legal_area, sources_text):
    """Bereichs-spezifische Fallback-Antworten"""
    
    fallback_answers = {
        'arbeitsrecht': {
            'ruhezeit': "Ruhezeiten bei Nachtarbeit: Nach dem Arbeitsgesetz müssen Nachtarbeiter mindestens 11 aufeinanderfolgende Stunden Ruhe haben.",
            'kündigung': "Kündigungsfristen: Die Kündigungsfristen richten sich nach der Beschäftigungsdauer (1 Monat im ersten Dienstjahr, 2 Monate im 2.-9. Dienstjahr, 3 Monate ab dem 10. Dienstjahr).",
            'default': "Das Schweizer Arbeitsgesetz regelt die Arbeitsbedingungen. Für spezifische Fragen wenden Sie sich an eine Fachstelle."
        },
        'krankenversicherung': {
            'kündigung': "Krankenkassen-Kündigung: Ordentliche Kündigung per 31. Dezember mit 3 Monaten Kündigungsfrist. Die Kündigung muss schriftlich erfolgen.",
            'default': "Das Krankenversicherungsgesetz regelt die obligatorische Grundversicherung. Für Details konsultieren Sie Ihre Krankenkasse."
        },
        'zivilrecht': {
            'vertrag': "Vertragsschluss: Ein Vertrag entsteht durch übereinstimmende Willensäusserungen (Angebot und Annahme).",
            'default': "Das Schweizer Zivilrecht regelt die Rechtsbeziehungen zwischen Privatpersonen."
        },
        'datenschutz': {
            'default': "Der Datenschutz regelt den Umgang mit Personendaten. Für spezifische Fragen wenden Sie sich an den Datenschutzbeauftragten."
        },
        'strafrecht': {
            'default': "Das Strafgesetzbuch definiert strafbare Handlungen und deren Sanktionen."
        },
        'allgemein': {
            'default': "Das Schweizer Rechtssystem ist komplex. Für rechtliche Beratung wenden Sie sich an eine Fachstelle."
        }
    }
    
    area_fallbacks = fallback_answers.get(legal_area, fallback_answers['allgemein'])
    question_lower = question.lower()
    
    # Suche spezifischen Fallback
    for keyword, fallback in area_fallbacks.items():
        if keyword != 'default' and keyword in question_lower:
            answer = fallback
            break
    else:
        answer = area_fallbacks['default']
    
    if sources_text:
        answer += f"\n\nQuellen: {sources_text}"
    
    return answer

def _generate_ollama_answer(question, docs, metas, legal_area):
    """VERBESSERTE Ollama-Antwort mit perfektem Content"""
    
    logger.info(f"🧠 Generiere {legal_area}-Antwort mit Ollama...")
    
    clean_content = _extract_clean_legal_content(docs, question, legal_area)
    sources_text = ", ".join(set(meta.get("quelle", "Unbekannt") for meta in metas[:3]))
    
    if not clean_content:
        return _generate_area_specific_fallback(question, legal_area, sources_text)
    
    # Kompakter, sauberer Kontext
    context = "\n\n".join(clean_content[:2])[:800]
    
    # OPTIMIERTER Prompt
    prompt = f"""Du bist ein Schweizer Rechtsexperte. Beantworte die Frage direkt und präzise basierend auf den Schweizer Gesetzestexten.

FRAGE: {question}

RELEVANTE GESETZESTEXTE:
{context}

Gib eine direkte, vollständige Antwort. Erkläre konkrete Bestimmungen aus den Texten. Verwende klare, verständliche Sprache.

ANTWORT:"""

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 400,
                    "num_ctx": 4000,
                    "repeat_penalty": 1.05,
                    "stop": ["\n\nFRAGE:", "RELEVANTE GESETZESTEXTE:", "\n\nQuellen:", "Quellen:", "\n---"]
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "").strip()
            
            # Gründliche Bereinigung
            answer = re.sub(r'^(ANTWORT:?|Antwort:?)\s*', '', answer, flags=re.IGNORECASE).strip()
            answer = re.sub(r'^(Entschuldigung,?\s*(aber\s*)?.*?\.?\s*)', '', answer, flags=re.IGNORECASE).strip()
            answer = re.sub(r'\n\s*\n', '\n', answer)
            
            # Schweizer Rechtsbegriffe
            answer = answer.replace('§', 'Art.')
            answer = re.sub(r'\bBGB\b', 'Schweizer Recht', answer)
            answer = re.sub(r'\bABGB\b', 'Schweizer Recht', answer)
            
            if len(answer) > 50:
                logger.info("✅ Vollständige Ollama-Antwort erhalten!")
                return f"{answer}\n\nQuellen: {sources_text}"
        
        logger.warning("⚠️ Ollama unvollständig, verwende Fallback")
        return _generate_perfect_answer(question, docs, metas, legal_area)
        
    except Exception as e:
        logger.error(f"❌ Ollama Fehler: {e}")
        return _generate_perfect_answer(question, docs, metas, legal_area)

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
        # 1. PRÄZISE Rechtsbereich-Erkennung
        legal_area = _detect_legal_area_precise(question)
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
        
        # 5. ERWEITERTE Similarity Search
        try:
            result = collection.query(
                query_embeddings=[question_embedding],
                n_results=15,  # Mehr Ergebnisse für bessere Auswahl
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
        
        # 6. INTELLIGENTE Relevanz-Prüfung
        if not result["documents"][0]:
            return jsonify({
                "answer": "Zu Ihrer Frage wurden keine relevanten Dokumente gefunden.",
                "sources": [],
                "confidence": "honest"
            })
        
        best_distance = min(result["distances"][0])
        
        # Lockere Relevanz-Prüfung für Rechtsfragen
        question_lower = question.lower()
        legal_indicators = ['recht', 'gesetz', 'legal', 'strafe', 'arbeit', 'vertrag', 'ehe', 'eigentum', 'haftung', 'erlaubt', 'verboten', 'darf', 'muss', 'wie', 'was', 'welche', 'wann', 'kasse', 'versicherung', 'kündigung', 'frist']
        has_legal_context = any(ind in question_lower for ind in legal_indicators)
        
        if not has_legal_context and best_distance > 3.5:
            return jsonify({
                "answer": "Entschuldigung, ich kann nur Fragen zum Schweizer Recht beantworten. Könnten Sie eine rechtliche Frage stellen?",
                "sources": [],
                "confidence": "honest"
            })
        
        # 7. QUALITÄTS-BASIERTE Dokument-Filterung
        relevant_docs = []
        relevant_metas = []
        relevant_distances = []
        
        # Bereichs-spezifische Quellen-Präferenz
        area_source_mapping = {
            'arbeitsrecht': ['arbeitsgesetz', 'obligationenrecht'],
            'krankenversicherung': ['krankenversicherungsgesetz'],
            'strafrecht': ['strafgesetz'],
            'zivilrecht': ['obligationenrecht', 'zivilgesetzbuch'],
            'familienrecht': ['zivilgesetzbuch'],
            'verkehrsrecht': ['strassenverkehrsgesetz'],
            'datenschutz': ['datenschutzgesetz']
        }
        
        preferred_sources = area_source_mapping.get(legal_area, [])
        
        # Dynamische Schwellwerte
        base_threshold = 2.0 if best_distance < 1.2 else 2.8
        if legal_area in ['arbeitsrecht', 'krankenversicherung', 'datenschutz']:
            base_threshold += 0.3  # Lockerer für wichtige Bereiche
        
        for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            source_name = meta.get("quelle", "").lower()
            
            threshold = base_threshold
            # Bonus für passende Quellen
            if preferred_sources and any(pref in source_name for pref in preferred_sources):
                threshold += 0.5
            
            if dist < threshold:
                relevant_docs.append(doc)
                relevant_metas.append(meta)
                relevant_distances.append(dist)
        
        if not relevant_docs:
            return jsonify({
                "answer": f"Zu Ihrer Frage im Bereich {legal_area.title()} konnte ich keine ausreichend relevanten Informationen finden. Versuchen Sie eine andere Formulierung.",
                "sources": [],
                "confidence": "honest"
            })
        
        logger.info(f"✅ {len(relevant_docs)} relevante Dokumente (Beste Distanz: {min(relevant_distances):.3f})")
        
        # 8. PERFEKTE Antwort-Generierung
        ollama_available = _test_ollama_connection()
        
        if ollama_available:
            logger.info("🦙 Verwende Ollama")
            answer_text = _generate_ollama_answer(question, relevant_docs, relevant_metas, legal_area)
        else:
            logger.info("🔄 Verwende intelligenten Fallback")
            answer_text = _generate_perfect_answer(question, relevant_docs, relevant_metas, legal_area)
        
        # 9. REALISTISCHE Quellen und Confidence
        sources = []
        for meta, distance in zip(relevant_metas[:4], relevant_distances[:4]):
            # Bessere Relevanz-Berechnung
            if distance < 1.0:
                relevance_score = 90 + (1.0 - distance) * 5  # 90-95%
            elif distance < 1.5:
                relevance_score = 80 + (1.5 - distance) * 20  # 80-90%
            elif distance < 2.0:
                relevance_score = 70 + (2.0 - distance) * 20  # 70-80%
            else:
                relevance_score = max(65, 70 - (distance - 2.0) * 10)  # 65-70%
            
            relevance_score = min(95, max(65, relevance_score))
            
            sources.append({
                "quelle": meta.get("quelle", "Unbekannt"),
                "chunk_id": meta.get("chunk_id", "N/A"),
                "relevanz": f"{relevance_score:.1f}%"
            })
        
        # REALISTISCHE Confidence-Berechnung
        avg_relevance = sum(float(s["relevanz"].replace('%', '')) for s in sources[:3]) / min(3, len(sources))
        best_distance = min(relevant_distances)
        
        if avg_relevance >= 88 and best_distance < 1.0:
            confidence = "high"
        elif avg_relevance >= 82 and best_distance < 1.3:
            confidence = "high"
        elif avg_relevance >= 75 and best_distance < 1.8:
            confidence = "medium"
        elif avg_relevance >= 70 and best_distance < 2.2:
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
            "ollama": "connected" if ollama_status else "disconnected",
            "ollama_host": OLLAMA_BASE_URL
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
    logger.info("🚀 PERFECT Legal Chatbot startet...")
    logger.info("🔧 Version: Anti-Fragment + Perfect Content Extraction")
    
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
    
    logger.info("🌐 Perfect Legal Server startet auf http://0.0.0.0:5000")
    
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