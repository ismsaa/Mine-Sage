#!/usr/bin/env python3
import json
import zipfile
import requests
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from pinecone.grpc import PineconeGRPC

# Configuration
PACK_ZIP = "/home/saad/Desktop/Enigmatica9Expert-1.25.0.zip"
PINECONE_HOST = "localhost:5081"
OLLAMA_URL = "http://localhost:11434"

# Initialize clients
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
pc = PineconeGRPC(api_key="dev", host=PINECONE_HOST)
index = pc.Index("mods")

def extract_manifest(zip_path):
    """Extract and parse manifest.json from modpack zip"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        manifest_data = z.read('manifest.json')
        return json.loads(manifest_data)

def upsert_to_pinecone(doc_id, text, metadata):
    """Generate embedding and upsert to Pinecone Local"""
    try:
        # Generate embedding
        embedding = emb.embed_query(text)
        
        # Upsert to Pinecone Local via gRPC
        index.upsert(vectors=[{
            "id": doc_id,
            "values": embedding,
            "metadata": metadata
        }])
        
        print(f"✅ Upserted: {doc_id}")
        return True
            
    except Exception as e:
        print(f"❌ Error upserting {doc_id}: {e}")
        return False

def main():
    print("🚀 Starting simple ingestion test...")
    
    # Check if Ollama is running
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code != 200:
            print("❌ Ollama not running or not accessible")
            return
        print("✅ Ollama is running")
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return
    
    # Check if Pinecone Local is running
    try:
        indexes = pc.list_indexes()
        print("✅ Pinecone Local is running")
    except Exception as e:
        print(f"❌ Cannot connect to Pinecone Local: {e}")
        return
    
    # Extract manifest
    try:
        manifest = extract_manifest(PACK_ZIP)
        pack_name = manifest.get("name", "unknown")
        pack_version = manifest.get("version", "0.0.0")
        mod_count = len(manifest.get("files", []))
        
        print(f"📦 Pack: {pack_name} v{pack_version}")
        print(f"📊 Mods: {mod_count}")
        
        # Create pack overview document
        overview_text = f"""# {pack_name} v{pack_version}

This is a Minecraft modpack containing {mod_count} mods.

## Pack Information
- Name: {pack_name}
- Version: {pack_version}
- Minecraft Version: {manifest.get('minecraft', {}).get('version', 'unknown')}
- Mod Loader: {manifest.get('minecraft', {}).get('modLoaders', [{}])[0].get('id', 'unknown')}

## Mod List
{chr(10).join([f"- Mod ID: {mod['projectID']}, File ID: {mod['fileID']}" for mod in manifest.get('files', [])[:10]])}
{'...' if mod_count > 10 else ''}
"""
        
        # Upsert pack overview
        success = upsert_to_pinecone(
            f"pack_{pack_name}_{pack_version}",
            overview_text,
            {
                "type": "pack_overview",
                "pack_name": pack_name,
                "pack_version": pack_version,
                "mod_count": mod_count
            }
        )
        
        if success:
            print("🎉 Simple ingestion test completed successfully!")
        else:
            print("❌ Ingestion test failed")
            
    except Exception as e:
        print(f"❌ Error processing pack: {e}")

if __name__ == "__main__":
    main()