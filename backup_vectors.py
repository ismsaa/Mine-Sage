#!/usr/bin/env python3
"""
Backup script for Pinecone Local vector data

Since Pinecone Local is RAM-only, this script exports all vectors
to a JSON file for persistence across restarts.
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
BACKUP_DIR = Path("./data/backups")
INDEX_NAME = "mods"

def ensure_backup_dir():
    """Create backup directory if it doesn't exist"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def get_all_vectors():
    """Retrieve all vectors from Pinecone Local"""
    try:
        # Get index info first
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code != 200:
            print(f"❌ Failed to get indexes: {response.status_code}")
            return None
        
        indexes = response.json()
        mods_index = None
        for idx in indexes.get('indexes', []):
            if idx['name'] == INDEX_NAME:
                mods_index = idx
                break
        
        if not mods_index:
            print(f"❌ Index '{INDEX_NAME}' not found")
            return None
        
        print(f"✅ Found index: {INDEX_NAME} (dimension: {mods_index['dimension']})")
        
        # Query with a dummy vector to get all vectors
        # Note: This is a limitation of Pinecone Local - we can't directly export all vectors
        # We'll use a broad search to get as many as possible
        dummy_vector = [0.0] * mods_index['dimension']
        
        query_payload = {
            "vector": dummy_vector,
            "topK": 10000,  # Try to get as many as possible
            "includeMetadata": True,
            "includeValues": True
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=query_payload)
        if response.status_code == 200:
            result = response.json()
            vectors = result.get('matches', [])
            print(f"✅ Retrieved {len(vectors)} vectors")
            return vectors
        else:
            print(f"❌ Failed to query vectors: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving vectors: {e}")
        return None

def save_backup(vectors, metadata=None):
    """Save vectors to backup file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"vectors_backup_{timestamp}.json"
        
        backup_data = {
            "timestamp": timestamp,
            "index_name": INDEX_NAME,
            "vector_count": len(vectors),
            "metadata": metadata or {},
            "vectors": vectors
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✅ Backup saved: {backup_file}")
        print(f"   📊 Vectors: {len(vectors)}")
        print(f"   📅 Timestamp: {timestamp}")
        
        # Also create a "latest" symlink for easy access
        latest_link = BACKUP_DIR / "latest_backup.json"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(backup_file.name)
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Error saving backup: {e}")
        return None

def get_index_stats():
    """Get additional index statistics for metadata"""
    try:
        response = requests.get(f"{DATA_HOST}/describe_index_stats")
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def main():
    print("🚀 Starting Vector Backup")
    print("=" * 50)
    
    # Ensure backup directory exists
    ensure_backup_dir()
    
    # Get all vectors
    print("📥 Retrieving vectors from Pinecone Local...")
    vectors = get_all_vectors()
    
    if not vectors:
        print("❌ No vectors to backup")
        return
    
    # Get additional metadata
    print("📊 Getting index statistics...")
    stats = get_index_stats()
    
    # Save backup
    print("💾 Saving backup...")
    backup_file = save_backup(vectors, stats)
    
    if backup_file:
        print("\n🎉 Backup completed successfully!")
        print(f"📁 Backup location: {backup_file}")
        print(f"📈 Total vectors backed up: {len(vectors)}")
        
        # Show some sample vector info
        if vectors:
            print("\n📋 Sample vectors:")
            for i, vector in enumerate(vectors[:3], 1):
                metadata = vector.get('metadata', {})
                doc_type = metadata.get('type', 'unknown')
                title = metadata.get('mod_title', metadata.get('pack_name', 'Unknown'))
                score = vector.get('score', 0) or 0
                print(f"   {i}. {title} ({doc_type}) - Score: {score:.3f}")
    else:
        print("❌ Backup failed")

if __name__ == "__main__":
    main()