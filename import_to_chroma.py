#!/usr/bin/env python3
"""
ChromaDB Import - Fast and reliable
"""

import json
import chromadb
from pathlib import Path

def import_to_chromadb():
    """Import embeddings to ChromaDB with fallback strategy"""
    print("📚 Starting ChromaDB import...")
    
    # Check if embeddings file exists
    embeddings_file = Path("data/embeddings_hf.json")
    if not embeddings_file.exists():
        print("❌ No embeddings file found! Run process_pdfs.py first.")
        return False
    
    # Load embeddings
    print("📁 Loading embeddings...")
    try:
        with open(embeddings_file, "r", encoding="utf-8") as f:
            embeddings_data = json.load(f)
        print(f"📊 Loaded {len(embeddings_data)} embeddings")
    except Exception as e:
        print(f"❌ Error loading embeddings: {e}")
        return False
    
    # Connect to ChromaDB with fallback
    client = None
    
    # Try HTTP client first (Docker)
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        print("✅ Connected to ChromaDB HTTP server")
    except Exception as e:
        print(f"⚠️ HTTP connection failed: {e}")
        
        # Fallback to persistent client
        try:
            client = chromadb.PersistentClient(path="./chroma_data")
            print("✅ Connected to ChromaDB persistent client")
        except Exception as e:
            print(f"❌ All ChromaDB connections failed: {e}")
            return False
    
    try:
        # Delete and recreate collection
        try:
            client.delete_collection("gesetzestexte")
            print("🗑️ Deleted old collection")
        except:
            pass  # Collection might not exist
        
        collection = client.create_collection("gesetzestexte")
        print("🆕 Created new collection")
        
        # Import in batches
        batch_size = 100
        total_imported = 0
        
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
                
                total_imported += len(batch)
                print(f"✅ Batch {i//batch_size + 1}: {len(batch)} documents")
                
            except Exception as e:
                print(f"❌ Batch import error: {e}")
                return False
        
        # Verify import
        final_count = collection.count()
        print(f"📊 Import completed: {final_count} documents in database")
        
        # Quick search test
        try:
            test_result = collection.query(
                query_texts=["Test"],
                n_results=1
            )
            if test_result["documents"][0]:
                print("🎯 Search test successful - system ready!")
            else:
                print("⚠️ Search test returned no results")
        except Exception as e:
            print(f"⚠️ Search test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB import failed: {e}")
        return False

def main():
    """Main import function"""
    if import_to_chromadb():
        print("🎉 ChromaDB import successful!")
        return True
    else:
        print("❌ ChromaDB import failed!")
        return False

if __name__ == "__main__":
    main()