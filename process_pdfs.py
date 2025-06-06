#!/usr/bin/env python3
"""
PDF Processing Pipeline - WORKING VERSION
Simple but effective chunking for legal texts
"""

import os
import json
import uuid
import fitz  # PyMuPDF
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer

def extract_text_from_pdfs():
    """Extract text from PDFs"""
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

def clean_text_for_chunking(text):
    """Simple but effective text cleaning"""
    
    # Remove noisy patterns
    patterns_to_clean = [
        r'BBl \d{4} \d+.*?(?=\n|Art\.|$)',     # BBl references
        r'AS \d{4} \d+.*?(?=\n|Art\.|$)',      # AS references
        r'---+.*?---+',                         # Separators  
        r'Seite \d+',                          # Page numbers
        r'Eingefügt durch.*?(?=\n|Art\.|$)',   # Change notes
        r'Fassung gemäss.*?(?=\n|Art\.|$)',    # Version notes
    ]
    
    cleaned = text
    for pattern in patterns_to_clean:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
    
    # Normalize whitespace but keep structure
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)            # Multiple spaces
    
    return cleaned.strip()

def create_smart_chunks():
    """Create smart chunks that respect legal structure"""
    print("✂️ Creating smart legal chunks...")
    
    input_folder = "data/text"
    output_folder = "data/chunks"
    os.makedirs(output_folder, exist_ok=True)
    
    target_size = 350  # words
    overlap = 60       # words
    
    def split_text_smartly(text, target_size=350, overlap=60):
        """Smart splitting that respects legal structure"""
        
        chunks = []
        text = clean_text_for_chunking(text)
        
        # Try to split by articles first
        article_pattern = r'(Art\.\s*\d+[a-z]*[.\s]*)'
        parts = re.split(article_pattern, text, flags=re.IGNORECASE)
        
        current_chunk = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if adding this part would exceed target size
            potential_chunk = current_chunk + " " + part
            word_count = len(potential_chunk.split())
            
            if word_count <= target_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it's substantial
                if len(current_chunk.split()) > 50:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk
                if len(part.split()) > target_size:
                    # Split large parts into smaller chunks
                    words = part.split()
                    for i in range(0, len(words), target_size - overlap):
                        chunk_words = words[i:i + target_size]
                        chunk_text = " ".join(chunk_words)
                        if len(chunk_text) > 100:  # Minimum length
                            chunks.append(chunk_text)
                    current_chunk = ""
                else:
                    current_chunk = part
        
        # Add the last chunk
        if current_chunk.strip() and len(current_chunk.split()) > 20:
            chunks.append(current_chunk.strip())
        
        # Filter out chunks that are too short or mostly references
        good_chunks = []
        for chunk in chunks:
            if (len(chunk) > 80 and 
                len(chunk.split()) > 15 and
                not chunk.strip().startswith(('---', 'Seite', 'BBl', 'AS'))):
                good_chunks.append(chunk)
        
        return good_chunks
    
    txt_files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
    if not txt_files:
        print("❌ No text files found!")
        return False
    
    total_chunks = 0
    for filename in txt_files:
        input_path = os.path.join(input_folder, filename)
        print(f"✂️ Smart chunking: {filename}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        
        chunks = split_text_smartly(full_text, target_size, overlap)
        
        base_name = filename.replace(".txt", "")
        for i, chunk in enumerate(chunks):
            chunk_filename = f"{base_name}_chunk_{i+1:03d}.txt"
            chunk_path = os.path.join(output_folder, chunk_filename)
            with open(chunk_path, "w", encoding="utf-8") as cf:
                cf.write(chunk)
        
        total_chunks += len(chunks)
        print(f"✅ {filename} → {len(chunks)} smart chunks")
    
    print(f"✂️ Smart chunking completed: {total_chunks} quality chunks")
    return True

def create_embeddings():
    """Create embeddings with HuggingFace model"""
    print("🧠 Creating embeddings...")
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"🤗 Loading model: {model_name}")
    
    try:
        model = SentenceTransformer(model_name)
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False
    
    chunks_dir = Path("data/chunks")
    chunk_files = sorted(list(chunks_dir.glob("*.txt")))
    
    if not chunk_files:
        print("❌ No chunk files found!")
        return False
    
    texts = []
    file_info = []
    
    print(f"📊 Processing {len(chunk_files)} chunk files...")
    
    for chunk_path in chunk_files:
        with open(chunk_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        if len(text) > 50:  # Only substantial chunks
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
    
    print(f"📊 Creating embeddings for {len(texts)} chunks...")
    
    try:
        # Create embeddings efficiently
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            batch_size=32
        )
        
        # Prepare data structure
        embeddings_data = []
        for text, embedding, info in zip(texts, embeddings, file_info):
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
        print(f"📁 File: {embeddings_file}")
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
    
    # Step 2: Create smart chunks
    if not create_smart_chunks():
        print("❌ Smart chunking failed!")
        return False
    
    # Step 3: Create embeddings
    if not create_embeddings():
        print("❌ Embedding creation failed!")
        return False
    
    print("🎉 PDF processing pipeline completed successfully!")
    print("📊 Your legal texts are now ready for high-quality search!")
    return True

if __name__ == "__main__":
    main()