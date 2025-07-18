#!/usr/bin/env python3
"""
OpenWebUI Integration for Minecraft Modpack RAG System

This script sets up custom tools in OpenWebUI to provide modpack knowledge
directly in the chat interface.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
OPENWEBUI_URL = "http://localhost:3000"
RAG_API_BASE = "http://localhost:8001"

def create_openwebui_tool_config():
    """Create OpenWebUI tool configuration"""
    return {
        "tools": [
            {
                "id": "modpack_search",
                "name": "Modpack Search",
                "description": "Search for information about Minecraft mods, modpacks, or configurations",
                "type": "function",
                "function": {
                    "name": "search_modpack_info",
                    "description": "Search the modpack database for mods, configurations, or pack information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'mekanism mods', 'thermal expansion', 'kubejs scripts')"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (1-10)",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"]
                    }
                },
                "endpoint": f"{RAG_API_BASE}/tools/modpack_search"
            },
            {
                "id": "modpack_chat",
                "name": "Modpack Expert",
                "description": "Ask detailed questions about modpacks and get AI-powered answers with sources",
                "type": "function", 
                "function": {
                    "name": "ask_modpack_question",
                    "description": "Get detailed answers about modpacks, mods, configurations, and gameplay",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about modpacks (e.g., 'What mods are in Enigmatica9Expert?', 'How is Mekanism configured?')"
                            },
                            "context_size": {
                                "type": "integer",
                                "description": "Number of context documents to use (3-10)",
                                "default": 5,
                                "minimum": 3,
                                "maximum": 10
                            }
                        },
                        "required": ["question"]
                    }
                },
                "endpoint": f"{RAG_API_BASE}/tools/modpack_chat"
            }
        ]
    }

def test_openwebui_connection():
    """Test connection to OpenWebUI"""
    try:
        response = requests.get(f"{OPENWEBUI_URL}/api/v1/auths", timeout=5)
        return response.status_code in [200, 401, 403]  # Any of these means OpenWebUI is running
    except Exception as e:
        print(f"❌ Cannot connect to OpenWebUI: {e}")
        return False

def register_tools_with_openwebui():
    """Register our tools with OpenWebUI"""
    print("🔧 Registering tools with OpenWebUI...")
    
    # Note: OpenWebUI tool registration varies by version
    # This is a demonstration of the configuration format
    tool_config = create_openwebui_tool_config()
    
    print("✅ Tool configuration created:")
    print(json.dumps(tool_config, indent=2))
    
    return tool_config

def create_openwebui_function_file():
    """Create a Python file that OpenWebUI can import as custom functions"""
    function_code = '''
"""
Custom functions for OpenWebUI - Minecraft Modpack RAG System
Place this file in your OpenWebUI functions directory
"""

import requests
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        self.rag_api_base = "http://host.docker.internal:8001"  # Access host from container
    
    def search_modpack_info(
        self, 
        query: str = Field(description="Search query for mods, packs, or configs"),
        top_k: int = Field(default=5, description="Number of results to return")
    ) -> Dict:
        """Search for information about Minecraft mods, modpacks, or configurations."""
        try:
            payload = {"query": query, "top_k": top_k, "score_threshold": 0.3}
            response = requests.post(f"{self.rag_api_base}/search", json=payload, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                formatted = []
                
                for result in results:
                    metadata = result.get("metadata", {})
                    formatted.append({
                        "title": metadata.get("mod_title", metadata.get("pack_name", "Unknown")),
                        "type": metadata.get("type", "unknown"),
                        "score": round(result.get("score", 0), 3),
                        "content": result.get("content", "")
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": formatted,
                    "total": len(formatted)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ask_modpack_question(
        self,
        question: str = Field(description="Natural language question about modpacks"),
        context_size: int = Field(default=5, description="Number of context documents")
    ) -> Dict:
        """Ask detailed questions about modpacks and get AI-powered answers."""
        try:
            payload = {"message": question, "top_k": context_size, "score_threshold": 0.3}
            response = requests.post(f"{self.rag_api_base}/chat", json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                sources = []
                for source in result.get("sources", []):
                    metadata = source.get("metadata", {})
                    sources.append({
                        "title": metadata.get("mod_title", metadata.get("pack_name", "Unknown")),
                        "type": metadata.get("type", "unknown"),
                        "score": round(source.get("score", 0), 3)
                    })
                
                return {
                    "success": True,
                    "question": question,
                    "answer": result.get("response", "No response generated"),
                    "sources": sources,
                    "sources_count": len(sources)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# Initialize tools
tools = Tools()

# Export functions for OpenWebUI
def search_modpack_info(query: str, top_k: int = 5) -> str:
    """Search for Minecraft mod and modpack information"""
    result = tools.search_modpack_info(query, top_k)
    
    if result["success"]:
        output = f"🔍 Found {result['total']} results for '{query}':\\n\\n"
        for i, item in enumerate(result["results"], 1):
            output += f"{i}. **{item['title']}** ({item['type']})\\n"
            output += f"   Score: {item['score']} | {item['content'][:100]}...\\n\\n"
        return output
    else:
        return f"❌ Search failed: {result['error']}"

def ask_modpack_question(question: str, context_size: int = 5) -> str:
    """Ask detailed questions about modpacks"""
    result = tools.ask_modpack_question(question, context_size)
    
    if result["success"]:
        output = f"**Question:** {question}\\n\\n"
        output += f"**Answer:** {result['answer']}\\n\\n"
        if result["sources"]:
            output += f"**Sources ({result['sources_count']}):**\\n"
            for source in result["sources"]:
                output += f"- {source['title']} ({source['type']}, score: {source['score']})\\n"
        return output
    else:
        return f"❌ Question failed: {result['error']}"
'''
    
    with open('openwebui_functions.py', 'w') as f:
        f.write(function_code)
    
    print("✅ Created openwebui_functions.py")
    print("📋 To use in OpenWebUI:")
    print("   1. Copy openwebui_functions.py to your OpenWebUI functions directory")
    print("   2. Restart OpenWebUI")
    print("   3. The functions will appear as available tools in chat")

def main():
    print("🚀 OpenWebUI Integration Setup")
    print("=" * 50)
    
    # Test connections
    print("🔍 Testing connections...")
    
    # Test RAG API
    try:
        response = requests.get(f"{RAG_API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✅ RAG API is accessible")
        else:
            print(f"⚠️  RAG API returned {response.status_code}")
    except Exception as e:
        print(f"❌ RAG API not accessible: {e}")
        return
    
    # Test OpenWebUI
    if test_openwebui_connection():
        print("✅ OpenWebUI is accessible")
    else:
        print("⚠️  OpenWebUI not accessible (this is OK for now)")
    
    print()
    
    # Create tool configuration
    tool_config = register_tools_with_openwebui()
    
    # Create function file
    print()
    create_openwebui_function_file()
    
    print()
    print("🎯 Next Steps:")
    print("1. Visit http://localhost:3000 to access OpenWebUI")
    print("2. Copy openwebui_functions.py to OpenWebUI's functions directory")
    print("3. Restart OpenWebUI to load the new functions")
    print("4. Test the tools in a chat conversation")
    
    print()
    print("💡 Example queries to try in OpenWebUI:")
    print("   - search_modpack_info('mekanism')")
    print("   - ask_modpack_question('What mods are in Enigmatica9Expert?')")
    print("   - ask_modpack_question('How is Thermal Expansion configured?')")

if __name__ == "__main__":
    main()