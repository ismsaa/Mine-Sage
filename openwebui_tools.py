#!/usr/bin/env python3
"""
OpenWebUI Tools for Minecraft Modpack RAG System

These functions will be registered as tools in OpenWebUI to provide
modpack knowledge directly in the chat interface.
"""

import requests
import json
from typing import Dict, List, Optional

# Configuration
RAG_API_BASE = "http://localhost:8001"

def search_modpack_info(query: str, top_k: int = 5) -> Dict:
    """
    Search for information about mods, modpacks, or configurations.
    
    Args:
        query: The search query (e.g., "mekanism mods", "thermal expansion")
        top_k: Number of results to return (default: 5)
    
    Returns:
        Dictionary with search results and metadata
    """
    try:
        payload = {
            "query": query,
            "top_k": top_k,
            "score_threshold": 0.3
        }
        
        response = requests.post(f"{RAG_API_BASE}/search", json=payload, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            # Format results for OpenWebUI
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("metadata", {}).get("mod_title", "Unknown"),
                    "type": result.get("metadata", {}).get("type", "unknown"),
                    "score": round(result.get("score", 0), 3),
                    "source": result.get("metadata", {}).get("source", "unknown"),
                    "content": result.get("content", "")
                })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }
        else:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}",
                "query": query
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

def ask_modpack_question(question: str, top_k: int = 5) -> Dict:
    """
    Ask a natural language question about modpacks and get an AI-powered answer.
    
    Args:
        question: Natural language question (e.g., "What mods are in Enigmatica9Expert?")
        top_k: Number of context documents to use (default: 5)
    
    Returns:
        Dictionary with AI response and source information
    """
    try:
        payload = {
            "message": question,
            "top_k": top_k,
            "score_threshold": 0.3
        }
        
        response = requests.post(f"{RAG_API_BASE}/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Format sources for display
            sources_info = []
            for source in result.get("sources", []):
                metadata = source.get("metadata", {})
                sources_info.append({
                    "title": metadata.get("mod_title", metadata.get("pack_name", "Unknown")),
                    "type": metadata.get("type", "unknown"),
                    "score": round(source.get("score", 0), 3)
                })
            
            return {
                "success": True,
                "question": question,
                "answer": result.get("response", "No response generated"),
                "sources": sources_info,
                "sources_count": len(sources_info)
            }
        else:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}",
                "question": question
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "question": question
        }

def get_modpack_stats() -> Dict:
    """
    Get statistics about the current modpack database.
    
    Returns:
        Dictionary with database statistics
    """
    try:
        # Try to get some sample data to determine database size
        sample_search = requests.post(
            f"{RAG_API_BASE}/search", 
            json={"query": "mod", "top_k": 100, "score_threshold": 0.0},
            timeout=10
        )
        
        if sample_search.status_code == 200:
            results = sample_search.json()
            
            # Count by document type
            type_counts = {}
            for result in results:
                doc_type = result.get("metadata", {}).get("type", "unknown")
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            return {
                "success": True,
                "total_documents": len(results),
                "document_types": type_counts,
                "api_status": "connected"
            }
        else:
            return {
                "success": False,
                "error": f"Could not retrieve stats: {sample_search.status_code}",
                "api_status": "error"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "api_status": "disconnected"
        }

# OpenWebUI Tool Registration Format
OPENWEBUI_TOOLS = [
    {
        "name": "search_modpack_info",
        "description": "Search for information about Minecraft mods, modpacks, or configurations",
        "function": search_modpack_info,
        "parameters": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'mekanism mods', 'thermal expansion')",
                "required": True
            },
            "top_k": {
                "type": "integer", 
                "description": "Number of results to return",
                "default": 5
            }
        }
    },
    {
        "name": "ask_modpack_question",
        "description": "Ask natural language questions about modpacks and get AI-powered answers",
        "function": ask_modpack_question,
        "parameters": {
            "question": {
                "type": "string",
                "description": "Natural language question about modpacks",
                "required": True
            },
            "top_k": {
                "type": "integer",
                "description": "Number of context documents to use",
                "default": 5
            }
        }
    },
    {
        "name": "get_modpack_stats", 
        "description": "Get statistics about the modpack database",
        "function": get_modpack_stats,
        "parameters": {}
    }
]

if __name__ == "__main__":
    # Test the tools
    print("🧪 Testing OpenWebUI Tools")
    print("=" * 50)
    
    # Test search
    print("\n1. Testing search_modpack_info...")
    search_result = search_modpack_info("mekanism")
    print(f"   Success: {search_result['success']}")
    if search_result['success']:
        print(f"   Found: {search_result['total_found']} results")
    
    # Test question
    print("\n2. Testing ask_modpack_question...")
    question_result = ask_modpack_question("What is Mekanism?")
    print(f"   Success: {question_result['success']}")
    if question_result['success']:
        print(f"   Answer length: {len(question_result['answer'])} chars")
        print(f"   Sources: {question_result['sources_count']}")
    
    # Test stats
    print("\n3. Testing get_modpack_stats...")
    stats_result = get_modpack_stats()
    print(f"   Success: {stats_result['success']}")
    if stats_result['success']:
        print(f"   Total documents: {stats_result['total_documents']}")
        print(f"   Document types: {stats_result['document_types']}")
    
    print("\n✅ Tool testing complete!")