import os

# Parameter
input_folder = "../data/text"
output_folder = "../data/chunks"
chunk_size = 500  # Wörter pro Chunk
overlap = 50      # Überlappung in Wörtern

# Ordner erstellen
os.makedirs(output_folder, exist_ok=True)

def split_into_chunks(text, chunk_size, overlap):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i:i + chunk_size]
        chunks.append(" ".join(chunk))
    return chunks

# Alle Textdateien durchgehen
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
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

        print(f"✅ {filename} → {len(chunks)} Chunks")

print("✅ Chunking abgeschlossen.")
