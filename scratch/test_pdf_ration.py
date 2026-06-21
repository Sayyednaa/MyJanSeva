import pypdf
import os

pdf_path = r"c:\Users\Abdul\Documents\Ali\Code\janseva\static\id_cards\ration-card\rationCard.pdf"

if os.path.exists(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total Pages: {len(reader.pages)}")
    for i, page in enumerate(reader.pages):
        print(f"\n--- PAGE {i+1} ---")
        print(page.extract_text())
else:
    print(f"File not found: {pdf_path}")
