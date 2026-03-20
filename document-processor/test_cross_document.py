"""
Test script to verify cross-document search is working
"""
import requests
import json

API_BASE = "http://localhost:8000"
USER_ID = 1

def test_question(question: str, document_id=None):
    """Test a question and show what chunks were retrieved"""
    print(f"\n{'='*80}")
    print(f"❓ QUESTION: {question}")
    print(f"📁 Document ID: {document_id if document_id else 'ALL DOCUMENTS (Cross-Search)'}")
    print(f"{'='*80}\n")
    
    payload = {"question": question}
    if document_id:
        payload["document_id"] = document_id
    
    try:
        response = requests.post(
            f"{API_BASE}/chat",
            params={"user_id": USER_ID},
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ ANSWER:")
        print(f"{result['answer']}\n")
        
        if result.get('sources'):
            print(f"📚 SOURCES ({len(result['sources'])} chunks retrieved):")
            for i, source in enumerate(result['sources'], 1):
                print(f"\n  {i}. {source['filename']} (Chunk {source['chunk_id']})")
                print(f"     Similarity: {source.get('similarity_score', 'N/A')}")
                # Show first 150 chars of the chunk
                chunk_preview = source.get('text_preview', '')[:150]
                print(f"     Preview: {chunk_preview}...")
        
        if result.get('usage'):
            print(f"\n💰 COST:")
            print(f"  Prompt: {result['usage']['prompt_tokens']} tokens")
            print(f"  Response: {result['usage']['completion_tokens']} tokens")
            print(f"  Total: {result['usage']['total_tokens']} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Cross-Document Search Functionality")
    print("=" * 80)
    
    # Test 1: Very general question (should definitely work)
    test_question("What companies are mentioned in my documents?")
    
    # Test 2: Specific to Lucky Cement
    test_question("What does Lucky Cement do?")
    
    # Test 3: Risk management (visible in sample chunks)
    test_question("Tell me about risk management practices")
    
    # Test 4: The original revenue question
    test_question("Which company has the highest revenue?")
    
    print(f"\n{'='*80}")
    print("✅ Test Complete!")
    print(f"{'='*80}\n")
