"""
title: Minecraft Modpack Expert
author: minecraft-rag
author_url: https://github.com/ismsaa/Mine-Sage
funding_url: https://github.com/ismsaa/Mine-Sage
version: 1.0
description: AI assistant specialized in Minecraft mods and modpacks using RAG
"""

import requests
from pydantic import BaseModel, Field
from typing import Optional, Generator, Iterator

class Pipe:
    class Valves(BaseModel):
        rag_api_base: str = Field(
            default="http://rag-worker:8001", 
            description="Base URL for the RAG API server"
        )
        chat_timeout: int = Field(
            default=30, 
            description="Timeout for chat requests in seconds"
        )
        search_timeout: int = Field(
            default=10,
            description="Timeout for search requests in seconds"
        )

    def __init__(self):
        self.type = "manifold"
        self.id = "modpack_expert"
        self.name = "Modpack Expert"
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        return [
            {
                "id": "modpack_expert",
                "name": "Modpack Expert",
                "description": "AI assistant specialized in Minecraft mods and modpacks"
            }
        ]

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> str | Generator | Iterator:
        """Main pipe function for modpack queries"""
        
        # Get the user's message
        messages = body.get("messages", [])
        if not messages:
            return "Please ask me something about Minecraft mods or modpacks!"
            
        user_message = messages[-1].get("content", "")
        
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Processing your modpack question...", "done": False},
                }
            )
        
        try:
            # Check if this is a search query or a question
            search_keywords = ["search", "find", "list", "show me", "what mods"]
            is_search = any(keyword in user_message.lower() for keyword in search_keywords)
            
            if is_search:
                # Use search endpoint
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
            else:
                # Use chat endpoint for detailed questions
                payload = {
                    "question": user_message,
                    "context_size": 5
                }
                
                response = requests.post(
                    f"{self.valves.rag_api_base}/tools/modpack_chat",
                    json=payload,
                    timeout=self.valves.chat_timeout
                )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("result", "I couldn't find information about that.")
                
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Response ready!", "done": True},
                        }
                    )
                
                return answer
            else:
                return f"❌ I encountered an error (status {response.status_code}). Please try again."
                
        except requests.exceptions.Timeout:
            return "❌ The request timed out. The modpack database might be busy. Please try again."
        except Exception as e:
            return f"❌ I encountered an error: {str(e)}"