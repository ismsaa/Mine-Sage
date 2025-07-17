#!/usr/bin/env python3
import requests
import json

# Configuration
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
INDEX = "mods"

def show_index_info():
    print("📊 Pinecone Local Index Information")
    print("=" * 50)
    
    try:
        # Get index information
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code == 200:
            indexes = response.json()
            
            # Find our index
            mods_index = None
            for idx in indexes.get('indexes', []):
                if idx['name'] == INDEX:
                    mods_index = idx
                    break
            
            if mods_index:
                print(f"📦 Index: {mods_index['name']}")
                print(f"📏 Dimensions: {mods_index['dimension']}")
                print(f"📐 Metric: {mods_index['metric']}")
                print(f"🌐 Host: {mods_index['host']}")
                print(f"✅ Status: {mods_index['status']['state']}")
                print()
                
                # Get index stats (if available)
                try:
                    stats_response = requests.get(f"{DATA_HOST}/describe_index_stats")
                    if stats_response.status_code == 200:
                        stats = stats_response.json()
                        print("📈 Index Statistics:")
                        print(f"   Total vectors: {stats.get('totalVectorCount', 'Unknown')}")
                        print(f"   Dimension: {stats.get('dimension', 'Unknown')}")
                        if 'namespaces' in stats:
                            print(f"   Namespaces: {len(stats['namespaces'])}")
                        print()
                except Exception as e:
                    print(f"⚠️  Could not get index stats: {e}")
                    print()
                
                # Try to query for some sample vectors
                print("🔍 Sample Vectors:")
                try:
                    # Query with a random vector to get some results
                    query_payload = {
                        "vector": [0.1] * mods_index['dimension'],
                        "topK": 5,
                        "includeMetadata": True,
                        "includeValues": False
                    }
                    
                    response = requests.post(f"{DATA_HOST}/query", json=query_payload)
                    if response.status_code == 200:
                        result = response.json()
                        matches = result.get('matches', [])
                        
                        if matches:
                            for i, match in enumerate(matches, 1):
                                print(f"   {i}. ID: {match['id']}")
                                print(f"      Score: {match['score']:.4f}")
                                if 'metadata' in match:
                                    metadata = match['metadata']
                                    print(f"      Type: {metadata.get('type', 'Unknown')}")
                                    if metadata.get('pack_name'):
                                        print(f"      Pack: {metadata['pack_name']} v{metadata.get('pack_version', '?')}")
                                    if metadata.get('mod_count'):
                                        print(f"      Mod Count: {metadata['mod_count']}")
                                print()
                        else:
                            print("   No vectors found in index")
                    else:
                        print(f"   ❌ Query failed: {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Error querying vectors: {e}")
                    
            else:
                print(f"❌ Index '{INDEX}' not found")
                print("Available indexes:")
                for idx in indexes.get('indexes', []):
                    print(f"   - {idx['name']}")
        else:
            print(f"❌ Failed to get index info: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error connecting to Pinecone Local: {e}")

if __name__ == "__main__":
    show_index_info()