#!/usr/bin/env python3
import json
import zipfile
import requests
import time
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Dict, List, Set, Optional

# Configuration
PACK_ZIP = "/home/saad/Desktop/Enigmatica9Expert-1.25.0.zip"
OLLAMA_URL = "http://localhost:11434"
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
INDEX = "mods"

# Load API keys from config
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load config.json: {e}")
        return {}

CONFIG = load_config()

# Initialize embeddings
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

# Thread-safe counters
class Counter:
    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.value += 1
            return self.value

class IngestionStats:
    def __init__(self):
        self.new_mods = Counter()
        self.existing_mods = Counter()
        self.failed_mods = Counter()
        self.pack_docs = Counter()
        self.override_docs = Counter()

stats = IngestionStats()

def extract_manifest(zip_path):
    """Extract and parse manifest.json from modpack zip"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        manifest_data = z.read('manifest.json')
        return json.loads(manifest_data)

# Global cache to track processed documents in this session
processed_docs_cache = set()

def get_existing_document_ids() -> Set[str]:
    """Get all existing document IDs from Pinecone (one-time fetch)"""
    try:
        # Query with a dummy vector to get all documents
        search_payload = {
            "vector": [0.0] * 768,
            "topK": 1000,  # Get as many as possible
            "includeMetadata": True
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=search_payload)
        if response.status_code == 200:
            results = response.json()
            matches = results.get('matches', [])
            return {match['id'] for match in matches}
        return set()
    except Exception as e:
        print(f"⚠️  Error fetching existing document IDs: {e}")
        return set()

def check_vector_exists(doc_id: str) -> bool:
    """Check if a vector already exists (using cache)"""
    return doc_id in processed_docs_cache

def upsert_document(doc_id: str, text: str, metadata: dict) -> bool:
    """Upsert a document to Pinecone Local"""
    try:
        # Generate embedding
        embedding = emb.embed_query(text)
        
        # Upsert to Pinecone
        upsert_payload = {
            "vectors": [{
                "id": doc_id,
                "values": embedding,
                "metadata": metadata
            }]
        }
        
        response = requests.post(f"{DATA_HOST}/vectors/upsert", json=upsert_payload)
        return response.status_code == 200
            
    except Exception as e:
        print(f"❌ Error upserting {doc_id}: {e}")
        return False

def fetch_mod_info_curseforge(project_id: str, file_id: str) -> Optional[Dict]:
    """Fetch mod information from CurseForge API"""
    try:
        api_key = CONFIG.get('curseforge_api_key')
        if not api_key:
            return {
                "title": f"CurseForge Mod {project_id}",
                "description": f"CurseForge mod with project ID {project_id}",
                "project_id": project_id,
                "file_id": file_id,
                "version": "unknown",
                "source": "curseforge"
            }
        
        headers = {
            'Accept': 'application/json',
            'x-api-key': api_key
        }
        
        # Get mod info
        mod_response = requests.get(f"https://api.curseforge.com/v1/mods/{project_id}", headers=headers)
        if mod_response.status_code != 200:
            return None
        
        mod_data = mod_response.json()['data']
        
        # Get file info for version
        file_response = requests.get(f"https://api.curseforge.com/v1/mods/{project_id}/files/{file_id}", headers=headers)
        file_version = "unknown"
        minecraft_versions = []
        
        if file_response.status_code == 200:
            file_data = file_response.json()['data']
            file_version = file_data.get('displayName', 'unknown')
            minecraft_versions = file_data.get('gameVersions', [])
        
        return {
            "title": mod_data.get("name", f"CurseForge Mod {project_id}"),
            "description": mod_data.get("summary", ""),
            "project_id": project_id,
            "file_id": file_id,
            "version": file_version,
            "categories": [cat.get("name", "") for cat in mod_data.get("categories", [])],
            "download_count": mod_data.get("downloadCount", 0),
            "minecraft_versions": minecraft_versions,
            "source": "curseforge"
        }
    except Exception as e:
        print(f"⚠️  Error fetching CurseForge info for {project_id}: {e}")
        return None

def create_base_mod_document(mod_info: Dict) -> str:
    """Create a universal base mod document"""
    doc = f"""# {mod_info['title']}

{mod_info['description']}

## Mod Information
- Project ID: {mod_info['project_id']}
- Version: {mod_info['version']}
- Source: {mod_info['source']}
"""
    
    if mod_info.get('categories'):
        doc += f"- Categories: {', '.join(mod_info['categories'])}\n"
    
    if mod_info.get('download_count'):
        doc += f"- Downloads: {mod_info['download_count']:,}\n"
    
    if mod_info.get('minecraft_versions'):
        doc += f"- Minecraft Versions: {', '.join(mod_info['minecraft_versions'])}\n"
    
    doc += f"""
## Description
This mod provides functionality for Minecraft and can be used across different modpacks.
"""
    
    return doc

def create_pack_overview_document(pack_name: str, pack_version: str, mods: List[Dict], minecraft_version: str = "unknown") -> str:
    """Create a pack overview document with mod references"""
    mod_references = [f"mod_{mod['projectID']}_{mod.get('version', 'unknown')}" for mod in mods]
    
    doc = f"""# {pack_name} v{pack_version}

This is a Minecraft modpack containing {len(mods)} mods.

## Pack Information
- Name: {pack_name}
- Version: {pack_version}
- Minecraft Version: {minecraft_version}
- Total Mods: {len(mods)}

## Featured Mods (First 20)
{chr(10).join([f"- Project ID: {mod['projectID']}" for mod in mods[:20]])}
{'...' if len(mods) > 20 else ''}

## Pack Context
This modpack provides a curated experience with carefully selected mods and configurations.
The mods work together to create a cohesive gameplay experience.
"""
    
    return doc

def process_base_mod(mod_data: Dict, pack_name: str, pack_version: str) -> bool:
    """Process a single base mod (check if exists, ingest if new)"""
    project_id = str(mod_data.get("projectID", ""))
    file_id = str(mod_data.get("fileID", ""))
    
    try:
        # Fetch mod info to get version
        mod_info = fetch_mod_info_curseforge(project_id, file_id)
        if not mod_info:
            stats.failed_mods.increment()
            return False
        
        # Create normalized mod ID
        mod_version = mod_info['version'].replace(' ', '_').replace('.', '_')[:20]  # Sanitize version
        base_mod_id = f"mod_{project_id}_v{mod_version}"
        
        # Check if this exact mod version already exists
        if check_vector_exists(base_mod_id):
            stats.existing_mods.increment()
            return True  # Already exists, skip
        
        # Create base mod document
        doc_content = create_base_mod_document(mod_info)
        
        # Create metadata for base mod
        metadata = {
            "type": "base_mod",
            "project_id": project_id,
            "version": mod_info['version'],
            "mod_title": mod_info["title"],
            "source": mod_info["source"],
            "categories": mod_info.get("categories", []),
            "minecraft_versions": mod_info.get("minecraft_versions", [])
        }
        
        # Upsert base mod
        if upsert_document(base_mod_id, doc_content, metadata):
            stats.new_mods.increment()
            return True
        else:
            stats.failed_mods.increment()
            return False
            
    except Exception as e:
        print(f"❌ Error processing base mod {project_id}: {e}")
        stats.failed_mods.increment()
        return False

def extract_kubejs_overrides(zip_path: Path, pack_name: str, pack_version: str) -> List[Dict]:
    """Extract KubeJS configuration overrides from the modpack"""
    overrides = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Look for KubeJS files
            kubejs_files = [f for f in z.namelist() if 'kubejs' in f.lower() and f.endswith('.js')]
            
            for file_path in kubejs_files[:10]:  # Limit for testing
                try:
                    content = z.read(file_path).decode('utf-8')
                    
                    # Create override document
                    override_doc = f"""# KubeJS Override: {file_path}

This is a KubeJS configuration file from {pack_name} v{pack_version}.

## File Information
- Path: {file_path}
- Pack: {pack_name} v{pack_version}
- Type: KubeJS Script

## Configuration Content
```javascript
{content[:1500]}{'...' if len(content) > 1500 else ''}
```

## Purpose
This script customizes mod behavior specifically for this modpack.
"""
                    
                    overrides.append({
                        "id": f"override_{pack_name}_{pack_version}_{file_path.replace('/', '_').replace('.', '_')}",
                        "content": override_doc,
                        "metadata": {
                            "type": "pack_override",
                            "pack_name": pack_name,
                            "pack_version": pack_version,
                            "file_path": file_path,
                            "override_type": "kubejs"
                        }
                    })
                    
                except Exception as e:
                    print(f"⚠️  Could not process {file_path}: {e}")
                    
    except Exception as e:
        print(f"⚠️  Could not extract KubeJS overrides: {e}")
    
    return overrides

def main():
    print("🚀 Starting Normalized Modpack Ingestion")
    print("=" * 60)
    
    # Test connections
    try:
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code != 200:
            print("❌ Pinecone Local not accessible")
            return
        print("✅ Pinecone Local connected")
    except Exception as e:
        print(f"❌ Cannot connect to Pinecone Local: {e}")
        return
    
    # Extract manifest
    try:
        manifest = extract_manifest(PACK_ZIP)
        pack_name = manifest.get("name", "unknown")
        pack_version = manifest.get("version", "0.0.0")
        minecraft_version = manifest.get("minecraft", {}).get("version", "unknown")
        mods = manifest.get("files", [])
        
        print(f"📦 Pack: {pack_name} v{pack_version}")
        print(f"🎮 Minecraft Version: {minecraft_version}")
        print(f"📊 Total mods: {len(mods)}")
        print()
        
        # Ask for confirmation
        response = input(f"⚠️  Process {len(mods)} mods with normalized architecture? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Aborted by user")
            return
        
        print("🔄 Initializing deduplication cache...")
        # Populate cache with existing document IDs
        global processed_docs_cache
        processed_docs_cache = get_existing_document_ids()
        print(f"📋 Found {len(processed_docs_cache)} existing documents in database")
        
        print("🔄 Phase 1: Processing base mods (deduplication enabled)...")
        start_time = time.time()
        
        # Process base mods in parallel
        max_workers = 5
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_mod = {
                executor.submit(process_base_mod, mod, pack_name, pack_version): i
                for i, mod in enumerate(mods, 1)
            }
            
            for future in as_completed(future_to_mod):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Exception in mod processing: {e}")
                
                # Progress update
                total_processed = stats.new_mods.value + stats.existing_mods.value + stats.failed_mods.value
                if total_processed % 25 == 0:
                    print(f"📊 Progress: {total_processed}/{len(mods)} mods processed")
                
                time.sleep(0.1)  # Rate limiting
        
        print(f"✅ Phase 1 Complete - Base mods processed")
        print(f"   🆕 New mods ingested: {stats.new_mods.value}")
        print(f"   ♻️  Existing mods skipped: {stats.existing_mods.value}")
        print(f"   ❌ Failed: {stats.failed_mods.value}")
        print()
        
        # Phase 2: Create pack overview
        print("🔄 Phase 2: Creating pack overview...")
        pack_id = f"pack_{pack_name}_{pack_version}"
        
        if not check_vector_exists(pack_id):
            pack_doc = create_pack_overview_document(pack_name, pack_version, mods, minecraft_version)
            pack_metadata = {
                "type": "pack_overview",
                "pack_name": pack_name,
                "pack_version": pack_version,
                "minecraft_version": minecraft_version,
                "mod_count": len(mods),
                "mod_references": [f"mod_{mod['projectID']}" for mod in mods[:50]]  # Sample references
            }
            
            if upsert_document(pack_id, pack_doc, pack_metadata):
                stats.pack_docs.increment()
                print("✅ Pack overview created")
            else:
                print("❌ Failed to create pack overview")
        else:
            print("♻️  Pack overview already exists")
        
        # Phase 3: Process overrides
        print("🔄 Phase 3: Processing pack-specific overrides...")
        overrides = extract_kubejs_overrides(Path(PACK_ZIP), pack_name, pack_version)
        
        for override in overrides:
            if not check_vector_exists(override["id"]):
                if upsert_document(override["id"], override["content"], override["metadata"]):
                    stats.override_docs.increment()
        
        print(f"✅ Phase 3 Complete - {stats.override_docs.value} overrides processed")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("🎉 Normalized Ingestion Completed!")
        print(f"   🆕 New base mods: {stats.new_mods.value}")
        print(f"   ♻️  Existing mods (skipped): {stats.existing_mods.value}")
        print(f"   📦 Pack documents: {stats.pack_docs.value}")
        print(f"   ⚙️  Override documents: {stats.override_docs.value}")
        print(f"   ❌ Failed: {stats.failed_mods.value}")
        print(f"   ⏱️  Duration: {duration:.1f} seconds")
        print(f"   💾 Storage efficiency: {stats.existing_mods.value}/{len(mods)} mods deduplicated")
        
    except Exception as e:
        print(f"❌ Error processing pack: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()