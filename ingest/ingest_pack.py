# ingest/ingest_pack.py
import json, uuid, pathlib
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from datetime import datetime

ROOT = pathlib.Path(__file__).parents[1]
EMB_DIR = ROOT / "data" / "embeddings"
RAW_DIR = ROOT / "data" / "raw_docs"
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

emb = OllamaEmbeddings(
        model='nomic-embed-text',              # or your choice
        base_url='http://localhost:11434')

def process_doc(doc_path: pathlib.Path, metadata: dict):
    text = doc_path.read_text()
    for i, chunk in enumerate(splitter.split_text(text)):
        vec = emb.embed_query(chunk)
        payload = {
            "id": f"{metadata['id']}_chunk{i}",
            "values": vec,
            "metadata": metadata
        }
        out = EMB_DIR / f"{uuid.uuid4().hex}.json"
        out.write_text(json.dumps(payload))

# after scraping a mod or override, call:
# process_doc(new_file, metadata)
