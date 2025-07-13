# ingest/bootstrap_pinecone.py

import os
import glob, json, pathlib
from tqdm import tqdm

from pinecone.grpc import PineconeGRPC, GRPCClientConfig
from pinecone import ServerlessSpec
from pinecone.core.client.exceptions import PineconeApiException

ROOT = pathlib.Path(__file__).parents[1]
EMB_DIR = ROOT / "data" / "embeddings"

# Instantiate the GRPC client directly (no pinecone.init required)
pc = PineconeGRPC(
    api_key=os.getenv("PINECONE_API_KEY", "pclocal"),
    host=os.getenv("PINECONE_HOST", "http://pinecone:5081")
)

index_name = "mods"
try:
    if index_name not in pc.list_indexes():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
except PineconeApiException as e:
    if e.status != 409:
        raise

idx_host = pc.describe_index(index_name).host
idx = pc.Index(host=idx_host, grpc_config=GRPCClientConfig(secure=False))

batch, BATCH = [], 200
for fn in tqdm(glob.glob(str(EMB_DIR / '*.json'))):
    batch.append(json.load(open(fn)))
    if len(batch) >= BATCH:
        idx.upsert(batch); batch.clear()
if batch:
    idx.upsert(batch)

print("Re-ingestion complete.")
