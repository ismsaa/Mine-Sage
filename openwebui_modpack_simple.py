"""
title: Minecraft Modpack RAG Assistant
author: minecraft-rag
author_url: https://github.com/ismsaa/Mine-Sage
funding_url: https://github.com/ismsaa/Mine-Sage
version: 1.0
description: Search and ask questions about Minecraft mods and modpacks using RAG
"""

import requests
from pydantic import BaseModel, Field
from typing import Optional

class Function:
    class Valves(BaseModel):
        rag_api_base: str = Field(
            default="http://localhost:8001", 
            description="Base URL for the RAG API server"
        )
        search_timeout: int = Field(
            default=10, 
            description="Timeout for search requests in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def search_modpack_info(
        self,
        query: str,
        top_k: int = 5,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> str:
        """Search for information about Minecraft mods, modpacks, or configurations"""
        
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Searching for '{query}'...", "done": False},
                }
            )
        
        try:
            payload = {
                "query": query,
                "top_k": min(top_k, 10),
                "score_threshold": 0.3
            }
            
            response = requests.post(
                f"{self.valves.rag_api_base}/tools/modpack_search",
                json=payload,
                timeout=self.valves.search_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Search completed!", "done": True},
                        }
                    )
                return result.get("result", "No results found")
            else:
                return f"❌ Search failed with status {response.status_code}"
                
        except Exception as e:
            return f"❌ Search error: {str(e)}"

    async def ask_modpack_question(
        self,
        question: str,
        context_size: int = 5,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> str:
        """Ask detailed questions about modpacks and get AI-powered answers"""
        
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Processing question...", "done": False},
                }
            )
        
        try:
            payload = {
                "question": question,
                "context_size": min(context_size, 10)
            }
            
            response = requests.post(
                f"{self.valves.rag_api_base}/tools/modpack_chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Answer generated!", "done": True},
                        }
                    )
                return result.get("result", "No answer generated")
            else:
                return f"❌ Question processing failed with status {response.status_code}"
                
        except Exception as e:
            return f"❌ Question processing error: {str(e)}"