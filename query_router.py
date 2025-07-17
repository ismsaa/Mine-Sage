#!/usr/bin/env python3
import requests
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.schema import BaseRetriever, Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from typing import List
import json

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

class PineconeRetriever(BaseRetriever):
    """Custom LangChain retriever for Pinecone Local"""
    
    def __init__(self, embeddings, data_host, top_k=5, score_threshold=0.3):
        super().__init__()
        self._embeddings = embeddings
        self._data_host = data_host
        self._top_k = top_k
        self._score_threshold = score_threshold
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve relevant documents from Pinecone Local"""
        try:
            # Generate embedding for the query
            query_embedding = self._embeddings.embed_query(query)
            
            # Search Pinecone
            search_payload = {
                "vector": query_embedding,
                "topK": self._top_k,
                "includeMetadata": True,
                "includeValues": False
            }
            
            response = requests.post(f"{self._data_host}/query", json=search_payload)
            if response.status_code != 200:
                return []
            
            results = response.json()
            documents = []
            
            for match in results.get('matches', []):
                if match.get('score', 0) >= self._score_threshold:
                    # Create LangChain Document
                    metadata = match.get('metadata', {})
                    
                    # Create content based on document type
                    content = self._format_document_content(match['id'], metadata)
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            **metadata,
                            'id': match['id'],
                            'score': match.get('score', 0)
                        }
                    )
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ Retrieval error: {e}")
            return []
    
    def _format_document_content(self, doc_id: str, metadata: dict) -> str:
        """Format document content for LLM consumption"""
        doc_type = metadata.get('type', 'unknown')
        
        if doc_type == 'pack_overview':
            return f"""MODPACK: {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', 'Unknown')}
This modpack contains {metadata.get('mod_count', 'unknown')} mods and provides a comprehensive Minecraft experience."""
            
        elif doc_type == 'base_mod':
            return f"""MOD: {metadata.get('mod_title', 'Unknown')}
- Project ID: {metadata.get('project_id', 'unknown')}
- Source: {metadata.get('source', 'unknown')}
- Included in: {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', 'Unknown')}
This mod is part of the modpack and contributes to the overall gameplay experience."""
            
        elif doc_type == 'pack_override':
            return f"""CONFIGURATION: {metadata.get('file_path', 'Unknown')}
- Type: {metadata.get('override_type', 'unknown')} configuration
- Pack: {metadata.get('pack_name', 'Unknown')} v{metadata.get('pack_version', 'Unknown')}
This configuration file customizes mod behavior specifically for this modpack."""
        
        return f"Document ID: {doc_id}"

class ModpackQueryRouter:
    """Router that handles different types of modpack queries"""
    
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
        self.llm = OllamaLLM(model="llama3", base_url=OLLAMA_URL)
        self.retriever = PineconeRetriever(
            embeddings=self.embeddings,
            data_host=DATA_HOST,
            top_k=5,
            score_threshold=0.3
        )
        
        # Create different prompt templates for different query types
        self.general_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful Minecraft modpack assistant. Use the following context to answer the user's question about the modpack.

Context:
{context}

Question: {question}

Provide a helpful and accurate answer based on the context. If you need more information, say so.

Answer:"""
        )
        
        self.mod_specific_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a Minecraft mod expert. The user is asking about specific mods in a modpack. Use the context to provide detailed information about the mods.

Context:
{context}

Question: {question}

Focus on mod names, versions, features, and how they work together in this modpack.

Answer:"""
        )
        
        self.config_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a modpack configuration expert. The user is asking about configurations, scripts, or customizations in the modpack.

Context:
{context}

Question: {question}

Focus on configuration files, KubeJS scripts, and how the modpack customizes mod behavior.

Answer:"""
        )
    
    def classify_query(self, query: str) -> str:
        """Classify the type of query to route to appropriate handler"""
        query_lower = query.lower()
        
        # Configuration-related keywords
        config_keywords = ['kubejs', 'config', 'script', 'override', 'configuration', 'jei', 'emi', 'customize']
        if any(keyword in query_lower for keyword in config_keywords):
            return 'configuration'
        
        # Mod-specific keywords
        mod_keywords = ['mod', 'mods', 'mekanism', 'applied', 'sophisticated', 'generator']
        if any(keyword in query_lower for keyword in mod_keywords):
            return 'mod_specific'
        
        # Default to general
        return 'general'
    
    def route_query(self, query: str) -> str:
        """Route query to appropriate handler and return response"""
        query_type = self.classify_query(query)
        
        print(f"🎯 Query type: {query_type}")
        
        # Select appropriate template
        if query_type == 'configuration':
            template = self.config_template
        elif query_type == 'mod_specific':
            template = self.mod_specific_template
        else:
            template = self.general_template
        
        # Create RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": template},
            return_source_documents=True
        )
        
        # Get response
        try:
            result = qa_chain({"query": query})
            return result["result"], result.get("source_documents", [])
        except Exception as e:
            return f"Error processing query: {e}", []

def main():
    print("🚀 LangChain Query Router - Modpack Assistant")
    print("=" * 60)
    print("Advanced RAG system with intelligent query routing!")
    print("Type 'quit' to exit, 'help' for example questions")
    print()
    
    router = ModpackQueryRouter()
    
    example_questions = [
        "What mods are in this modpack?",
        "Tell me about Mekanism mods",
        "What KubeJS configurations exist?",
        "How is JEI customized?",
        "What are the EMI overrides?",
        "List all the configuration files"
    ]
    
    while True:
        try:
            user_input = input("💬 Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input.lower() == 'help':
                print("\n📝 Example questions:")
                for i, q in enumerate(example_questions, 1):
                    print(f"   {i}. {q}")
                print()
                continue
            elif not user_input:
                continue
            
            print(f"\n🔍 Processing: '{user_input}'")
            
            # Route query and get response
            response, sources = router.route_query(user_input)
            
            print("\n🤖 Assistant:")
            print(response)
            
            if sources:
                print(f"\n📚 Sources ({len(sources)} documents):")
                for i, doc in enumerate(sources[:3], 1):  # Show top 3 sources
                    metadata = doc.metadata
                    print(f"   {i}. {metadata.get('type', 'unknown')} - Score: {metadata.get('score', 0):.3f}")
                    if metadata.get('mod_title'):
                        print(f"      Mod: {metadata['mod_title']}")
                    if metadata.get('file_path'):
                        print(f"      File: {metadata['file_path']}")
            
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Thanks for using the Query Router!")

if __name__ == "__main__":
    main()