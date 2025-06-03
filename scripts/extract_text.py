import fitz  # PyMuPDF
import os

# Pfade hart codiert
input_folder = "../data"
output_folder = "../data/text"

# Ordner erstellen, falls nicht vorhanden
os.makedirs(output_folder, exist_ok=True)

# Alle PDFs im Input-Ordner durchgehen
for filename in os.listdir(input_folder):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(input_folder, filename)
        print(f"📄 Bearbeite: {filename}")

        # PDF öffnen und Text extrahieren
        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num, page in enumerate(doc, start=1):
            full_text += f"\n--- Seite {page_num} ---\n"
            full_text += page.get_text()

        # Text als .txt speichern
        txt_filename = filename.replace(".pdf", ".txt")
        txt_path = os.path.join(output_folder, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

print("✅ Alle Texte wurden extrahiert und gespeichert.")
