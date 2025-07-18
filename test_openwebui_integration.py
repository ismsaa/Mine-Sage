#!/usr/bin/env python3
"""
Test OpenWebUI Integration End-to-End

This script tests the complete integration between our RAG system and OpenWebUI.
"""

import requests
import json
import time
from typing import Dict

# Configuration
OPENWEBUI_URL = "http://localhost:3000"
RAG_API_BASE = "http://localhost:8001"

def test_rag_api_endpoints():
    """Test all RAG API endpoints"""
    print("🧪 Testing RAG API Endpoints")
    print("-" * 40)
    
    tests = [
        {
            "name": "Health Check",
            "method": "GET",
            "url": f"{RAG_API_BASE}/health",
            "expected_status": 200
        },
        {
            "name": "Search Endpoint",
            "method": "POST", 
            "url": f"{RAG_API_BASE}/search",
            "payload": {"query": "mekanism", "top_k": 3},
            "expected_status": 200
        },
        {
            "name": "Chat Endpoint",
            "method": "POST",
            "url": f"{RAG_API_BASE}/chat", 
            "payload": {"message": "What is Mekanism?", "top_k": 3},
            "expected_status": 200
        },
        {
            "name": "OpenWebUI Search Tool",
            "method": "POST",
            "url": f"{RAG_API_BASE}/tools/modpack_search",
            "payload": {"query": "thermal"},
            "expected_status": 200
        },
        {
            "name": "OpenWebUI Chat Tool", 
            "method": "POST",
            "url": f"{RAG_API_BASE}/tools/modpack_chat",
            "payload": {"message": "tell me about thermal mods"},
            "expected_status": 200
        }
    ]
    
    passed = 0
    for test in tests:
        try:
            if test["method"] == "GET":
                response = requests.get(test["url"], timeout=10)
            else:
                response = requests.post(test["url"], json=test.get("payload", {}), timeout=30)
            
            if response.status_code == test["expected_status"]:
                print(f"✅ {test['name']}: PASSED")
                passed += 1
            else:
                print(f"❌ {test['name']}: FAILED (status {response.status_code})")
                
        except Exception as e:
            print(f"❌ {test['name']}: ERROR - {e}")
    
    print(f"\n📊 API Tests: {passed}/{len(tests)} passed")
    return passed == len(tests)

def test_openwebui_function_format():
    """Test that our functions match OpenWebUI's expected format"""
    print("\n🧪 Testing OpenWebUI Function Format")
    print("-" * 40)
    
    try:
        # Import our functions
        import openwebui_functions
        
        # Test search function
        search_result = openwebui_functions.search_modpack_info("mekanism", 3)
        print("✅ search_modpack_info: Function callable")
        print(f"   Result type: {type(search_result)}")
        print(f"   Result length: {len(search_result)} chars")
        
        # Test question function
        question_result = openwebui_functions.ask_modpack_question("What is Mekanism?", 3)
        print("✅ ask_modpack_question: Function callable")
        print(f"   Result type: {type(question_result)}")
        print(f"   Result length: {len(question_result)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Function format test failed: {e}")
        return False

def simulate_openwebui_chat():
    """Simulate a chat conversation using our tools"""
    print("\n🧪 Simulating OpenWebUI Chat Conversation")
    print("-" * 40)
    
    # Simulate user questions and tool responses
    conversation = [
        {
            "user": "What mods are related to Mekanism?",
            "tool": "search_modpack_info",
            "params": {"query": "mekanism", "top_k": 3}
        },
        {
            "user": "Tell me more about Thermal mods",
            "tool": "ask_modpack_question", 
            "params": {"question": "What are Thermal mods and what do they do?", "context_size": 3}
        },
        {
            "user": "What KubeJS configurations are there?",
            "tool": "search_modpack_info",
            "params": {"query": "kubejs configuration", "top_k": 5}
        }
    ]
    
    try:
        import openwebui_functions
        
        for i, turn in enumerate(conversation, 1):
            print(f"\n💬 Turn {i}: {turn['user']}")
            
            if turn['tool'] == 'search_modpack_info':
                result = openwebui_functions.search_modpack_info(
                    turn['params']['query'], 
                    turn['params']['top_k']
                )
            elif turn['tool'] == 'ask_modpack_question':
                result = openwebui_functions.ask_modpack_question(
                    turn['params']['question'],
                    turn['params']['context_size']
                )
            
            print(f"🤖 Tool Response ({turn['tool']}):")
            print(f"   {result[:200]}..." if len(result) > 200 else f"   {result}")
        
        print("\n✅ Chat simulation completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Chat simulation failed: {e}")
        return False

def check_openwebui_status():
    """Check OpenWebUI status and provide setup instructions"""
    print("\n🧪 Checking OpenWebUI Status")
    print("-" * 40)
    
    try:
        response = requests.get(f"{OPENWEBUI_URL}", timeout=5)
        if response.status_code == 200:
            print("✅ OpenWebUI is accessible at http://localhost:3000")
            
            # Check if we can access the API
            try:
                api_response = requests.get(f"{OPENWEBUI_URL}/api/v1/auths", timeout=5)
                print(f"✅ OpenWebUI API responding (status: {api_response.status_code})")
            except:
                print("⚠️  OpenWebUI API not accessible (may require authentication)")
            
            return True
        else:
            print(f"⚠️  OpenWebUI returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot access OpenWebUI: {e}")
        return False

def main():
    print("🚀 OpenWebUI Integration Test Suite")
    print("=" * 60)
    
    # Test sequence
    tests = [
        ("RAG API Endpoints", test_rag_api_endpoints),
        ("OpenWebUI Function Format", test_openwebui_function_format), 
        ("Chat Simulation", simulate_openwebui_chat),
        ("OpenWebUI Status", check_openwebui_status)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Final results
    print("\n" + "="*60)
    print("🎯 INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"✅ Tests Passed: {passed_tests}/{total_tests}")
    print(f"📊 Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! OpenWebUI integration is ready!")
        print("\n📋 Next Steps:")
        print("1. Visit http://localhost:3000")
        print("2. Create an account or sign in")
        print("3. Go to Settings > Functions")
        print("4. Upload or paste the openwebui_functions.py content")
        print("5. Enable the functions")
        print("6. Start chatting and use the modpack tools!")
        
        print("\n💡 Example prompts to try:")
        print("- 'Search for mekanism mods'")
        print("- 'What mods are in Enigmatica9Expert?'")
        print("- 'Tell me about Thermal Expansion'")
        print("- 'What KubeJS configurations are available?'")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()