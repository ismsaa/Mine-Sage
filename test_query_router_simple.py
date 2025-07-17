#!/usr/bin/env python3
import requests
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.schema import Document
from typing import List

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

class SimpleModpackRouter:
    """Simplified router for testing"""
    
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
        self.llm = OllamaLLM(model="llama3", base_url=OLLAMA_URL)
    
    def search_documents(self, query: str, top_k: int = 3) -> List[dict]:
        """Search for relevant documents"""
        try:
            # Generate embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search Pinecone
            search_payload = {
                "vector": query_embedding,
                "topK": top_k,
                "includeMetadata": True,
                "includeValues": False
            }
            
            response = requests.post(f"{DATA_HOST}/query", json=search_payload)
            if response.status_code == 200:
                results = response.json()
                return results.get('matches', [])
            else:
                print(f"❌ Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def classify_query(self, query: str) -> str:
        """Classify query type"""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['kubejs', 'config', 'script', 'override', 'jei', 'emi']):
            return 'configuration'
        elif any(keyword in query_lower for keyword in ['mod', 'mods', 'mekanism', 'applied', 'sophisticated']):
            return 'mod_specific'
        else:
            return 'general'
    
    def format_context(self, matches: List[dict]) -> str:
        """Format search results into context"""
        if not matches:
            return "No relevant information found."
        
        context_parts = []
        for match in matches:
            metadata = match.get('metadata', {})
            doc_type = metadata.get('type', 'unknown')
            score = match.get('score', 0)
            
            if doc_type == 'pack_overview':
                context_parts.append(f"MODPACK: {metadata.get('pack_name')} v{metadata.get('pack_version')} ({metadata.get('mod_count')} mods) [Score: {score:.3f}]")
            elif doc_type == 'base_mod':
                context_parts.append(f"MOD: {metadata.get('mod_title')} (ID: {metadata.get('project_id')}, Source: {metadata.get('source')}) [Score: {score:.3f}]")
            elif doc_type == 'pack_override':
                context_parts.append(f"CONFIG: {metadata.get('file_path')} ({metadata.get('override_type')}) [Score: {score:.3f}]")
        
        return "\n".join(context_parts)
    
    def generate_response(self, query: str, context: str, query_type: str) -> str:
        """Generate response using LLM"""
        if query_type == 'configuration':
            prompt = f"""You are a modpack configuration expert. Answer the user's question about configurations and scripts.

Context:
{context}

Question: {query}

Focus on configuration files, scripts, and customizations. Be specific and helpful.

Answer:"""
        elif query_type == 'mod_specific':
            prompt = f"""You are a Minecraft mod expert. Answer the user's question about specific mods.

Context:
{context}

Question: {query}

Focus on mod names, features, and how they work in the modpack. Be specific and helpful.

Answer:"""
        else:
            prompt = f"""You are a helpful Minecraft modpack assistant. Answer the user's question.

Context:
{context}

Question: {query}

Provide a helpful and accurate answer based on the context.

Answer:"""
        
        try:
            response = self.llm.invoke(prompt)
            return response
        except Exception as e:
            return f"Error generating response: {e}"
    
    def process_query(self, query: str) -> tuple:
        """Process a query and return response with metadata"""
        print(f"🔍 Searching for: '{query}'")
        
        # Classify query
        query_type = self.classify_query(query)
        print(f"🎯 Query type: {query_type}")
        
        # Search for relevant documents
        matches = self.search_documents(query, top_k=3)
        print(f"📚 Found {len(matches)} relevant documents")
        
        if not matches:
            return "I couldn't find any relevant information for your query.", []
        
        # Format context
        context = self.format_context(matches)
        print("📄 Context prepared")
        
        # Generate response
        print("🤖 Generating response...")
        response = self.generate_response(query, context, query_type)
        
        return response, matches

def test_queries():
    """Test the router with various queries"""
    router = SimpleModpackRouter()
    
    test_cases = [
        "What mods are in this modpack?",
        "Tell me about Mekanism mods",
        "What KubeJS configurations are there?",
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {query}")
        print('='*60)
        
        try:
            response, sources = router.process_query(query)
            
            print("\n🤖 Response:")
            print(response)
            
            print(f"\n📚 Sources ({len(sources)}):")
            for j, source in enumerate(sources, 1):
                metadata = source.get('metadata', {})
                print(f"   {j}. {metadata.get('type', 'unknown')} - Score: {source.get('score', 0):.3f}")
                if metadata.get('mod_title'):
                    print(f"      Mod: {metadata['mod_title']}")
                elif metadata.get('file_path'):
                    print(f"      File: {metadata['file_path']}")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing Simple Query Router")
    test_queries()
    print("\n✅ Testing completed!")