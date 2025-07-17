#!/usr/bin/env python3
import time, os
import requests
import json

# Test Pinecone Local directly with HTTP requests
CONTROL_HOST = os.getenv("PINECONE_CONTROL_HOST", "http://localhost:5080")
DATA_HOST = os.getenv("PINECONE_DATA_HOST", "http://localhost:5081")
INDEX = "mods"
DIM = 768

print(f"Testing Pinecone Local at {CONTROL_HOST}")

# 1) Check if index exists
try:
    response = requests.get(f"{CONTROL_HOST}/indexes")
    indexes = response.json()
    print(f"[INDEXES] {indexes}")
    
    index_exists = any(idx['name'] == INDEX for idx in indexes.get('indexes', []))
    
    if not index_exists:
        # Create index
        create_payload = {
            "name": INDEX,
            "dimension": DIM,
            "metric": "cosine",
            "spec": {
                "serverless": {
                    "cloud": "aws",
                    "region": "us-east-1"
                }
            }
        }
        response = requests.post(f"{CONTROL_HOST}/indexes", json=create_payload)
        print(f"[INDEX CREATED] {response.status_code}: {response.text}")
        time.sleep(2)  # Wait for index to be ready
    
    # 2) Test upsert
    upsert_payload = {
        "vectors": [
            {
                "id": "test1",
                "values": [0.1] * DIM
            }
        ]
    }
    
    response = requests.post(f"{DATA_HOST}/vectors/upsert", json=upsert_payload)
    print(f"[UPSERT] {response.status_code}: {response.text}")
    
    # 3) Test query
    query_payload = {
        "vector": [0.1] * DIM,
        "topK": 1
    }
    
    response = requests.post(f"{DATA_HOST}/query", json=query_payload)
    print(f"[QUERY] {response.status_code}: {response.text}")
    
except Exception as e:
    print(f"[ERROR] {e}")
