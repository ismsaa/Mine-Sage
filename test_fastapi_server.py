#!/usr/bin/env python3
import requests
import json
import time
import subprocess
import signal
import os

# Configuration
SERVER_URL = "http://localhost:8000"

def start_server():
    """Start the FastAPI server in background"""
    try:
        # Start server process
        process = subprocess.Popen([
            "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        return process
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_search_endpoint():
    """Test the search endpoint"""
    try:
        payload = {
            "query": "mekanism mods",
            "top_k": 3,
            "score_threshold": 0.3
        }
        
        response = requests.post(f"{SERVER_URL}/search", json=payload)
        if response.status_code == 200:
            results = response.json()
            print("✅ Search endpoint working")
            print(f"   Found {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result['content']} (Score: {result['score']:.3f})")
            return True
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Search endpoint error: {e}")
        return False

def test_chat_endpoint():
    """Test the chat endpoint"""
    try:
        payload = {
            "message": "What mods are in this modpack?",
            "top_k": 3,
            "score_threshold": 0.3
        }
        
        response = requests.post(f"{SERVER_URL}/chat", json=payload)
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat endpoint working")
            print(f"   Response length: {len(result['response'])} chars")
            print(f"   Sources: {len(result['sources'])}")
            print(f"   Preview: {result['response'][:100]}...")
            return True
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
        return False

def test_openwebui_tools():
    """Test OpenWebUI tool endpoints"""
    try:
        # Test search tool
        search_payload = {"query": "mekanism"}
        response = requests.post(f"{SERVER_URL}/tools/modpack_search", json=search_payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OpenWebUI search tool working")
            print(f"   Results: {result.get('total', 0)}")
        else:
            print(f"❌ OpenWebUI search tool failed: {response.status_code}")
            return False
        
        # Test chat tool
        chat_payload = {"message": "tell me about this modpack"}
        response = requests.post(f"{SERVER_URL}/tools/modpack_chat", json=chat_payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OpenWebUI chat tool working")
            print(f"   Sources: {result.get('sources_count', 0)}")
            return True
        else:
            print(f"❌ OpenWebUI chat tool failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ OpenWebUI tools error: {e}")
        return False

def main():
    print("🚀 Testing FastAPI Server")
    print("=" * 50)
    
    # Check if server is already running
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        server_running = response.status_code == 200
        server_process = None
    except:
        server_running = False
        print("📡 Starting FastAPI server...")
        server_process = start_server()
        
        if not server_process:
            print("❌ Failed to start server")
            return
        
        # Wait for server to be ready
        for i in range(10):
            try:
                response = requests.get(f"{SERVER_URL}/health", timeout=1)
                if response.status_code == 200:
                    server_running = True
                    break
            except:
                pass
            time.sleep(1)
    
    if not server_running:
        print("❌ Server not responding")
        return
    
    print("✅ Server is running")
    print()
    
    # Run tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Search Endpoint", test_search_endpoint),
        ("Chat Endpoint", test_chat_endpoint),
        ("OpenWebUI Tools", test_openwebui_tools),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🧪 Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("📊 Test Results:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {passed/total*100:.1f}%")
    
    # Cleanup
    if server_process:
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
    
    print("✅ Testing completed!")

if __name__ == "__main__":
    main()