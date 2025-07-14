from pinecone import Pinecone
pc = Pinecone(api_key="anything", environment="local", host="http://localhost:5080")  # or 5080
print(pc.list_indexes().names())    # should include "mods"

idx = pc.Index("mods")
idx.upsert(vectors=[{"id":"test1","values":[0.1]*768}])
print(idx.query(vector=[0.1]*768, top_k=1).matches)
