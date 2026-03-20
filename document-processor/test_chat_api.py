"""
Test script for the RAG Chat API endpoint
Run this after starting the FastAPI server
"""
import requests
import json

# Configuration
API_URL = "http://localhost:8000/chat"
USER_ID = 1
DOCUMENT_ID = 15  # Change this to your document ID

def test_chat(question: str, document_id: int = None):
    """Test the chat endpoint with a question"""
    
    print(f"\n{'='*70}")
    print(f"📝 Question: {question}")
    print(f"{'='*70}\n")
    
    # Prepare request
    payload = {
        "question": question,
        "top_k": 5
    }
    
    if document_id:
        payload["document_id"] = document_id
    
    params = {"user_id": USER_ID}
    
    try:
        # Make request
        print("🔄 Sending request to API...")
        response = requests.post(API_URL, json=payload, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        
        # Display results
        print(f"\n💬 Answer:")
        print(f"{result['answer']}\n")
        
        if result.get('chunks_found', 0) > 0:
            print(f"📚 Sources ({result['chunks_found']} chunks found):")
            for i, source in enumerate(result.get('sources', []), 1):
                print(f"\n  {i}. {source['filename']} (chunk {source['chunk_index']})")
                print(f"     Similarity: {source['similarity']:.4f}")
                print(f"     Preview: {source['preview'][:100]}...")
        else:
            print("⚠️  No sources found")
        
        if result.get('usage'):
            usage = result['usage']
            print(f"\n💰 Token Usage:")
            print(f"   Prompt: {usage['prompt_tokens']} tokens")
            print(f"   Completion: {usage['completion_tokens']} tokens")
            print(f"   Total: {usage['total_tokens']} tokens")
            print(f"   Estimated cost: ${usage['total_tokens'] * 0.00000015:.6f}")
        
        print(f"\n{'='*70}\n")
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


def main():
    """Run test queries"""
    
    print("\n" + "="*70)
    print("🧪 RAG Chat API Test")
    print("="*70)
    print(f"\nAPI URL: {API_URL}")
    print(f"User ID: {USER_ID}")
    print(f"Document ID: {DOCUMENT_ID}")
    
    # Test 1: General question about document
    test_chat(
        question="What is this document about?",
        document_id=DOCUMENT_ID
    )
    
    # Test 2: Specific information
    test_chat(
        question="What company is mentioned in this document?",
        document_id=DOCUMENT_ID
    )
    
    # Test 3: Question without document_id (searches all documents)
    test_chat(
        question="What financial information is available?",
        document_id=None
    )
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    # Check if server is running
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running!")
            main()
        else:
            print("❌ Server returned non-200 status")
    except requests.exceptions.RequestException:
        print("❌ Server is not running!")
        print("\nPlease start the server first:")
        print("  python -m uvicorn app.main:app --reload")
