"""
title: Minecraft Modpack Search
author: minecraft-rag
author_url: https://github.com/ismsaa/Mine-Sage
funding_url: https://github.com/ismsaa/Mine-Sage
version: 1.0
description: Search for Minecraft mod and modpack information using RAG
"""

import requests
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Action:
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

    async def action(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """Handle modpack search action"""
        
        # Get the user's message
        messages = body.get("messages", [])
        if not messages:
            return None
            
        user_message = messages[-1].get("content", "")
        
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Searching modpack database for: '{user_message[:50]}...'", "done": False},
                }
            )
        
        try:
            # Search for modpack information
            payload = {
                "query": user_message,
                "top_k": 5,
                "score_threshold": 0.3
            }
            
            response = requests.post(
                f"{self.valves.rag_api_base}/tools/modpack_search",
                json=payload,
                timeout=self.valves.search_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                search_result = result.get("result", "No results found")
                
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Search completed!", "done": True},
                        }
                    )
                
                # Return the search result as a new message
                return {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": f"🔍 **Modpack Search Results:**\n\n{search_result}"
                        }
                    ]
                }
            else:
                error_msg = f"❌ Search failed with status {response.status_code}"
                return {
                    "messages": [
                        {
                            "role": "assistant", 
                            "content": error_msg
                        }
                    ]
                }
                
        except Exception as e:
            error_msg = f"❌ Search error: {str(e)}"
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": error_msg
                    }
                ]
            }