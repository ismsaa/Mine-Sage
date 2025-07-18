#!/usr/bin/env python3
"""
Restore script for Pinecone Local vector data

This script restores vectors from a backup JSON file back into Pinecone Local.
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime

# Configuration
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
BACKUP_DIR = Path("./data/backups")
INDEX_NAME = "mods"

def list_backups():
    """List available backup files"""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for backup_file in BACKUP_DIR.glob("vectors_backup_*.json"):
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)
                backups.append({
                    "file": backup_file,
                    "timestamp": data.get("timestamp", "unknown"),
                    "vector_count": data.get("vector_count", 0),
                    "index_name": data.get("index_name", "unknown")
                })
        except Exception as e:
            print(f"⚠️  Could not read backup {backup_file}: {e}")
    
    return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

def create_index_if_missing():
    """Create the index if it doesn't exist"""
    try:
        # Check if index exists
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code != 200:
            print(f"❌ Failed to check indexes: {response.status_code}")
            return False
        
        indexes = response.json()
        index_exists = any(idx['name'] == INDEX_NAME for idx in indexes.get('indexes', []))
        
        if not index_exists:
            print(f"📝 Creating index: {INDEX_NAME}")
            create_payload = {
                "name": INDEX_NAME,
                "dimension": 768,  # Standard dimension for our embeddings
                "metric": "cosine",
                "spec": {
                    "serverless": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    }
                }
            }
            
            response = requests.post(f"{CONTROL_HOST}/indexes", json=create_payload)
            if response.status_code in [200, 201]:
                print(f"✅ Index created successfully")
                time.sleep(2)  # Wait for index to be ready
                return True
            else:
                print(f"❌ Failed to create index: {response.status_code} - {response.text}")
                return False
        else:
            print(f"✅ Index {INDEX_NAME} already exists")
            return True
            
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False

def restore_vectors(backup_file):
    """Restore vectors from backup file"""
    try:
        print(f"📥 Loading backup: {backup_file}")
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        vectors = backup_data.get("vectors", [])
        if not vectors:
            print("❌ No vectors found in backup")
            return False
        
        print(f"📊 Backup info:")
        print(f"   📅 Timestamp: {backup_data.get('timestamp', 'unknown')}")
        print(f"   📈 Vector count: {len(vectors)}")
        print(f"   🎯 Target index: {backup_data.get('index_name', INDEX_NAME)}")
        
        # Restore vectors in batches
        batch_size = 100
        successful = 0
        failed = 0
        
        print(f"🔄 Restoring vectors in batches of {batch_size}...")
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            
            # Prepare batch for upsert
            upsert_vectors = []
            for vector in batch:
                upsert_vectors.append({
                    "id": vector["id"],
                    "values": vector["values"],
                    "metadata": vector.get("metadata", {})
                })
            
            # Upsert batch
            upsert_payload = {"vectors": upsert_vectors}
            response = requests.post(f"{DATA_HOST}/vectors/upsert", json=upsert_payload)
            
            if response.status_code == 200:
                result = response.json()
                batch_count = result.get("upsertedCount", len(upsert_vectors))
                successful += batch_count
                print(f"   ✅ Batch {i//batch_size + 1}: {batch_count} vectors")
            else:
                failed += len(upsert_vectors)
                print(f"   ❌ Batch {i//batch_size + 1} failed: {response.status_code}")
            
            # Small delay between batches
            time.sleep(0.1)
        
        print(f"\n📊 Restore Summary:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success rate: {successful/(successful+failed)*100:.1f}%")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Error restoring vectors: {e}")
        return False

def main():
    print("🚀 Starting Vector Restore")
    print("=" * 50)
    
    # List available backups
    backups = list_backups()
    if not backups:
        print("❌ No backup files found")
        print(f"   📁 Backup directory: {BACKUP_DIR}")
        return
    
    print("📋 Available backups:")
    for i, backup in enumerate(backups, 1):
        print(f"   {i}. {backup['timestamp']} - {backup['vector_count']} vectors")
    
    # Use latest backup by default, or allow user selection
    if len(backups) == 1:
        selected_backup = backups[0]
        print(f"\n🎯 Using backup: {selected_backup['timestamp']}")
    else:
        # For automation, use the latest backup
        selected_backup = backups[0]
        print(f"\n🎯 Using latest backup: {selected_backup['timestamp']}")
    
    # Create index if needed
    print("\n📝 Checking index...")
    if not create_index_if_missing():
        print("❌ Failed to create/verify index")
        return
    
    # Restore vectors
    print("\n🔄 Starting restore...")
    success = restore_vectors(selected_backup["file"])
    
    if success:
        print("\n🎉 Restore completed successfully!")
        print("💡 Your vector data has been restored to Pinecone Local")
    else:
        print("\n❌ Restore failed")

if __name__ == "__main__":
    main()