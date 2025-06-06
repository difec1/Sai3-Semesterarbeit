#!/bin/bash

# ChromaDB im Hintergrund starten
echo "Starting ChromaDB..."
chroma run --host 0.0.0.0 --port 8000 --path /app/chroma_data &

# Warten bis ChromaDB bereit ist
sleep 10

# Flask-App starten
echo "Starting Flask App..."
python app.py