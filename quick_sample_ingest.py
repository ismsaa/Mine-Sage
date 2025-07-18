#!/usr/bin/env python3
import requests
from langchain_ollama import OllamaEmbeddings

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

# Initialize embeddings
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

def upsert_document(doc_id, text, metadata):
    """Upsert a document to Pinecone Local"""
    try:
        embedding = emb.embed_query(text)
        
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

def main():
    print("🚀 Quick Sample Data Ingestion")
    print("=" * 40)
    
    # Sample mod documents
    sample_mods = [
        {
            "id": "mod_mekanism_v10_3_9",
            "text": """# Mekanism

Mekanism is a comprehensive tech mod that adds advanced machinery, energy systems, and automation to Minecraft.

## Features
- Advanced energy generation and storage
- Complex machinery for ore processing
- Chemical processing systems
- Digital mining systems
- Jetpacks and other equipment

## Categories
- Technology
- Energy
- Automation
- Industrial

This mod is essential for tech-focused modpacks and provides extensive automation capabilities.""",
            "metadata": {
                "type": "base_mod",
                "mod_title": "Mekanism",
                "project_id": "268560",
                "version": "10.3.9",
                "source": "curseforge",
                "categories": ["technology", "energy", "automation"]
            }
        },
        {
            "id": "mod_thermal_expansion_v10_3_0",
            "text": """# Thermal Expansion

Thermal Expansion is a tech mod focused on machines, energy, and automation with a steampunk aesthetic.

## Features
- Steam-powered machinery
- Energy conduits and storage
- Automated crafting systems
- Resource processing
- Redstone integration

## Categories
- Technology
- Energy
- Automation
- Steampunk

This mod provides a different approach to automation compared to other tech mods, with unique mechanics and aesthetics.""",
            "metadata": {
                "type": "base_mod",
                "mod_title": "Thermal Expansion",
                "project_id": "69163",
                "version": "10.3.0",
                "source": "curseforge",
                "categories": ["technology", "energy", "steampunk"]
            }
        },
        {
            "id": "mod_applied_energistics_v12_9_9",
            "text": """# Applied Energistics 2

Applied Energistics 2 (AE2) is a storage and automation mod that revolutionizes item management in Minecraft.

## Features
- Digital storage networks
- Automated crafting systems
- Spatial storage
- Network-based item transport
- Advanced terminals and interfaces

## Categories
- Storage
- Automation
- Technology
- Networks

AE2 is considered one of the most sophisticated storage mods available, offering unparalleled organization and automation capabilities.""",
            "metadata": {
                "type": "base_mod",
                "mod_title": "Applied Energistics 2",
                "project_id": "223794",
                "version": "12.9.9",
                "source": "curseforge",
                "categories": ["storage", "automation", "technology"]
            }
        },
        {
            "id": "override_enigmatica_mekanism_config",
            "text": """# KubeJS Override: Mekanism Configuration

This configuration file customizes Mekanism behavior in Enigmatica9Expert.

## File: overrides/kubejs/server_scripts/mekanism_recipes.js

```javascript
// Disable certain Mekanism recipes for balance
ServerEvents.recipes(event => {
    // Remove digital miner recipe - too powerful early game
    event.remove({id: 'mekanism:digital_miner'})
    
    // Modify enrichment chamber recipes
    event.custom({
        type: 'mekanism:enriching',
        input: {ingredient: {item: 'minecraft:iron_ore'}},
        output: {item: 'mekanism:dust_iron', count: 3}
    })
})
```

## Purpose
This override balances Mekanism for the expert pack progression.""",
            "metadata": {
                "type": "pack_override",
                "pack_name": "Enigmatica9Expert",
                "pack_version": "1.25.0",
                "target_mod": "mekanism",
                "override_type": "kubejs_recipe",
                "file_path": "overrides/kubejs/server_scripts/mekanism_recipes.js"
            }
        }
    ]
    
    # Ingest sample data
    successful = 0
    for mod in sample_mods:
        if upsert_document(mod["id"], mod["text"], mod["metadata"]):
            successful += 1
    
    print(f"\n✅ Successfully ingested {successful}/{len(sample_mods)} documents")
    print("🎯 Ready for OpenWebUI testing!")

if __name__ == "__main__":
    main()