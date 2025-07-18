"""
title: Minecraft Modpack RAG Assistant
author: minecraft-rag
author_url: https://github.com/ismsaa/Mine-Sage
funding_url: https://github.com/ismsaa/Mine-Sage
version: 1.0
description: Search and ask questions about Minecraft mods and modpacks using RAG
"""

import requests
from pydant, Field
from typing import Optional

n:
    class Va):
        rag_api_base: str = 
            default="http://localh", 
            description="Base URL for the RAG"
        )
        s
            default=10, 
            description=ds"
        )

    def __init__(self):
        self.valves = sealves()

    asynck_info(
        self,
        query: str,
        top_k: int = 5,
        _,

    ) -> str:
        """Search for information a""
   
        if __event_emitter__:
            a_(
                {
                    "type": "status",
                    "data": {"descriptioFalse},
                }
            )
        
        try:
         = {
                "query": query,
                "top_k": min(top_k, 10),
                "score_threshold": 0.3
           
          
            response = requesst(
                f"{self.valves.rag_aearch",
                j
                timeout=self.valves.smeout
            )
            
            i00:
        )
            :
                    await __e
                        {
                
                       
                        }
                    )
                return result.get("res
            ese:
            "
                
        except Exception as e:
            return f"❌ Search"

    async def
        self,
        question: str,
        context_size: int = 5,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> str:
        """Ask detailed quest
        
        if __event_emitter__:
            await __event_emi
                {
                    "type": "status",
                    "False},
                }
            )
        
        try:
            payload = {
                "question": question,
                "context_size"
            }
    
            response = requests.post(
             at",
                json=poad,
                timeout=30
            )
            
            i0:
           n()
                if __event_emitter__:
        __(
                        {
                            "type": "status",
                            "data": {"description},
             }
           )
                return resulted")
            else:
                r"
                
        except Exception as e:
            returtr(e)}"or: {sing err processestionf"❌ Qun 