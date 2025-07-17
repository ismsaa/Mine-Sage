#!/usr/bin/env python3
import json
import zipfile
import requests
import time
from pathlib import Path
from langchain_ollama import OllamaEmbeddings

# Configuration
PACK_ZIP = "/home/saad/Desktop/Enigmatica9Expert-1.25.0.zip"
OLLAMA_URL = "http://localhost:11434"
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
INDEX = "mods"

# API endpoints
MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://api.curseforge.com/v1"

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
            print(f"✅ Upserted: {doc_id}")
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
            print(f"⚠️  No CurseForge API key found in config")
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
        
        response = requests.get(f"{CURSEFORGE_API}/mods/{project_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()['data']
            return {
                "title": data.get("name", f"CurseForge Mod {project_id}"),
                "description": data.get("summary", ""),
                "project_id": project_id,
                "file_id": file_id,
                "categories": [cat.get("name", "") for cat in data.get("categories", [])],
                "download_count": data.get("downloadCount", 0),
                "game_versions": data.get("latestFilesIndexes", []),
                "source": "curseforge"
            }
        else:
            print(f"⚠️  CurseForge API returned {response.status_code} for {project_id}")
            return {
                "title": f"CurseForge Mod {project_id}",
                "description": f"CurseForge mod with project ID {project_id} and file ID {file_id}",
                "project_id": project_id,
                "file_id": file_id,
                "source": "curseforge"
            }
    except Exception as e:
        print(f"⚠️  Could not fetch CurseForge info for {project_id}: {e}")
        return None

def fetch_mod_info_modrinth(project_id):
    """Fetch mod information from Modrinth API"""
    try:
        headers = {}
        token = CONFIG.get('modrinth_token')
        if token:
            headers['Authorization'] = token
        
        response = requests.get(f"{MODRINTH_API}/project/{project_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", "Unknown"),
                "description": data.get("description", ""),
                "project_id": project_id,
                "categories": data.get("categories", []),
                "client_side": data.get("client_side", "unknown"),
                "server_side": data.get("server_side", "unknown"),
                "downloads": data.get("downloads", 0),
                "source": "modrinth"
            }
        else:
            print(f"⚠️  Modrinth API returned {response.status_code} for {project_id}")
            return None
    except Exception as e:
        print(f"⚠️  Could not fetch Modrinth info for {project_id}: {e}")
        return None

def fetch_mod_info(project_id, file_id, pack_source="curseforge"):
    """Fetch mod information using preferred source order"""
    # Since this is a CurseForge modpack, try CurseForge first, then Modrinth
    if pack_source == "curseforge":
        # Try CurseForge first (modpack source)
        mod_info = fetch_mod_info_curseforge(project_id, file_id)
        if mod_info:
            return mod_info
        
        # Fallback to Modrinth
        mod_info = fetch_mod_info_modrinth(project_id)
        if mod_info:
            return mod_info
    else:
        # For other modpacks, try Modrinth first, then CurseForge
        mod_info = fetch_mod_info_modrinth(project_id)
        if mod_info:
            return mod_info
            
        mod_info = fetch_mod_info_curseforge(project_id, file_id)
        if mod_info:
            return mod_info
    
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
    
    if mod_info['source'] == 'modrinth':
        doc += f"""- Categories: {', '.join(mod_info.get('categories', []))}
- Client Side: {mod_info.get('client_side', 'unknown')}
- Server Side: {mod_info.get('server_side', 'unknown')}
- Downloads: {mod_info.get('downloads', 0):,}
"""
    elif mod_info['source'] == 'curseforge':
        doc += f"- File ID: {mod_info.get('file_id', 'unknown')}\n"
    
    doc += f"""
## Pack Context
This mod is included in {pack_name} v{pack_version}.
"""
    
    return doc

def extract_kubejs_overrides(zip_path, pack_name, pack_version):
    """Extract KubeJS configuration overrides from the modpack"""
    overrides = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Look for KubeJS files
            kubejs_files = [f for f in z.namelist() if 'kubejs' in f.lower() and f.endswith('.js')]
            
            for file_path in kubejs_files[:5]:  # Limit to first 5 files for testing
                try:
                    content = z.read(file_path).decode('utf-8')
                    
                    # Create override document
                    override_doc = f"""# KubeJS Override: {file_path}

This is a KubeJS configuration file from {pack_name} v{pack_version}.

## File Path
{file_path}

## Configuration Content
```javascript
{content[:1000]}{'...' if len(content) > 1000 else ''}
```

## Pack Context
This override modifies game behavior in {pack_name} v{pack_version}.
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
    print("🚀 Starting full pack ingestion...")
    
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
        print(f"📊 Total mods: {len(mods)}")
        print()
        
        # Process first 10 mods for testing
        print("🔄 Processing individual mods (first 10)...")
        successful_mods = 0
        
        for i, mod in enumerate(mods[:10]):
            project_id = str(mod.get("projectID", ""))
            file_id = str(mod.get("fileID", ""))
            
            print(f"   Processing mod {i+1}/10: {project_id}")
            
            # Use preferred source order (CurseForge first for this modpack)
            mod_info = fetch_mod_info(project_id, file_id, pack_source="curseforge")
            
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
                        successful_mods += 1
            
            # Small delay to be nice to APIs
            time.sleep(0.5)
        
        print(f"✅ Successfully processed {successful_mods}/10 mods")
        print()
        
        # Extract and process KubeJS overrides
        print("🔄 Processing KubeJS overrides...")
        overrides = extract_kubejs_overrides(PACK_ZIP, pack_name, pack_version)
        
        successful_overrides = 0
        for override in overrides:
            if upsert_document(override["id"], override["content"], override["metadata"]):
                successful_overrides += 1
        
        print(f"✅ Successfully processed {successful_overrides}/{len(overrides)} overrides")
        print()
        
        print("🎉 Full pack ingestion completed!")
        print(f"   📊 Mods processed: {successful_mods}")
        print(f"   ⚙️  Overrides processed: {successful_overrides}")
        
    except Exception as e:
        print(f"❌ Error processing pack: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()