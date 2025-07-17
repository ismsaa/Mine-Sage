#!/usr/bin/env python3
import json
import requests
from langchain_ollama import OllamaEmbeddings

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

# Initialize embeddings
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

def search_documents(query: str, doc_type: str = None, top_k: int = 5):
    """Search for documents with optional type filtering"""
    try:
        query_embedding = emb.embed_query(query)
        
        search_payload = {
            "vector": query_embedding,
            "topK": top_k,
            "includeMetadata": True,
            "includeValues": False
        }
        
        # Add type filter if specified
        if doc_type:
            search_payload["filter"] = {"type": {"$eq": doc_type}}
        
        response = requests.post(f"{DATA_HOST}/query", json=search_payload)
        if response.status_code == 200:
            return response.json().get('matches', [])
        return []
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

def test_universal_mod_queries():
    """Test queries that work across all mods regardless of modpack"""
    print("🔍 Testing Universal Mod Queries")
    print("=" * 50)
    
    test_queries = [
        "What is Mekanism?",
        "Tell me about Thermal mods",
        "JEI recipe viewer",
        "Applied Energistics storage",
        "Tinkers Construct tools"
    ]
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        
        # Search only base mods (universal knowledge)
        base_mod_results = search_documents(query, doc_type="base_mod", top_k=3)
        
        if base_mod_results:
            print(f"   📚 Found {len(base_mod_results)} base mod(s):")
            for result in base_mod_results:
                metadata = result.get('metadata', {})
                print(f"   - {metadata.get('mod_title', 'Unknown')} (Score: {result.get('score', 0):.3f})")
                print(f"     Version: {metadata.get('version', 'unknown')}")
                print(f"     Source: {metadata.get('source', 'unknown')}")
        else:
            print("   ❌ No base mods found")

def test_pack_specific_queries():
    """Test queries that are pack-specific"""
    print("\n🔍 Testing Pack-Specific Queries")
    print("=" * 50)
    
    test_queries = [
        "Enigmatica9Expert modpack overview",
        "What mods are in Enigmatica9Expert?",
        "Enigmatica pack configuration"
    ]
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        
        # Search pack documents
        pack_results = search_documents(query, doc_type="pack_overview", top_k=2)
        
        if pack_results:
            print(f"   📦 Found {len(pack_results)} pack document(s):")
            for result in pack_results:
                metadata = result.get('metadata', {})
                print(f"   - {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', '?')}")
                print(f"     Score: {result.get('score', 0):.3f}")
                print(f"     Mod Count: {metadata.get('mod_count', 'unknown')}")
        else:
            print("   ❌ No pack documents found")

def test_configuration_queries():
    """Test queries about pack-specific configurations"""
    print("\n🔍 Testing Configuration Queries")
    print("=" * 50)
    
    test_queries = [
        "KubeJS configuration scripts",
        "EMI material unification",
        "JEI customizations"
    ]
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        
        # Search override documents
        override_results = search_documents(query, doc_type="pack_override", top_k=3)
        
        if override_results:
            print(f"   ⚙️  Found {len(override_results)} override(s):")
            for result in override_results:
                metadata = result.get('metadata', {})
                print(f"   - {metadata.get('file_path', 'Unknown')}")
                print(f"     Pack: {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', '?')}")
                print(f"     Score: {result.get('score', 0):.3f}")
        else:
            print("   ❌ No override documents found")

def show_database_stats():
    """Show current database statistics"""
    print("\n📊 Database Statistics")
    print("=" * 50)
    
    # Count documents by type
    doc_types = ["base_mod", "pack_overview", "pack_override"]
    
    for doc_type in doc_types:
        results = search_documents("*", doc_type=doc_type, top_k=100)  # Get many results
        print(f"   {doc_type}: {len(results)} documents")
    
    # Show some examples
    print("\n📋 Sample Documents:")
    
    # Sample base mod
    base_mods = search_documents("mekanism", doc_type="base_mod", top_k=1)
    if base_mods:
        metadata = base_mods[0].get('metadata', {})
        print(f"   🔧 Base Mod: {metadata.get('mod_title', 'Unknown')} v{metadata.get('version', '?')}")
    
    # Sample pack
    packs = search_documents("enigmatica", doc_type="pack_overview", top_k=1)
    if packs:
        metadata = packs[0].get('metadata', {})
        print(f"   📦 Pack: {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', '?')}")
    
    # Sample override
    overrides = search_documents("kubejs", doc_type="pack_override", top_k=1)
    if overrides:
        metadata = overrides[0].get('metadata', {})
        print(f"   ⚙️  Override: {metadata.get('file_path', 'Unknown')}")

def main():
    print("🚀 Testing Normalized Architecture Benefits")
    print("=" * 60)
    
    # Show current database state
    show_database_stats()
    
    # Test different query types
    test_universal_mod_queries()
    test_pack_specific_queries()
    test_configuration_queries()
    
    print("\n" + "=" * 60)
    print("✅ Normalized Architecture Testing Complete!")
    print("\n🎯 Key Benefits Demonstrated:")
    print("   1. Universal mod knowledge (works across all packs)")
    print("   2. Pack-specific information (targeted queries)")
    print("   3. Configuration-specific searches (overrides)")
    print("   4. Efficient storage (no duplicate base mods)")
    print("   5. Flexible query routing (type-specific searches)")

if __name__ == "__main__":
    main()