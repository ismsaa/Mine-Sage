#!/usr/bin/env python3
import json
import zipfile
import os
import requests
from pathlib import Path
from langchain_ollama import OllamaEmbeddings

# Configuration - using exact same HTTP pattern as UpsertTest.py
PACK_ZIP = "/home/saad/Desktop/Enigmatica9Expert-1.25.0.zip"
OLLAMA_URL = "http://localhost:11434"
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
INDEX = "mods"

# Initialize embeddings
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

def extract_manifest(zip_path):
    """Extract and parse manifest.json from modpack zip"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        manifest_data = z.read('manifest.json')
        return json.loads(manifest_data)

def main():
    print("🚀 Starting working ingestion test...")
    
    # Test basic Pinecone connection first (like UpsertTest.py)
    try:
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code == 200:
            print("✅ Pinecone connection working")
        else:
            print(f"❌ Pinecone connection failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Pinecone connection failed: {e}")
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

## First 10 Mods
{chr(10).join([f"- Mod ID: {mod['projectID']}, File ID: {mod['fileID']}" for mod in manifest.get('files', [])[:10]])}
{'...' if mod_count > 10 else ''}
"""
        
        print("🔄 Generating embedding...")
        # Generate embedding using Ollama
        embedding = emb.embed_query(overview_text)
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        
        # Upsert to Pinecone (exactly like UpsertTest.py)
        doc_id = f"pack_{pack_name}_{pack_version}"
        metadata = {
            "type": "pack_overview",
            "pack_name": pack_name,
            "pack_version": pack_version,
            "mod_count": mod_count
        }
        
        print("🔄 Upserting to Pinecone...")
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
            print(f"   Response: {response.text}")
        else:
            print(f"❌ Upsert failed: {response.status_code} - {response.text}")
            return
        
        # Test query to verify it worked
        print("🔄 Testing query...")
        query_payload = {
            "vector": embedding[:768],  # Ensure correct dimension
            "topK": 1,
            "includeMetadata": True
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=query_payload)
        if response.status_code == 200:
            result = response.json()
            if result.get("matches"):
                match = result["matches"][0]
                print(f"✅ Query successful! Found: {match['id']} (score: {match['score']:.4f})")
                print(f"   Metadata: {match.get('metadata', {})}")
            else:
                print("❌ No matches found in query")
        else:
            print(f"❌ Query failed: {response.status_code} - {response.text}")
        
        print("🎉 Ingestion test completed successfully!")
            
    except Exception as e:
        print(f"❌ Error processing pack: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()