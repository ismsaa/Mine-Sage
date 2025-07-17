#!/usr/bin/env python3
import json
import zipfile
import requests
import time
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

successful_mods = Counter()
failed_mods = Counter()

def extract_manifest(zip_path):
    """Extract and parse manifest.json from modpack zip"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        manifest_data = z.read('manifest.json')
        return json.loads(manifest_data)

def upsert_document(doc_id, text, metadata):
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
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Failed to upsert {doc_id}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error upserting {doc_id}: {e}")
        return False

def fetch_mod_info_curseforge(project_id, file_id):
    """Fetch mod information from CurseForge API"""
    try:
        api_key = CONFIG.get('curseforge_api_key')
        if not api_key:
            return {
                "title": f"CurseForge Mod {project_id}",
                "description": f"CurseForge mod with project ID {project_id} and file ID {file_id}",
                "project_id": project_id,
                "file_id": file_id,
                "source": "curseforge"
            }
        
        headers = {
            'Accept': 'application/json',
            'x-api-key': api_key
        }
        
        response = requests.get(f"https://api.curseforge.com/v1/mods/{project_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()['data']
            return {
                "title": data.get("name", f"CurseForge Mod {project_id}"),
                "description": data.get("summary", ""),
                "project_id": project_id,
                "file_id": file_id,
                "categories": [cat.get("name", "") for cat in data.get("categories", [])],
                "download_count": data.get("downloadCount", 0),
                "source": "curseforge"
            }
        else:
            return {
                "title": f"CurseForge Mod {project_id}",
                "description": f"CurseForge mod with project ID {project_id} and file ID {file_id}",
                "project_id": project_id,
                "file_id": file_id,
                "source": "curseforge"
            }
    except Exception as e:
        print(f"⚠️  Error fetching CurseForge info for {project_id}: {e}")
        return None

def create_mod_document(mod_info, pack_name, pack_version):
    """Create a text document for a mod"""
    if not mod_info:
        return None
        
    doc = f"""# {mod_info['title']}

{mod_info['description']}

## Mod Information
- Project ID: {mod_info['project_id']}
- Source: {mod_info['source']}
"""
    
    if mod_info['source'] == 'curseforge':
        doc += f"- File ID: {mod_info.get('file_id', 'unknown')}\n"
        if mod_info.get('categories'):
            doc += f"- Categories: {', '.join(mod_info.get('categories', []))}\n"
        if mod_info.get('download_count'):
            doc += f"- Downloads: {mod_info.get('download_count', 0):,}\n"
    
    doc += f"""
## Pack Context
This mod is included in {pack_name} v{pack_version}.
"""
    
    return doc

def process_single_mod(mod_data, pack_name, pack_version, mod_index, total_mods):
    """Process a single mod (for threading)"""
    project_id = str(mod_data.get("projectID", ""))
    file_id = str(mod_data.get("fileID", ""))
    
    try:
        # Fetch mod info
        mod_info = fetch_mod_info_curseforge(project_id, file_id)
        
        if mod_info:
            # Create document
            doc_content = create_mod_document(mod_info, pack_name, pack_version)
            if doc_content:
                # Upsert to Pinecone
                doc_id = f"mod_{pack_name}_{pack_version}_{project_id}"
                metadata = {
                    "type": "base_mod",
                    "pack_name": pack_name,
                    "pack_version": pack_version,
                    "project_id": project_id,
                    "mod_title": mod_info["title"],
                    "source": mod_info["source"]
                }
                
                if upsert_document(doc_id, doc_content, metadata):
                    count = successful_mods.increment()
                    if count % 10 == 0:  # Progress update every 10 mods
                        print(f"✅ Progress: {count}/{total_mods} mods processed")
                    return True
        
        failed_mods.increment()
        return False
        
    except Exception as e:
        print(f"❌ Error processing mod {project_id}: {e}")
        failed_mods.increment()
        return False

def main():
    print("🚀 Starting Full-Scale Modpack Ingestion")
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
        mods = manifest.get("files", [])
        
        print(f"📦 Pack: {pack_name} v{pack_version}")
        print(f"📊 Total mods to process: {len(mods)}")
        print()
        
        # Ask for confirmation
        response = input(f"⚠️  This will process {len(mods)} mods. Continue? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Aborted by user")
            return
        
        print("🔄 Starting parallel mod processing...")
        start_time = time.time()
        
        # Process mods in parallel
        max_workers = 5  # Limit concurrent requests to be nice to APIs
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all mod processing tasks
            future_to_mod = {
                executor.submit(process_single_mod, mod, pack_name, pack_version, i, len(mods)): i
                for i, mod in enumerate(mods, 1)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_mod):
                mod_index = future_to_mod[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Exception in mod {mod_index}: {e}")
                
                # Small delay to avoid overwhelming APIs
                time.sleep(0.1)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("🎉 Full-Scale Ingestion Completed!")
        print(f"   ✅ Successfully processed: {successful_mods.value}")
        print(f"   ❌ Failed: {failed_mods.value}")
        print(f"   📊 Success rate: {successful_mods.value/(successful_mods.value + failed_mods.value)*100:.1f}%")
        print(f"   ⏱️  Duration: {duration:.1f} seconds")
        print(f"   🚀 Rate: {successful_mods.value/duration:.1f} mods/second")
        
    except Exception as e:
        print(f"❌ Error processing pack: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()