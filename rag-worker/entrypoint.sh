# rag-worker/entrypoint.sh             <-- make sure this is the FIRST line
#!/usr/bin/env bash
set -e
echo "Waiting for Pinecone gRPC on pinecone:5081…"
for i in {1..30}; do
  if nc -z pinecone 5081; then
    echo "Pinecone is up!"
    break
  fi
  sleep 1
done

python ingest/bootstrap_pinecone.py    # idempotent: safe on restarts
exec uvicorn server:app --host 0.0.0.0 --port 8000
