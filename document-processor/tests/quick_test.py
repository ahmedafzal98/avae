#!/usr/bin/env python3
"""
Quick test script - Tests entire workflow in one go

Usage:
    python quick_test.py
"""
import requests
import time
import sys
from pathlib import Path


BASE_URL = "http://localhost:8000"
COLORS = {
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'blue': '\033[94m',
    'end': '\033[0m'
}


def print_colored(text, color='green'):
    """Print colored text"""
    print(f"{COLORS.get(color, '')}{text}{COLORS['end']}")


def test_step(step_number, description):
    """Print test step header"""
    print()
    print("=" * 70)
    print(f"Step {step_number}: {description}")
    print("=" * 70)


def main():
    print_colored("🚀 QUICK TEST - Document Processing System", 'blue')
    print_colored("=" * 70, 'blue')
    
    # Step 1: Health Check
    test_step(1, "Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_colored(f"✅ API is healthy", 'green')
            print(f"   Status: {data['status']}")
            print(f"   Redis: {'Connected' if data.get('redis_connected') else 'Disconnected'}")
            print(f"   Queue depth: {data.get('queue_depth', 0)}")
        else:
            print_colored(f"❌ Health check failed: HTTP {response.status_code}", 'red')
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print_colored("❌ Cannot connect to FastAPI server!", 'red')
        print_colored("   Make sure FastAPI is running:", 'yellow')
        print_colored("   uvicorn app.main:app --reload --port 8000", 'yellow')
        sys.exit(1)
    except Exception as e:
        print_colored(f"❌ Error: {e}", 'red')
        sys.exit(1)
    
    # Step 2: Check for test PDF
    test_step(2, "Prepare Test File")
    
    test_file = Path(__file__).parent / "sample.pdf"
    
    if not test_file.exists():
        print_colored("⚠️  sample.pdf not found. Creating one...", 'yellow')
        try:
            from create_sample_pdf import create_sample_pdf
            create_sample_pdf()
        except Exception as e:
            print_colored(f"❌ Could not create sample PDF: {e}", 'red')
            print_colored("   Please run: python create_sample_pdf.py", 'yellow')
            sys.exit(1)
    else:
        file_size_kb = test_file.stat().st_size / 1024
        print_colored(f"✅ Found test file: {test_file.name}", 'green')
        print(f"   Size: {file_size_kb:.2f} KB")
    
    # Step 3: Upload PDF
    test_step(3, "Upload PDF File")
    
    try:
        with open(test_file, "rb") as f:
            files = {"files": (test_file.name, f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)
        
        if response.status_code == 202:
            data = response.json()
            task_id = data["task_ids"][0]
            print_colored(f"✅ Upload successful!", 'green')
            print(f"   Task ID: {task_id}")
            print(f"   Total files: {data['total_files']}")
        else:
            print_colored(f"❌ Upload failed: HTTP {response.status_code}", 'red')
            print(f"   Response: {response.text}")
            sys.exit(1)
    except Exception as e:
        print_colored(f"❌ Upload error: {e}", 'red')
        sys.exit(1)
    
    # Step 4: Poll for completion
    test_step(4, "Monitor Processing")
    
    print("Waiting for processing to complete...")
    print()
    
    max_wait = 60  # 60 seconds max
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BASE_URL}/status/{task_id}", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data['status']
                progress = status_data['progress']
                
                # Only print if status changed
                if status != last_status:
                    elapsed = int(time.time() - start_time)
                    
                    if status == "PENDING":
                        print(f"[{elapsed}s] ⏳ Status: PENDING - Waiting for worker...")
                    elif status == "PROCESSING":
                        print(f"[{elapsed}s] ⚙️  Status: PROCESSING - Progress: {progress}%")
                    elif status == "COMPLETED":
                        print_colored(f"[{elapsed}s] ✅ Status: COMPLETED - Progress: {progress}%", 'green')
                        break
                    elif status == "FAILED":
                        print_colored(f"[{elapsed}s] ❌ Status: FAILED", 'red')
                        error = status_data.get('error', 'Unknown error')
                        print(f"   Error: {error}")
                        sys.exit(1)
                    
                    last_status = status
                
                # If still processing, update progress inline
                if status == "PROCESSING":
                    print(f"\r   Current progress: {progress}%", end='', flush=True)
            else:
                print_colored(f"❌ Status check failed: HTTP {response.status_code}", 'red')
                sys.exit(1)
        
        except Exception as e:
            print_colored(f"❌ Status check error: {e}", 'red')
            sys.exit(1)
        
        time.sleep(2)
    else:
        print_colored(f"\n❌ Timeout: Processing took longer than {max_wait} seconds", 'red')
        print_colored("   This might mean the Celery worker is not running!", 'yellow')
        print_colored("   Start it with:", 'yellow')
        print_colored("   celery -A app.celery_app worker --loglevel=info", 'yellow')
        sys.exit(1)
    
    print()  # New line after inline progress
    
    # Step 5: Get results
    test_step(5, "Retrieve Extraction Results")
    
    try:
        response = requests.get(f"{BASE_URL}/result/{task_id}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            print_colored("✅ Extraction Results:", 'green')
            print(f"   Filename: {result['filename']}")
            print(f"   Page count: {result['page_count']}")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Tables found: {len(result['tables'])}")
            print(f"   Images found: {len(result['images'])}")
            print(f"   Extraction time: {result['extraction_time_seconds']} seconds")
            print()
            
            # Show sample text
            if result['text']:
                sample_text = result['text'][:200].replace('\n', ' ')
                print(f"   Text sample: \"{sample_text}...\"")
            
            # Show metadata if available
            metadata = result.get('metadata', {})
            if metadata and any(metadata.values()):
                print()
                print("   Metadata:")
                if metadata.get('title'):
                    print(f"     Title: {metadata['title']}")
                if metadata.get('author'):
                    print(f"     Author: {metadata['author']}")
                if metadata.get('creator'):
                    print(f"     Creator: {metadata['creator']}")
        else:
            print_colored(f"❌ Failed to get results: HTTP {response.status_code}", 'red')
            sys.exit(1)
    
    except Exception as e:
        print_colored(f"❌ Error retrieving results: {e}", 'red')
        sys.exit(1)
    
    # Final summary
    print()
    print("=" * 70)
    print_colored("🎉 ALL TESTS PASSED!", 'green')
    print("=" * 70)
    print()
    print("Your Document Processing System is working correctly!")
    print()
    print("Next steps:")
    print("  1. Run load test: python load_test.py")
    print("  2. Try the web UI: http://localhost:8000/docs")
    print("  3. Monitor with Flower: celery -A app.celery_app flower")
    print()


if __name__ == "__main__":
    main()
