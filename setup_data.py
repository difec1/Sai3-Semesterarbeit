import os
import json
import uuid
import chromadb
import time
import logging
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HuggingFaceProcessor:
    def __init__(self):
        self.data_dir = Path("data")
        self.text_dir = self.data_dir / "text"
        self.chunks_dir = self.data_dir / "chunks"
        self.embeddings_file = self.data_dir / "embeddings_hf.json"
        
        # Ordner erstellen
        for dir_path in [self.data_dir, self.text_dir, self.chunks_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # HuggingFace Parameter
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.chunk_size = 400
        self.overlap = 100
        
        # Model laden
        logger.info(f"🤗 Lade HuggingFace Model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("✅ HuggingFace Model erfolgreich geladen!")
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden des Models: {e}")
            logger.info("Installieren Sie: pip install sentence-transformers")
            raise
    
    def create_chunks(self) -> None:
        """Texte in Chunks aufteilen"""
        logger.info("✂️ Starte Text-Chunking...")
        
        txt_files = list(self.text_dir.glob("*.txt"))
        if not txt_files:
            logger.warning("❌ Keine Textdateien gefunden!")
            return
        
        # Chunks-Ordner leeren
        for chunk_file in self.chunks_dir.glob("*.txt"):
            chunk_file.unlink()
        
        total_chunks = 0
        
        for txt_path in txt_files:
            logger.info(f"✂️ Chunking: {txt_path.name}")
            
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            chunks = self._split_into_chunks(text)
            
            base_name = txt_path.stem
            for i, chunk in enumerate(chunks):
                chunk_path = self.chunks_dir / f"{base_name}_chunk_{i+1:03d}.txt"
                with open(chunk_path, "w", encoding="utf-8") as f:
                    f.write(chunk)
            
            total_chunks += len(chunks)
            logger.info(f"✅ {txt_path.name} → {len(chunks)} Chunks")
        
        logger.info(f"✂️ Chunking abgeschlossen: {total_chunks} Chunks total")
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Text intelligent chunken"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Nur Chunks mit genügend Inhalt
            if len(chunk_text.strip()) > 50:
                chunks.append(chunk_text)
        
        return chunks
    
    def create_embeddings(self) -> None:
        """Embeddings mit HuggingFace erstellen"""
        logger.info("🧠 Starte Embedding-Erstellung mit HuggingFace...")
        
        # Prüfen ob Embeddings bereits existieren
        if self.embeddings_file.exists():
            logger.info("📁 Embeddings bereits vorhanden - überspringe Erstellung")
            return
        
        chunk_files = sorted(list(self.chunks_dir.glob("*.txt")))
        if not chunk_files:
            logger.warning("❌ Keine Chunk-Dateien gefunden!")
            return
        
        embeddings_data = []
        
        # Alle Texte laden
        texts = []
        file_info = []
        
        for chunk_path in chunk_files:
            with open(chunk_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            
            if len(text) > 50:  # Nur ausreichend lange Texte
                texts.append(text)
                
                # Metadaten extrahieren
                filename = chunk_path.name
                parts = filename.replace(".txt", "").split("_chunk_")
                quelle = parts[0] if len(parts) > 1 else "unknown"
                chunk_id = parts[1] if len(parts) > 1 else "0"
                
                file_info.append({
                    "filename": filename,
                    "quelle": quelle,
                    "chunk_id": chunk_id
                })
        
        logger.info(f"📊 Verarbeite {len(texts)} Chunks...")
        
        # BATCH-Verarbeitung mit HuggingFace (sehr schnell!)
        try:
            batch_size = 32  # Optimal für die meisten GPUs/CPUs
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Embeddings für Batch erstellen
                batch_embeddings = self.model.encode(
                    batch_texts,
                    show_progress_bar=True,
                    convert_to_numpy=True
                )
                
                all_embeddings.extend(batch_embeddings)
                
                if (i + batch_size) % 100 == 0:
                    logger.info(f"📈 Fortschritt: {min(i + batch_size, len(texts))}/{len(texts)} Chunks")
            
            # Daten zusammenstellen
            for text, embedding, info in zip(texts, all_embeddings, file_info):
                embeddings_data.append({
                    "id": str(uuid.uuid4()),
                    "text": text,
                    "quelle": info["quelle"],
                    "chunk_id": info["chunk_id"],
                    "filename": info["filename"],
                    "embedding": embedding.tolist()  # NumPy zu List
                })
            
            logger.info(f"🧠 Embeddings erstellt: {len(embeddings_data)} erfolgreich")
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Embedding-Erstellung: {e}")
            return
        
        # Embeddings speichern
        with open(self.embeddings_file, "w", encoding="utf-8") as f:
            json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Embeddings gespeichert in: {self.embeddings_file}")
    
    def import_to_chroma(self) -> None:
        """Embeddings in ChromaDB importieren - MIT FALLBACK"""
        logger.info("📚 Starte ChromaDB-Import...")
        
        if not self.embeddings_file.exists():
            logger.error("❌ Embeddings-Datei nicht gefunden!")
            return
        
        # ChromaDB-Client mit Fallback-Strategie
        client = None
        
        # Versuch 1: HTTP Client (Docker)
        try:
            logger.info("🔄 Versuche HTTP-Client (Docker)...")
            client = chromadb.HttpClient(host="localhost", port=8000)
            client.heartbeat()
            logger.info("✅ HTTP-Client erfolgreich!")
        except Exception as e:
            logger.warning(f"⚠️ HTTP-Client fehlgeschlagen: {e}")
        
        # Versuch 2: Lokaler Persistent Client
        if not client:
            try:
                logger.info("🔄 Versuche lokalen Client...")
                client = chromadb.PersistentClient(path="./chroma_data")
                logger.info("✅ Lokaler Client erfolgreich!")
            except Exception as e:
                logger.error(f"❌ Alle ChromaDB-Verbindungen fehlgeschlagen: {e}")
                logger.info("💡 Installieren Sie ChromaDB: pip install chromadb")
                return
        
        try:
            # Collection löschen und neu erstellen
            try:
                client.delete_collection("gesetzestexte")
                logger.info("🗑️ Alte Collection gelöscht")
            except:
                pass
            
            collection = client.create_collection("gesetzestexte")
            logger.info("🆕 Neue Collection erstellt")
            
            # Embeddings laden
            with open(self.embeddings_file, "r", encoding="utf-8") as f:
                embeddings_data = json.load(f)
            
            logger.info(f"📁 {len(embeddings_data)} Embeddings geladen")
            
            # Batch-Import mit Fehlerbehandlung
            batch_size = 100
            imported_count = 0
            
            for i in range(0, len(embeddings_data), batch_size):
                batch = embeddings_data[i:i + batch_size]
                
                try:
                    collection.add(
                        ids=[entry["id"] for entry in batch],
                        documents=[entry["text"] for entry in batch],
                        embeddings=[entry["embedding"] for entry in batch],
                        metadatas=[{
                            "filename": entry["filename"],
                            "chunk_id": entry["chunk_id"],
                            "quelle": entry["quelle"]
                        } for entry in batch]
                    )
                    
                    imported_count += len(batch)
                    logger.info(f"✅ Batch {i//batch_size + 1}: {len(batch)} Dokumente importiert")
                    
                except Exception as e:
                    logger.error(f"❌ Batch-Import Fehler: {e}")
            
            # Verifikation
            final_count = collection.count()
            logger.info(f"✅ ChromaDB-Import abgeschlossen: {final_count} Dokumente")
            
            # BONUS: Schneller Suchtest
            try:
                test_embedding = self.model.encode(["Test"])[0].tolist()
                result = collection.query(
                    query_embeddings=[test_embedding],
                    n_results=1,
                    include=["documents"]
                )
                if result["documents"][0]:
                    logger.info("🎯 Suchtest erfolgreich - System bereit!")
                else:
                    logger.warning("⚠️ Suchtest ergab keine Ergebnisse")
            except Exception as e:
                logger.warning(f"⚠️ Suchtest fehlgeschlagen: {e}")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB-Import fehlgeschlagen: {e}")
            raise

def main():
    """Hauptfunktion"""
    logger.info("🤗 HuggingFace Embedding Pipeline")
    
    try:
        processor = HuggingFaceProcessor()
        
        # Prüfen ob Textdateien vorhanden
        txt_files = list(Path("data/text").glob("*.txt"))
        
        if not txt_files:
            logger.error("❌ Keine Textdateien gefunden!")
            logger.info("Legen Sie Textdateien in data/text/ oder führen Sie extract_text.py aus")
            return
        
        logger.info(f"📄 Gefundene Textdateien: {len(txt_files)}")
        for txt_file in txt_files:
            logger.info(f"  📄 {txt_file.name}")
        
        # Pipeline manuell starten
        logger.info("🚀 === Starte HuggingFace Datenverarbeitungs-Pipeline ===")
        
        processor.create_chunks()
        processor.create_embeddings()
        processor.import_to_chroma()
        
        logger.info("🎉 HuggingFace Pipeline erfolgreich abgeschlossen!")
        logger.info("🚀 Sie können jetzt die App starten: python app.py")
        
    except Exception as e:
        logger.error(f"❌ Hauptfehler: {e}")
        logger.info("💡 Falls Probleme auftreten:")
        logger.info("   1. Stellen Sie sicher, dass ChromaDB läuft (docker-compose up -d)")
        logger.info("   2. Oder das Script wird lokale ChromaDB verwenden")

if __name__ == "__main__":
    main()