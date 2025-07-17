#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_ollama import OllamaEmbeddings, OllamaLLM
import requests
import os
from typing import List, Optional

app = FastAPI(title="Minecraft Modpack RAG API", version="1.0.0")

# Add CORS middleware for OpenWebUI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DATA_HOST = os.getenv("PINECONE_DATA_HOST", "http://localhost:5081")

# Initialize components
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
llm = OllamaLLM(model="llama3", base_url=OLLAMA_URL)

# Request/Response models
class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: float = 0.3

class ChatQuery(BaseModel):
    message: str
    top_k: int = 5
    score_threshold: float = 0.3

class SearchResult(BaseModel):
    id: str
    score: float
    metadata: dict
    content: str

class ChatResponse(BaseModel):
    response: str
    sources: List[SearchResult]

def semantic_search(query: str, top_k: int = 5, score_threshold: float = 0.3) -> List[SearchResult]:
    """Perform semantic search and return results"""
    try:
        # Generate embedding for the query
        query_embedding = emb.embed_query(query)
        
        # Search Pinecone
        search_payload = {
            "vector": query_embedding,
            "topK": top_k,
            "includeMetadata": True,
            "includeValues": False
        }
        
        response = requests.post(f"{DATA_HOST}/query", json=search_payload)
        if response.status_code != 200:
            return []
        
        results = response.json()
        search_results = []
        
        for match in results.get('matches', []):
            if match.get('score', 0) >= score_threshold:
                # Format content based on document type
                metadata = match.get('metadata', {})
                content = format_document_content(match['id'], metadata)
                
                search_results.append(SearchResult(
                    id=match['id'],
                    score=match.get('score', 0),
                    metadata=metadata,
                    content=content
                ))
        
        return search_results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def format_document_content(doc_id: str, metadata: dict) -> str:
    """Format document content for display"""
    doc_type = metadata.get('type', 'unknown')
    
    if doc_type == 'pack_overview':
        return f"Modpack: {metadata.get('pack_name')} v{metadata.get('pack_version')} ({metadata.get('mod_count')} mods)"
    elif doc_type == 'base_mod':
        return f"Mod: {metadata.get('mod_title')} (ID: {metadata.get('project_id')}, Source: {metadata.get('source')})"
    elif doc_type == 'pack_override':
        return f"Configuration: {metadata.get('file_path')} ({metadata.get('override_type')})"
    
    return f"Document: {doc_id}"

def create_rag_response(user_query: str, search_results: List[SearchResult]) -> str:
    """Generate RAG response using LLM"""
    if not search_results:
        return "I couldn't find any relevant information in the modpack database for your query."
    
    # Format context
    context_parts = []
    for result in search_results:
        context_parts.append(f"- {result.content} (relevance: {result.score:.3f})")
    
    context = "\n".join(context_parts)
    
    # Create prompt
    prompt = f"""You are a helpful assistant that answers questions about Minecraft modpacks. Use the following context to answer the user's question.

CONTEXT:
{context}

USER QUESTION: {user_query}

Provide a helpful and accurate answer based on the context. Be specific about mod names, versions, and configurations when available.

ANSWER:"""
    
    try:
        response = llm.invoke(prompt)
        return response
    except Exception as e:
        return f"Error generating response: {e}"

# API Endpoints
@app.get("/")
def root():
    return {"message": "Minecraft Modpack RAG API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "minecraft-rag"}

@app.post("/search", response_model=List[SearchResult])
def search_endpoint(query: SearchQuery):
    """Search for relevant modpack information"""
    try:
        results = semantic_search(query.query, query.top_k, query.score_threshold)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(query: ChatQuery):
    """Chat with RAG-enhanced responses about modpacks"""
    try:
        # Get relevant context
        search_results = semantic_search(query.message, query.top_k, query.score_threshold)
        
        # Generate response
        response = create_rag_response(query.message, search_results)
        
        return ChatResponse(
            response=response,
            sources=search_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# OpenWebUI Tool Integration
@app.post("/tools/modpack_search")
def modpack_search_tool(query: dict):
    """OpenWebUI tool for modpack search"""
    try:
        user_query = query.get("query", "")
        if not user_query:
            return {"error": "No query provided"}
        
        # Perform search
        results = semantic_search(user_query, top_k=3, score_threshold=0.3)
        
        # Format for OpenWebUI
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.content,
                "score": result.score,
                "type": result.metadata.get('type', 'unknown')
            })
        
        return {
            "results": formatted_results,
            "query": user_query,
            "total": len(formatted_results)
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/tools/modpack_chat")
def modpack_chat_tool(query: dict):
    """OpenWebUI tool for modpack chat"""
    try:
        user_message = query.get("message", "")
        if not user_message:
            return {"error": "No message provided"}
        
        # Get RAG response
        search_results = semantic_search(user_message, top_k=5, score_threshold=0.3)
        response = create_rag_response(user_message, search_results)
        
        return {
            "response": response,
            "sources_count": len(search_results),
            "query": user_message
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
