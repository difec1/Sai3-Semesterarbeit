#!/bin/bash

echo "🐳 Starting Docker Chatbot System..."

# ChromaDB Datenordner aufräumen (WICHTIG!)
echo "🧹 Cleaning ChromaDB data..."
rm -rf /app/chroma_data/* 2>/dev/null || true

# ChromaDB Server im Hintergrund starten
echo "📚 Starting ChromaDB Server..."
chroma run --host 0.0.0.0 --port 8000 --path /app/chroma_data &
CHROMA_PID=$!

# Warten bis ChromaDB bereit ist
echo "⏳ Waiting for ChromaDB to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
        echo "✅ ChromaDB is ready!"
        break
    fi
    echo "   Attempt $i/30..."
    sleep 2
done

# IMMER Daten verarbeiten, da ChromaDB Collection fehlt (wie Original)
echo "📄 Setting up data processing..."

# Prüfen ob PDFs vorhanden sind
if ls /app/data/*.pdf 1> /dev/null 2>&1; then
    echo "📑 PDFs found. Processing..."
    
    # Versuche ursprüngliche Scripts zu verwenden, sonst Fallback
    if [ -f "/app/extract_text.py" ] && [ -f "/app/chunk_text.py" ] && [ -f "/app/setup_data.py" ]; then
        echo "📋 Using original processing scripts..."
        
        # PDF → Text
        echo "🔤 Extracting text from PDFs..."
        cd /app && python extract_text.py
        
        # Text → Chunks  
        echo "✂️ Creating chunks..."
        cd /app && python chunk_text.py
        
        # Embeddings erstellen und in ChromaDB importieren
        echo "🧠 Creating embeddings and importing to ChromaDB..."
        cd /app && python setup_data.py
        
    elif [ -f "/app/process_pdfs.py" ] && [ -f "/app/import_to_chroma.py" ]; then
        echo "📋 Using new processing pipeline..."
        
        # Neue Pipeline verwenden
        cd /app && python process_pdfs.py
        cd /app && python import_to_chroma.py
        
    else
        echo "❌ No processing scripts found!"
        echo "📝 Please add the required processing scripts"
    fi
    
    echo "✅ Data processing completed!"
else
    echo "⚠️ No PDFs found in /app/data/"
    echo "📝 Please add PDFs and restart the container"
fi

# Trap für graceful shutdown
trap 'echo "🛑 Shutting down..."; kill $CHROMA_PID 2>/dev/null || true; exit 0' SIGTERM SIGINT

# Flask App starten
echo "🚀 Starting Flask Application..."
exec python app.py