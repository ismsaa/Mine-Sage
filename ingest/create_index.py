from pinecone.grpc import PineconeGRPC
from pinecone import ServerlessSpec

pc = PineconeGRPC(api_key="local-dev", host="http://localhost:5081")

if not pc.has_index("mods"):
    pc.create_index(
        name="mods",
        vector_type="dense",
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(           # <-- FIXED
            cloud="aws",
            region="us-east-1"
        ),
        deletion_protection="disabled" # optional
    )
    print("Index 'mods' created.")
else:
    print("Index already exists.")
