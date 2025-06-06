#!/usr/bin/env python3
"""
PDF Processing Pipeline - Standalone version
Combines extract_text.py + chunk_text.py + embedding creation
"""

import os
import json
import uuid
import fitz  # PyMuPDF
from pathlib import Path
from sentence_transformers import SentenceTransformer

def extract_text_from_pdfs():
    """Extract text from PDFs - matches original extract_text.py"""
    print("🔤 Extracting text from PDFs...")
    
    input_folder = "data"
    output_folder = "data/text"
    os.makedirs(output_folder, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(input_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print("❌ No PDF files found!")
        return False
    
    for filename in pdf_files:
        pdf_path = os.path.join(input_folder, filename)
        print(f"📄 Processing: {filename}")
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page_num, page in enumerate(doc, start=1):
                full_text += f"\n--- Seite {page_num} ---\n"
                full_text += page.get_text()
            doc.close()
            
            txt_filename = filename.replace(".pdf", ".txt")
            txt_path = os.path.join(output_folder, txt_filename)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            print(f"✅ {filename} → {txt_filename}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
    
    return True

def create_chunks():
    """Create chunks from text - matches original chunk_text.py"""
    print("✂️ Creating chunks...")
    
    input_folder = "data/text"
    output_folder = "data/chunks"
    os.makedirs(output_folder, exist_ok=True)
    
    # Original parameters
    chunk_size = 500  # words
    overlap = 50      # words
    
    def split_into_chunks(text, chunk_size, overlap):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = words[i:i + chunk_size]
            chunks.append(" ".join(chunk))
        return chunks
    
    txt_files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
    if not txt_files:
        print("❌ No text files found!")
        return False
    
    total_chunks = 0
    for filename in txt_files:
        input_path = os.path.join(input_folder, filename)
        with open(input_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        
        chunks = split_into_chunks(full_text, chunk_size, overlap)
        
        base_name = filename.replace(".txt", "")
        for i, chunk in enumerate(chunks):
            chunk_filename = f"{base_name}_chunk_{i+1:03d}.txt"
            chunk_path = os.path.join(output_folder, chunk_filename)
            with open(chunk_path, "w", encoding="utf-8") as cf:
                cf.write(chunk)
        
        total_chunks += len(chunks)
        print(f"✅ {filename} → {len(chunks)} chunks")
    
    print(f"✂️ Total chunks created: {total_chunks}")
    return True

def create_embeddings():
    """Create embeddings - matches original setup_data.py logic"""
    print("🧠 Creating embeddings...")
    
    # Load HuggingFace model
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"🤗 Loading model: {model_name}")
    
    try:
        model = SentenceTransformer(model_name)
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False
    
    # Process chunks
    chunks_dir = Path("data/chunks")
    chunk_files = sorted(list(chunks_dir.glob("*.txt")))
    
    if not chunk_files:
        print("❌ No chunk files found!")
        return False
    
    # Load texts and metadata
    texts = []
    file_info = []
    
    for chunk_path in chunk_files:
        with open(chunk_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        if len(text) > 50:
            texts.append(text)
            
            filename = chunk_path.name
            parts = filename.replace(".txt", "").split("_chunk_")
            quelle = parts[0] if len(parts) > 1 else "unknown"
            chunk_id = parts[1] if len(parts) > 1 else "0"
            
            file_info.append({
                "filename": filename,
                "quelle": quelle,
                "chunk_id": chunk_id
            })
    
    print(f"📊 Processing {len(texts)} chunks...")
    
    # Create embeddings in batches
    try:
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = model.encode(
                batch_texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            all_embeddings.extend(batch_embeddings)
            
            if (i + batch_size) % 100 == 0:
                print(f"📈 Progress: {min(i + batch_size, len(texts))}/{len(texts)}")
        
        # Prepare data structure
        embeddings_data = []
        for text, embedding, info in zip(texts, all_embeddings, file_info):
            embeddings_data.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "quelle": info["quelle"],
                "chunk_id": info["chunk_id"],
                "filename": info["filename"],
                "embedding": embedding.tolist()
            })
        
        # Save embeddings
        embeddings_file = "data/embeddings_hf.json"
        with open(embeddings_file, "w", encoding="utf-8") as f:
            json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Embeddings saved: {len(embeddings_data)} items")
        return True
        
    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        return False

def main():
    """Main processing pipeline"""
    print("🚀 Starting PDF processing pipeline...")
    
    # Step 1: Extract text from PDFs
    if not extract_text_from_pdfs():
        print("❌ PDF extraction failed!")
        return False
    
    # Step 2: Create chunks
    if not create_chunks():
        print("❌ Chunking failed!")
        return False
    
    # Step 3: Create embeddings
    if not create_embeddings():
        print("❌ Embedding creation failed!")
        return False
    
    print("🎉 PDF processing pipeline completed successfully!")
    return True

if __name__ == "__main__":
    main()