#!/usr/bin/env python3
# ingest_pack.py

import argparse
import json
import os
import zipfile
from pathlib import Path

import pinecone
from pinecone import Pinecone as PineconeClient
import requests
from bs4 import BeautifulSoup  # HTML parsing for overrides
from langchain_ollama import OllamaEmbeddings  # updated Ollama embeddings
from langchain_community.vectorstores import Pinecone  # updated Pinecone vectorstore

# ─── Configuration ─────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent
RAW_DIR     = ROOT_DIR / "data"
MODS_DIR    = RAW_DIR / "mods"
PACKS_DIR   = RAW_DIR / "modpacks"
OVRD_DIR    = RAW_DIR / "overrides"

EMB_MODEL   = "nomic-embed-text"
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PC_INDEX    = os.getenv("PINECONE_INDEX", "mods")
PC_HOST     = os.getenv("PINECONE_HOST", "http://localhost:5081")

pc = PineconeClient(
    api_key="local-dev",         # dummy key for local
    environment="local",         # must match local env
    host=PC_HOST                 # e.g. http://localhost:5081
)  # pinecone.init() is deprecated

# ── Create index if missing ────────────────────────────────────
if PC_INDEX not in pc.list_indexes().names():
    pc.create_index(
        name=PC_INDEX,
        dimension=768,
        metric="cosine"
    )

# ── Wrap existing index for LangChain ─────────────────────────
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
vect = Pinecone.from_existing_index(
    index_name=PC_INDEX,
    embedding=emb
)  # host/API key already configured in pc

MODRINTH_API = "https://api.modrinth.com/v2"
CF_SEARCH    = "https://addons-ecs.forgesvc.net/api/v2/mods/search"

# ─── Utility Functions ─────────────────────────────────────────

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str):
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    print(f"[WRITE] {path}")

def upsert_doc(path: Path, metadata: dict):
    text = path.read_text(encoding="utf-8")
    vect.add_texts([text], metadatas=[metadata], ids=[str(path)])
    print(f"[UPSERT] {path}")

# ─── ZIP Pack Parsing ──────────────────────────────────────────

def parse_zip_pack(zip_path: Path):
    tmp = RAW_DIR / "tmp_pack"
    if tmp.exists():
        for f in tmp.iterdir(): f.unlink()
    ensure_dir(tmp)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmp)  # extractall via zipfile module :contentReference[oaicite:7]{index=7}
    manifest = json.loads((tmp/"manifest.json").read_text(encoding="utf-8"))
    pack_meta = {
        "id": manifest.get("name","localpack"),
        "version": manifest.get("version","0.0.0"),
        "source": "zip"
    }
    mods = [{"slug": f["projectID"], "version": str(f["fileID"])} for f in manifest["files"]]
    return mods, pack_meta, tmp

# ─── Remote Pack Fetching ──────────────────────────────────────

def fetch_pack_via_api(slug: str):
    r = requests.get(f"{MODRINTH_API}/modpack/{slug}/versions")
    if r.ok:
        v = r.json()[0]
        pack_meta = {"id":slug, "version":v["version_number"], "source":"modrinth"}
        mods = [{"slug":m["project_id"], "version":m["file_id"]} for m in v["projects"]]
        return mods, pack_meta, None
    cf = requests.get(CF_SEARCH, params={"gameId":432, "searchFilter":slug})
    cf.raise_for_status()
    data = cf.json()["data"][0]
    # Further CF calls omitted for brevity
    return [], {}, None

# ─── Base‐Mod Document Handling ────────────────────────────────

def fetch_or_load_mod_doc(mod: dict):
    md_path = MODS_DIR / mod["slug"] / f"{mod['version']}.md"
    if not md_path.exists():
        r = requests.get(f"{MODRINTH_API}/project/{mod['slug']}")
        r.raise_for_status()
        data = r.json()
        content = f"# {data.get('title','')}\n\n{data.get('description','')}\n"
        write_file(md_path, content)
    return md_path

# ─── Pack Overview Writing ─────────────────────────────────────

def write_pack_overview(pack_meta: dict, mods: list):
    out = PACKS_DIR / pack_meta["id"] / pack_meta["version"] / "overview.md"
    lines = [
        f"# {pack_meta['id']} v{pack_meta['version']}\n",
        f"Source: {pack_meta['source']}\n",
        "## Mods included:\n"
    ] + [f"- {m['slug']} @ {m['version']}" for m in mods]
    write_file(out, "\n".join(lines))
    return out

# ─── Override Extraction ───────────────────────────────────────

def generate_and_write_overrides(tmp_dir: Path, pack_meta: dict, mods: list):
    paths = []
    if not tmp_dir:
        return paths
    # Example: parse all .js under kubejs for "removeRecipe"
    for js in (tmp_dir/"kubejs").rglob("*.js"):
        soup = BeautifulSoup(js.read_text(encoding="utf-8"), "html.parser")  # BeautifulSoup 4 parsing :contentReference[oaicite:8]{index=8}
        text = soup.get_text()
        for mod in mods:
            if "removeRecipe" in text and mod["slug"] in text:
                out = OVRD_DIR / pack_meta["id"] / pack_meta["version"] / f"{mod['slug']}.json"
                write_file(out, json.dumps({"mod":mod["slug"], "disabled":True}, indent=2))
                paths.append(out)
    return paths

# ─── Main Entry Point ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest Minecraft modpack data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip",  help="Path to local modpack ZIP")
    group.add_argument("--pack", help="Slug of remote modpack")
    args = parser.parse_args()

    if args.zip:
        mods, pack_meta, tmp = parse_zip_pack(Path(args.zip))
    else:
        mods, pack_meta, tmp = fetch_pack_via_api(args.pack)

    for mod in mods:
        mdpath = fetch_or_load_mod_doc(mod)
        upsert_doc(mdpath, {**mod, "type":"base_mod"})

    ov = write_pack_overview(pack_meta, mods)
    upsert_doc(ov, {**pack_meta, "type":"pack_overview"})

    overrides = generate_and_write_overrides(tmp, pack_meta, mods)
    for p in overrides:
        upsert_doc(p, {**pack_meta, "type":"pack_override", "mod":p.stem})

    print("✅ Ingestion complete!")

if __name__ == "__main__":
    main()
