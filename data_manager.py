#!/usr/bin/env python3
"""
Comprehensive Data Management Tool

This script provides a unified interface for managing vector data persistence:
- Backup current data
- Restore from backups
- List available backups
- Clean old backups
- Show current database status
"""

import argparse
import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
CONTROL_HOST = "http://localhost:5080"
DATA_HOST = "http://localhost:5081"
BACKUP_DIR = Path("./data/backups")

def get_database_status():
    """Get current database status"""
    try:
        # Check if Pinecone is accessible
        response = requests.get(f"{CONTROL_HOST}/indexes", timeout=5)
        if response.status_code != 200:
            return {"status": "offline", "error": f"HTTP {response.status_code}"}
        
        indexes = response.json()
        mods_index = None
        for idx in indexes.get('indexes', []):
            if idx['name'] == 'mods':
                mods_index = idx
                break
        
        if not mods_index:
            return {"status": "no_index", "indexes": len(indexes.get('indexes', []))}
        
        # Get vector count estimate
        dummy_vector = [0.0] * mods_index['dimension']
        query_payload = {
            "vector": dummy_vector,
            "topK": 10000,
            "includeMetadata": True
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=query_payload)
        if response.status_code == 200:
            result = response.json()
            vectors = result.get('matches', [])
            
            # Count by type
            type_counts = {}
            for vector in vectors:
                doc_type = vector.get('metadata', {}).get('type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            return {
                "status": "online",
                "index_name": mods_index['name'],
                "dimension": mods_index['dimension'],
                "metric": mods_index['metric'],
                "vector_count": len(vectors),
                "type_counts": type_counts
            }
        else:
            return {"status": "query_failed", "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

def list_backups_detailed():
    """List all available backups with details"""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for backup_file in BACKUP_DIR.glob("vectors_backup_*.json"):
        try:
            stat = backup_file.stat()
            with open(backup_file, 'r') as f:
                data = json.load(f)
            
            backups.append({
                "file": backup_file,
                "filename": backup_file.name,
                "timestamp": data.get("timestamp", "unknown"),
                "vector_count": data.get("vector_count", 0),
                "index_name": data.get("index_name", "unknown"),
                "file_size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "metadata": data.get("metadata", {})
            })
        except Exception as e:
            print(f"⚠️  Could not read backup {backup_file}: {e}")
    
    return sorted(backups, key=lambda x: x["created"], reverse=True)

def clean_old_backups(keep_count=5):
    """Clean old backup files, keeping only the most recent ones"""
    backups = list_backups_detailed()
    if len(backups) <= keep_count:
        print(f"✅ Only {len(backups)} backups found, nothing to clean")
        return
    
    to_delete = backups[keep_count:]
    print(f"🗑️  Cleaning {len(to_delete)} old backups (keeping {keep_count} most recent)")
    
    for backup in to_delete:
        try:
            backup["file"].unlink()
            print(f"   ✅ Deleted: {backup['filename']}")
        except Exception as e:
            print(f"   ❌ Failed to delete {backup['filename']}: {e}")

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def main():
    parser = argparse.ArgumentParser(description="Manage vector data persistence")
    parser.add_argument("command", choices=["status", "backup", "restore", "list", "clean"], 
                       help="Command to execute")
    parser.add_argument("--keep", type=int, default=5, 
                       help="Number of backups to keep when cleaning (default: 5)")
    
    args = parser.parse_args()
    
    if args.command == "status":
        print("📊 Database Status")
        print("=" * 50)
        
        status = get_database_status()
        
        if status["status"] == "online":
            print("✅ Status: Online")
            print(f"📦 Index: {status['index_name']}")
            print(f"📏 Dimension: {status['dimension']}")
            print(f"📐 Metric: {status['metric']}")
            print(f"📈 Total vectors: {status['vector_count']}")
            
            if status['type_counts']:
                print("\n📋 Document types:")
                for doc_type, count in status['type_counts'].items():
                    emoji = {"base_mod": "🔧", "pack_overview": "📦", "pack_override": "⚙️"}.get(doc_type, "📄")
                    print(f"   {emoji} {doc_type}: {count}")
        
        elif status["status"] == "offline":
            print("❌ Status: Offline")
            print(f"   Error: {status.get('error', 'Unknown')}")
        
        elif status["status"] == "no_index":
            print("⚠️  Status: No 'mods' index found")
            print(f"   Available indexes: {status.get('indexes', 0)}")
        
        else:
            print(f"❌ Status: {status['status']}")
            print(f"   Error: {status.get('error', 'Unknown')}")
    
    elif args.command == "backup":
        print("💾 Creating Backup")
        print("=" * 50)
        os.system("python backup_vectors.py")
    
    elif args.command == "restore":
        print("📥 Restoring from Backup")
        print("=" * 50)
        os.system("python restore_vectors.py")
    
    elif args.command == "list":
        print("📋 Available Backups")
        print("=" * 50)
        
        backups = list_backups_detailed()
        if not backups:
            print("❌ No backup files found")
            return
        
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup['filename']}")
            print(f"   📅 Created: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📈 Vectors: {backup['vector_count']}")
            print(f"   📁 Size: {format_file_size(backup['file_size'])}")
            print(f"   🎯 Index: {backup['index_name']}")
            print()
    
    elif args.command == "clean":
        print("🗑️  Cleaning Old Backups")
        print("=" * 50)
        clean_old_backups(args.keep)

if __name__ == "__main__":
    main()