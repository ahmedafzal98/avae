"""Load test for 500+ PDF files"""
import os
import time
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
import statistics


BASE_URL = "http://localhost:8000"
MAX_WORKERS = 50  # Number of concurrent upload threads


def create_dummy_pdf(file_path: str):
    """Create a minimal valid PDF file for testing"""
    # Minimal PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
    
    with open(file_path, 'wb') as f:
        f.write(pdf_content)


def upload_single_file(file_path: str, file_index: int) -> dict:
    """
    Upload a single PDF file
    Returns: dict with task_id and upload time
    """
    start_time = time.time()
    
    try:
        with open(file_path, 'rb') as f:
            files = {"files": (f"test_{file_index}.pdf", f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)
        
        upload_time = time.time() - start_time
        
        if response.status_code == 202:
            data = response.json()
            return {
                "success": True,
                "task_id": data["task_ids"][0],
                "upload_time": upload_time,
                "index": file_index
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "upload_time": upload_time,
                "index": file_index
            }
    
    except Exception as e:
        upload_time = time.time() - start_time
        return {
            "success": False,
            "error": str(e),
            "upload_time": upload_time,
            "index": file_index
        }


def check_task_status(task_id: str) -> dict:
    """Check the status of a task"""
    try:
        response = requests.get(f"{BASE_URL}/status/{task_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def load_test(num_files: int = 500, use_dummy: bool = True):
    """
    Load test: Upload multiple PDF files concurrently
    
    Args:
        num_files: Number of files to upload
        use_dummy: If True, create dummy PDFs; if False, use existing test files
    """
    print("=" * 80)
    print(f"🚀 LOAD TEST: Uploading {num_files} PDF files")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Prepare test files
    test_dir = Path(__file__).parent / "test_pdfs"
    test_dir.mkdir(exist_ok=True)
    
    test_files = []
    
    if use_dummy:
        print("📝 Creating dummy PDF files...")
        for i in range(num_files):
            file_path = test_dir / f"test_{i}.pdf"
            if not file_path.exists():
                create_dummy_pdf(str(file_path))
            test_files.append((str(file_path), i))
        print(f"✅ Created {num_files} dummy PDF files")
        print()
    else:
        # Use existing sample.pdf repeatedly
        sample_file = Path(__file__).parent / "sample.pdf"
        if not sample_file.exists():
            print("❌ Error: sample.pdf not found. Set use_dummy=True")
            return
        test_files = [(str(sample_file), i) for i in range(num_files)]
    
    # Check system health before starting
    print("🏥 Checking system health...")
    health_response = requests.get(f"{BASE_URL}/health")
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"   Status: {health_data['status']}")
        print(f"   Redis: {'Connected' if health_data['redis_connected'] else 'Disconnected'}")
        print(f"   Queue depth: {health_data['queue_depth']}")
        print()
    
    # Upload files concurrently
    print(f"📤 Uploading {num_files} files with {MAX_WORKERS} concurrent workers...")
    upload_start = time.time()
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(upload_single_file, file_path, index)
            for file_path, index in test_files
        ]
        
        # Show progress
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            if completed % 50 == 0 or completed == num_files:
                print(f"   Progress: {completed}/{num_files} ({(completed/num_files)*100:.1f}%)")
    
    upload_end = time.time()
    upload_duration = upload_end - upload_start
    
    print()
    print("=" * 80)
    print("📊 UPLOAD RESULTS")
    print("=" * 80)
    
    # Analyze results
    successful_uploads = [r for r in results if r["success"]]
    failed_uploads = [r for r in results if not r["success"]]
    
    upload_times = [r["upload_time"] for r in successful_uploads]
    
    print(f"✅ Successful uploads: {len(successful_uploads)}/{num_files}")
    print(f"❌ Failed uploads: {len(failed_uploads)}")
    print(f"⏱️  Total upload time: {upload_duration:.2f} seconds")
    print(f"⚡ Throughput: {num_files/upload_duration:.2f} uploads/second")
    
    if upload_times:
        print(f"📈 Upload time stats:")
        print(f"   Average: {statistics.mean(upload_times):.3f}s")
        print(f"   Median: {statistics.median(upload_times):.3f}s")
        print(f"   Min: {min(upload_times):.3f}s")
        print(f"   Max: {max(upload_times):.3f}s")
    
    if failed_uploads:
        print(f"\n⚠️  Failed upload errors (first 5):")
        for fail in failed_uploads[:5]:
            print(f"   File {fail['index']}: {fail['error']}")
    
    print()
    
    # Monitor task processing
    if successful_uploads:
        print("=" * 80)
        print("⏳ MONITORING TASK PROCESSING")
        print("=" * 80)
        
        task_ids = [r["task_id"] for r in successful_uploads]
        
        # Sample 10 tasks to monitor
        sample_tasks = task_ids[:min(10, len(task_ids))]
        
        print(f"Monitoring {len(sample_tasks)} sample tasks...")
        print()
        
        max_wait = 300  # 5 minutes max
        start_monitor = time.time()
        
        completed_tasks = set()
        
        while time.time() - start_monitor < max_wait:
            statuses = {}
            
            for task_id in sample_tasks:
                if task_id not in completed_tasks:
                    status_data = check_task_status(task_id)
                    status = status_data.get("status", "UNKNOWN")
                    progress = status_data.get("progress", 0)
                    
                    statuses[status] = statuses.get(status, 0) + 1
                    
                    if status == "COMPLETED":
                        completed_tasks.add(task_id)
            
            # Print status summary
            status_line = " | ".join([f"{k}: {v}" for k, v in statuses.items()])
            elapsed = int(time.time() - start_monitor)
            print(f"[{elapsed}s] {status_line} (Completed: {len(completed_tasks)}/{len(sample_tasks)})")
            
            # Check if all sampled tasks are complete
            if len(completed_tasks) == len(sample_tasks):
                print()
                print("✅ All sampled tasks completed!")
                break
            
            time.sleep(5)
        
        print()
        
        # Final system health check
        print("=" * 80)
        print("🏁 FINAL SYSTEM HEALTH CHECK")
        print("=" * 80)
        
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"Status: {health_data['status']}")
            print(f"Redis: {'Connected' if health_data['redis_connected'] else 'Disconnected'}")
            print(f"Queue depth: {health_data['queue_depth']}")
        
        print()
        print("=" * 80)
        print(f"✅ LOAD TEST COMPLETED")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)


if __name__ == "__main__":
    # Run load tests with different scales
    
    # Small test first
    print("\n🧪 Running small test (10 files)...")
    load_test(num_files=10, use_dummy=True)
    
    input("\n⏸️  Press Enter to continue with 500 file test...")
    
    # Full load test
    print("\n🔥 Running full load test (500 files)...")
    load_test(num_files=500, use_dummy=True)
