"""PDF processing tasks with LlamaParse integration"""
import os
import json
import logging
import base64
from datetime import datetime
from typing import Generator, Dict, Any, List, Tuple
import PyPDF2
import pdfplumber
from PIL import Image
from io import BytesIO

# LlamaIndex imports
from llama_parse import LlamaParse

from app.celery_app import celery_app
from app.dependencies import redis_client, timeit
from app.config import settings
from app.schemas_api import PDFMetadata, PDFExtractionResult

logger = logging.getLogger(__name__)

# ============= LLAMAPARSE INITIALIZATION =============

# Initialize LlamaParse with Markdown result type for better table preservation
llamaparse_parser = None

def get_llamaparse_parser():
    """
    Lazy initialization of LlamaParse parser
    Returns a configured LlamaParse instance
    """
    global llamaparse_parser
    
    if llamaparse_parser is None:
        try:
            llamaparse_parser = LlamaParse(
                api_key=settings.llama_cloud_api_key,
                result_type="markdown",  # Preserves tables and layout
                verbose=True,
                language="en",
                
                num_workers=1  # Process one page at a time to avoid rate limits
            )
            logger.info("✅ LlamaParse initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LlamaParse: {e}")
            raise
    
    return llamaparse_parser


# ============= GENERATOR FOR PROGRESS UPDATES =============

def process_with_progress(task_id: str, total_steps: int) -> Generator[int, None, None]:
    """
    Generator: Yields progress updates during processing
    Professional use case: Real-time progress tracking for long-running PDF processing
    
    Args:
        task_id: Task identifier
        total_steps: Total number of processing steps
    
    Yields:
        int: Progress percentage (0-100)
    """
    for step in range(total_steps + 1):
        progress = int((step / total_steps) * 100)
        
        # Update progress in Redis
        try:
            redis_client.hset(f"task:{task_id}", "progress", progress)
            logger.info(f"📊 Task {task_id}: {progress}% complete")
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
        
        yield progress


def read_pdf_in_chunks(file_path: str, chunk_size: int = 1024 * 1024) -> Generator[bytes, None, None]:
    """
    Generator: Reads PDF file in chunks
    Professional use case: Memory-efficient reading of large (500MB+) PDF files
    
    Args:
        file_path: Path to PDF file
        chunk_size: Chunk size in bytes (default 1MB)
    
    Yields:
        bytes: File chunks
    """
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.error(f"Error reading PDF in chunks: {e}")
        raise


def extract_pages_generator(pdf_path: str) -> Generator[Dict[str, Any], None, None]:
    """
    Generator: Yields extracted data page by page
    Professional use case: Process large PDFs without loading entire document into memory
    
    Args:
        pdf_path: Path to PDF file
    
    Yields:
        dict: Page data (page number, text, etc.)
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_data = {
                    "page_number": page_num,
                    "text": page.extract_text() or "",
                    "width": page.width,
                    "height": page.height
                }
                yield page_data
    except Exception as e:
        logger.error(f"Error in extract_pages_generator: {e}")
        raise


# ============= PDF EXTRACTION FUNCTIONS =============

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """
    Extract text from PDF using LlamaParse (Cloud API)
    Returns: (markdown_text, page_count)
    
    LlamaParse provides:
    - AI-powered text extraction with better accuracy
    - Automatic table detection and conversion to Markdown
    - OCR support for scanned documents
    - Layout preservation
    """
    try:
        logger.info(f"🚀 Starting LlamaParse extraction for: {pdf_path}")
        
        # Get LlamaParse instance
        parser = get_llamaparse_parser()
        
        # Parse the PDF - returns list of Document objects
        # This is a blocking call that uploads to LlamaCloud and waits for results
        logger.info("📤 Uploading PDF to LlamaCloud...")
        documents = parser.load_data(pdf_path)
        
        logger.info(f"✅ Received {len(documents)} document(s) from LlamaParse")
        
        # Extract text from Document objects
        # Each Document has a 'text' attribute containing Markdown content
        all_text = []
        for doc in documents:
            if hasattr(doc, 'text') and doc.text:
                all_text.append(doc.text)
        
        # Combine all text with double newlines
        markdown_text = '\n\n'.join(all_text)
        
        # Get page count using PyPDF2 as fallback (fast metadata check)
        page_count = 0
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
        except Exception as e:
            logger.warning(f"Could not get page count: {e}")
            # Estimate from document count
            page_count = len(documents)
        
        logger.info(f"✅ Extraction complete: {len(markdown_text)} chars, {page_count} pages")
        return markdown_text, page_count
    
    except Exception as e:
        logger.error(f"❌ LlamaParse extraction failed: {e}")
        logger.warning("⚠️  Falling back to legacy PyPDF2/pdfplumber extraction...")
        
        # Fallback to legacy extraction
        return extract_text_from_pdf_legacy(pdf_path)


def extract_text_from_pdf_legacy(pdf_path: str) -> Tuple[str, int]:
    """
    Legacy: Extract text using PyPDF2 and pdfplumber (fallback only)
    Returns: (text, page_count)
    """
    all_text = []
    page_count = 0
    
    try:
        # Try PyPDF2 first
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
        
        # If PyPDF2 didn't get much text, try pdfplumber
        if len(''.join(all_text).strip()) < 100:
            all_text = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
        
        return '\n\n'.join(all_text), page_count
    
    except Exception as e:
        logger.error(f"Error in legacy extraction: {e}")
        return "", 0






def extract_metadata_from_pdf(pdf_path: str) -> PDFMetadata:
    """
    Extract metadata from PDF using PyPDF2
    Returns: PDFMetadata object
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata
            
            if metadata:
                return PDFMetadata(
                    author=metadata.get('/Author'),
                    creator=metadata.get('/Creator'),
                    producer=metadata.get('/Producer'),
                    subject=metadata.get('/Subject'),
                    title=metadata.get('/Title'),
                    creation_date=str(metadata.get('/CreationDate')) if metadata.get('/CreationDate') else None,
                    modification_date=str(metadata.get('/ModDate')) if metadata.get('/ModDate') else None
                )
    
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
    
    return PDFMetadata()


# ============= MAIN CELERY TASK =============

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff: 60s, 120s, 240s
    retry_backoff_max=600,  # Max 10 minutes between retries
    acks_late=True,
    reject_on_worker_lost=True
)
@timeit
def process_pdf_task(self, task_id: str, file_path: str, filename: str):
    """
    Main Celery task: Process PDF and extract all data
    
    Decorators used:
    - @celery_app.task: Auto-retry with exponential backoff
    - @timeit: Performance monitoring
    
    Generators used:
    - process_with_progress(): Yield progress updates
    - extract_pages_generator(): Memory-efficient page processing
    
    Args:
        self: Celery task instance (bind=True)
        task_id: Unique task identifier
        file_path: Path to uploaded PDF
        filename: Original filename
    """
    start_time = datetime.now()
    
    try:
        # Update status to PROCESSING
        redis_client.hset(f"task:{task_id}", "status", "PROCESSING")
        redis_client.hset(f"task:{task_id}", "started_at", start_time.isoformat())
        
        logger.info(f"🚀 Starting PDF processing: {filename} (Task: {task_id})")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Define processing steps for progress tracking
        total_steps = 3
        progress_gen = process_with_progress(task_id, total_steps)
        
        # Step 1: Extract text
        next(progress_gen)  # 0%
        logger.info(f"📄 Extracting text from {filename}...")
        text, page_count = extract_text_from_pdf(file_path)
        next(progress_gen)  # 33%
        
        # Step 2: Extract metadata
        logger.info(f"ℹ️  Extracting metadata from {filename}...")
        metadata = extract_metadata_from_pdf(file_path)
        next(progress_gen)  # 66%
        
        # Step 3: Compile results
        logger.info(f"💾 Compiling results for {filename}...")
        
        end_time = datetime.now()
        extraction_time = (end_time - start_time).total_seconds()
        
        result = PDFExtractionResult(
            task_id=task_id,
            filename=filename,
            page_count=page_count,
            text=text,
            metadata=metadata,
            extraction_time_seconds=round(extraction_time, 2)
        )
        
        # Store result in Redis with TTL
        result_json = result.model_dump_json()
        redis_client.setex(
            f"result:{task_id}",
            settings.task_result_ttl,
            result_json
        )
        
        # Update task status to COMPLETED
        redis_client.hset(f"task:{task_id}", "status", "COMPLETED")
        redis_client.hset(f"task:{task_id}", "completed_at", end_time.isoformat())
        redis_client.hset(f"task:{task_id}", "progress", 100)
        
        next(progress_gen)  # 100%
        
        logger.info(f"✅ Completed processing {filename} in {extraction_time:.2f}s")
        logger.info(f"   📊 Stats: {page_count} pages, {len(text)} chars")
        
        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "filename": filename,
            "extraction_time_seconds": extraction_time
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error processing {filename}: {error_msg}")
        
        # Update task status to FAILED
        redis_client.hset(f"task:{task_id}", "status", "FAILED")
        redis_client.hset(f"task:{task_id}", "error", error_msg)
        redis_client.hset(f"task:{task_id}", "completed_at", datetime.now().isoformat())
        
        # Re-raise for Celery retry mechanism
        raise self.retry(exc=e)
