#!/usr/bin/env python3
import requests
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# Configuration
OLLAMA_URL = "http://localhost:11434"
DATA_HOST = "http://localhost:5081"

# Initialize components
emb = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
llm = OllamaLLM(model="llama3", base_url=OLLAMA_URL)

def semantic_search(query, top_k=5, score_threshold=0.3):
    """Perform semantic search and return relevant context"""
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
        if response.status_code == 200:
            results = response.json()
            # Filter by score threshold
            filtered_matches = [
                match for match in results.get('matches', [])
                if match.get('score', 0) >= score_threshold
            ]
            return filtered_matches
        else:
            print(f"❌ Search failed: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

def format_context(matches):
    """Format search results into context for the LLM"""
    if not matches:
        return "No relevant information found in the modpack database."
    
    context_parts = []
    
    for match in matches:
        metadata = match.get('metadata', {})
        doc_type = metadata.get('type', 'unknown')
        score = match.get('score', 0)
        
        if doc_type == 'pack_overview':
            context_parts.append(f"MODPACK OVERVIEW (relevance: {score:.3f}):")
            context_parts.append(f"- Pack: {metadata.get('pack_name')} v{metadata.get('pack_version')}")
            context_parts.append(f"- Contains {metadata.get('mod_count', 'unknown')} mods")
            
        elif doc_type == 'base_mod':
            context_parts.append(f"MOD INFO (relevance: {score:.3f}):")
            context_parts.append(f"- Mod: {metadata.get('mod_title', 'Unknown')}")
            context_parts.append(f"- Project ID: {metadata.get('project_id')}")
            context_parts.append(f"- Source: {metadata.get('source', 'unknown')}")
            context_parts.append(f"- In pack: {metadata.get('pack_name')} v{metadata.get('pack_version')}")
            
        elif doc_type == 'pack_override':
            context_parts.append(f"CONFIGURATION OVERRIDE (relevance: {score:.3f}):")
            context_parts.append(f"- File: {metadata.get('file_path', 'unknown')}")
            context_parts.append(f"- Type: {metadata.get('override_type', 'unknown')}")
            context_parts.append(f"- Pack: {metadata.get('pack_name')} v{metadata.get('pack_version')}")
        
        context_parts.append("")  # Empty line between entries
    
    return "\n".join(context_parts)

def create_prompt(user_query, context):
    """Create a prompt for the LLM with context and query"""
    prompt = f"""You are a helpful assistant that answers questions about Minecraft modpacks. You have access to information about mods, configurations, and pack details.

CONTEXT FROM MODPACK DATABASE:
{context}

USER QUESTION: {user_query}

Please provide a helpful and accurate answer based on the context provided. If the context doesn't contain enough information to fully answer the question, say so and provide what information you can. Be specific about mod names, versions, and configurations when available.

ANSWER:"""
    
    return prompt

def rag_chat(user_query, top_k=5, score_threshold=0.3):
    """Perform RAG: Retrieve relevant context and generate response"""
    print(f"🔍 Searching for: '{user_query}'")
    
    # Retrieve relevant context
    matches = semantic_search(user_query, top_k=top_k, score_threshold=score_threshold)
    
    if not matches:
        return "I couldn't find any relevant information in the modpack database for your query."
    
    print(f"📚 Found {len(matches)} relevant documents")
    
    # Format context
    context = format_context(matches)
    
    # Create prompt
    prompt = create_prompt(user_query, context)
    
    print("🤖 Generating response...")
    
    # Generate response
    try:
        response = llm.invoke(prompt)
        return response
    except Exception as e:
        return f"Error generating response: {e}"

def main():
    print("🚀 RAG Chat System - Minecraft Modpack Assistant")
    print("=" * 60)
    print("Ask questions about the Enigmatica9Expert modpack!")
    print("Type 'quit' to exit, 'help' for example questions")
    print()
    
    # Example questions
    example_questions = [
        "What mods are in this modpack?",
        "Tell me about the Mekanism mods",
        "What KubeJS configurations are there?",
        "How is EMI configured in this pack?",
        "What are the JEI customizations?",
        "Are there any client-side only mods?"
    ]
    
    while True:
        try:
            user_input = input("💬 Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input.lower() == 'help':
                print("\n📝 Example questions you can ask:")
                for i, q in enumerate(example_questions, 1):
                    print(f"   {i}. {q}")
                print()
                continue
            elif not user_input:
                continue
            
            print()
            # Get RAG response
            response = rag_chat(user_input)
            
            print("🤖 Assistant:")
            print(response)
            print("\n" + "-" * 60)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Thanks for using the RAG Chat System!")

if __name__ == "__main__":
    main()