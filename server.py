# rag-worker/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pinecone.grpc import PineconeGRPC, GRPCClientConfig
import os, json

app = FastAPI()
PINECONE_HOST = os.getenv("PINECONE_HOST", "http://pinecone:5081")

# ---- connect once at startup ----
pc = PineconeGRPC(api_key="local-dev", host=PINECONE_HOST)
idx_host = pc.describe_index("mods").host
index = pc.Index(host=idx_host, grpc_config=GRPCClientConfig(secure=False))

# ---- request / response models ----
class Query(BaseModel):
    text: str
    top_k: int = 5

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/hello")
def hello():
    return {"msg": "Minecraft RAG worker is alive 🎮"}

@app.post("/search")
def search(q: Query):
    try:
        # demo: assume you embedded client-side; if not, embed here
        results = index.query(vector=[0]*1536, top_k=q.top_k)  # placeholder
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
