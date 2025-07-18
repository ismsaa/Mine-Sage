#!/usr/bin/env python3
"""
Startup restore script

This script automatically restores the latest backup when the system starts.
It's designed to be run after Docker services are up and running.
"""

import time
import requests
import subprocess
import sys
from pathlib import Path

# Configuration
CONTROL_HOST = "http://localhost:5080"
MAX_WAIT_TIME = 60  # Maximum time to wait for services
CHECK_INTERVAL = 2  # Seconds between checks

def wait_for_services():
    """Wait for Pinecone Local to be ready"""
    print("⏳ Waiting for Pinecone Local to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            response = requests.get(f"{CONTROL_HOST}/indexes", timeout=5)
            if response.status_code == 200:
                print("✅ Pinecone Local is ready!")
                return True
        except Exception:
            pass
        
        print("   ⏳ Still waiting...")
        time.sleep(CHECK_INTERVAL)
    
    print("❌ Timeout waiting for Pinecone Local")
    return False

def check_if_data_exists():
    """Check if there's already data in the index"""
    try:
        response = requests.get(f"{CONTROL_HOST}/indexes")
        if response.status_code != 200:
            return False
        
        indexes = response.json()
        mods_index = None
        for idx in indexes.get('indexes', []):
            if idx['name'] == 'mods':
                mods_index = idx
                break
        
        if not mods_index:
            return False
        
        # Try a simple query to see if there's data
        dummy_vector = [0.0] * 768
        query_payload = {
            "vector": dummy_vector,
            "topK": 1,
            "includeMetadata": False
        }
        
        response = requests.post("http://localhost:5081/query", json=query_payload)
        if response.status_code == 200:
            result = response.json()
            matches = result.get('matches', [])
            return len(matches) > 0
        
        return False
        
    except Exception as e:
        print(f"⚠️  Error checking existing data: {e}")
        return False

def run_restore():
    """Run the restore script"""
    try:
        print("🔄 Running restore script...")
        result = subprocess.run([
            sys.executable, "restore_vectors.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Restore completed successfully")
            return True
        else:
            print(f"❌ Restore failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running restore: {e}")
        return False

def main():
    print("🚀 Startup Restore Service")
    print("=" * 50)
    
    # Wait for services to be ready
    if not wait_for_services():
        print("❌ Services not ready, skipping restore")
        return
    
    # Check if data already exists
    print("🔍 Checking for existing data...")
    if check_if_data_exists():
        print("✅ Data already exists, skipping restore")
        print("💡 Use 'python restore_vectors.py' to force restore from backup")
        return
    
    # Check if backup exists
    backup_dir = Path("./data/backups")
    if not backup_dir.exists() or not list(backup_dir.glob("vectors_backup_*.json")):
        print("⚠️  No backup files found, skipping restore")
        print("💡 This might be a fresh installation")
        return
    
    # Run restore
    print("📥 No existing data found, restoring from backup...")
    success = run_restore()
    
    if success:
        print("\n🎉 Startup restore completed!")
        print("💡 Your system is ready with restored data")
    else:
        print("\n⚠️  Startup restore failed")
        print("💡 You can manually run 'python restore_vectors.py'")

if __name__ == "__main__":
    main()