"""Basic tests for upload endpoint"""
import requests
import time
from pathlib import Path


BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code}")
    print(response.json())
    assert response.status_code == 200


def test_single_file_upload():
    """Test uploading a single PDF file"""
    # Note: You need a test PDF file in the tests directory
    test_file = Path(__file__).parent / "sample.pdf"
    
    if not test_file.exists():
        print("⚠️  Warning: sample.pdf not found. Create a sample PDF for testing.")
        return
    
    with open(test_file, "rb") as f:
        files = {"files": (test_file.name, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print(f"Upload response: {response.status_code}")
    data = response.json()
    print(data)
    
    assert response.status_code == 202
    assert "task_ids" in data
    assert len(data["task_ids"]) == 1
    
    task_id = data["task_ids"][0]
    
    # Poll for completion
    for _ in range(30):  # Max 30 seconds
        status_response = requests.get(f"{BASE_URL}/status/{task_id}")
        status_data = status_response.json()
        print(f"Status: {status_data['status']} - Progress: {status_data['progress']}%")
        
        if status_data["status"] == "COMPLETED":
            # Get results
            result_response = requests.get(f"{BASE_URL}/result/{task_id}")
            result_data = result_response.json()
            print(f"✅ Extraction complete!")
            print(f"   Pages: {result_data['page_count']}")
            print(f"   Text length: {len(result_data['text'])} chars")
            print(f"   Tables: {len(result_data['tables'])}")
            print(f"   Images: {len(result_data['images'])}")
            break
        
        time.sleep(1)


def test_multiple_file_upload():
    """Test uploading multiple PDF files"""
    # Note: You need multiple test PDF files
    test_files = [
        Path(__file__).parent / "sample.pdf",
        Path(__file__).parent / "sample2.pdf",
    ]
    
    existing_files = [f for f in test_files if f.exists()]
    
    if not existing_files:
        print("⚠️  Warning: No test PDF files found.")
        return
    
    files = [("files", (f.name, open(f, "rb"), "application/pdf")) for f in existing_files]
    
    response = requests.post(f"{BASE_URL}/upload", files=files)
    
    # Close file handles
    for _, (_, fh, _) in files:
        fh.close()
    
    print(f"Multiple upload response: {response.status_code}")
    data = response.json()
    print(data)
    
    assert response.status_code == 202
    assert len(data["task_ids"]) == len(existing_files)


def test_invalid_file_type():
    """Test uploading non-PDF file"""
    # Create a fake text file
    fake_file = ("files", ("test.txt", b"Not a PDF", "text/plain"))
    
    response = requests.post(f"{BASE_URL}/upload", files=[fake_file])
    
    print(f"Invalid file response: {response.status_code}")
    print(response.json())
    
    assert response.status_code == 400


if __name__ == "__main__":
    print("🧪 Running basic tests...\n")
    
    print("1. Testing health check...")
    test_health_check()
    print()
    
    print("2. Testing single file upload...")
    test_single_file_upload()
    print()
    
    print("3. Testing multiple file upload...")
    test_multiple_file_upload()
    print()
    
    print("4. Testing invalid file type...")
    test_invalid_file_type()
    print()
    
    print("✅ All tests completed!")
