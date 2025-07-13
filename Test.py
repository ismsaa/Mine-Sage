#!/usr/bin/env python3
import os
from pinecone.grpc import PineconeGRPC

pc = PineconeGRPC(
    api_key="dev",
    host=os.getenv("PINECONE_HOST", "http://localhost:5081")
)


# 2. List all indexes
indexes = pc.list_indexes()
if not indexes:
    print("No indexes found.")
    exit(0)

# 3. Describe stats for each index
for idx in indexes:
    stats = idx.spec
    dim = idx.dimension
    total = idx.metric
    print(f"Index: {idx}")
    # Optionally, print per-namespace breakdown:
    for ns, ns_stats in stats.get("namespaces", {}).items():
        print(f"    – Namespace '{ns}': {ns_stats.get('vector_count')} vectors")
