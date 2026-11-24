
from pathlib import Path

import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 1. Convert PDF to Markdown
pdf_path = "data/politique_carthage_air.pdf"

md_text = pymupdf4llm.to_markdown(pdf_path)

# Save extracted Markdown
Path("data/politique_carthage_air.md").write_text(
    md_text, encoding="utf-8"
)

# 2. Split Markdown by headers
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

chunks = markdown_splitter.split_text(md_text)

# 3. Initialize embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# 4. Store chunks in ChromaDB
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# 5. Display results
print(f"Successfully indexed {len(chunks)} chunks.")

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print("Metadata:", chunk.metadata)
    print("Content:", chunk.page_content[:300])

print("\nVector database saved in ./chroma_db")
