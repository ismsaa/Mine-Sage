#!/usr/bin/env python3
import requests
from langchain_ollama import OllamaEmbeddings

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

# Initialize embeddings
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

def semantic_search(query, top_k=5):
    """Perform semantic search on our modpack data"""
    try:
        # Generate embedding for the query
        query_embedding = emb.embed_query(query)
        
        # Search Pinecone
        search_payload = {
            "vector": query_embedding,
            "topK": top_k,
            "includeMetadata": True,
            "includeValues": False
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=search_payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Search failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

def display_results(query, results):
    """Display search results in a readable format"""
    print(f"\n🔍 Query: '{query}'")
    print("=" * 60)
    
    if not results or not results.get('matches'):
        print("No results found.")
        return
    
    for i, match in enumerate(results['matches'], 1):
        metadata = match.get('metadata', {})
        score = match.get('score', 0)
        
        print(f"\n{i}. {match['id']} (Score: {score:.4f})")
        print(f"   Type: {metadata.get('type', 'unknown')}")
        
        if metadata.get('pack_name'):
            print(f"   Pack: {metadata['pack_name']} v{metadata.get('pack_version', '?')}")
        
        if metadata.get('mod_title'):
            print(f"   Mod: {metadata['mod_title']}")
        
        if metadata.get('source'):
            print(f"   Source: {metadata['source']}")
        
        if metadata.get('file_path'):
            print(f"   File: {metadata['file_path']}")

def main():
    print("🚀 Testing Semantic Search on Modpack Data")
    print("=" * 50)
    
    # Test different types of queries
    test_queries = [
        "What mods are in this modpack?",
        "KubeJS configuration scripts",
        "EMI recipe viewer integration",
        "JEI item descriptions and categories",
        "Enigmatica Expert modpack overview",
        "client side mod configuration",
        "material unification scripts"
    ]
    
    for query in test_queries:
        results = semantic_search(query, top_k=3)
        display_results(query, results)
        print("\n" + "-" * 60)
    
    # Interactive search
    print("\n🎯 Interactive Search (type 'quit' to exit)")
    while True:
        try:
            user_query = input("\nEnter your search query: ").strip()
            if user_query.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_query:
                results = semantic_search(user_query, top_k=5)
                display_results(user_query, results)
                
        except KeyboardInterrupt:
            break
    
    print("\n👋 Search testing completed!")

if __name__ == "__main__":
    main()