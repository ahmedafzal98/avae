"""Redis connection, decorators, and generators"""
import time
import functools
import logging
from typing import Generator, Dict, Any, Optional
from datetime import datetime
import redis
from fastapi import Request, HTTPException
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============= REDIS CONNECTION =============

def get_redis_client() -> redis.Redis:
    """Get Redis client instance — uses REDIS_URL if set, otherwise individual params."""
    if settings.redis_url_override:
        from urllib.parse import urlparse
        url = settings.redis_url_override
        parsed = urlparse(url)
        use_ssl = parsed.scheme in ("rediss",)
        return redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            username=parsed.username if parsed.username != "default" else None,
            ssl=use_ssl,
            ssl_cert_reqs=None,
            decode_responses=True,
        )
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
        decode_responses=True
    )


redis_client = get_redis_client()


# ============= DECORATORS =============

def timeit(func):
    """
    Decorator: Logs execution time of functions
    Professional use case: Performance monitoring for API endpoints and Celery tasks
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"⏱️  {func.__name__} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func.__name__} failed after {elapsed:.2f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"⏱️  {func.__name__} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func.__name__} failed after {elapsed:.2f}s: {str(e)}")
            raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def rate_limit(max_requests: int = None, window_seconds: int = None):
    """
    Decorator: Rate limiting using Redis sliding window
    Professional use case: Prevents system abuse (e.g., max 10 uploads/min per IP)
    """
    max_reqs = max_requests or settings.rate_limit_requests
    window = window_seconds or settings.rate_limit_window
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object from args/kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            
            if request:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"
                endpoint = request.url.path
                
                # Redis key for rate limiting
                rate_key = f"rate_limit:{client_ip}:{endpoint}"
                
                try:
                    # Get current count
                    current_count = redis_client.get(rate_key)
                    
                    if current_count and int(current_count) >= max_reqs:
                        logger.warning(f"🚫 Rate limit exceeded for {client_ip} on {endpoint}")
                        raise HTTPException(
                            status_code=429,
                            detail=f"Rate limit exceeded. Max {max_reqs} requests per {window} seconds."
                        )
                    
                    # Increment counter
                    pipe = redis_client.pipeline()
                    pipe.incr(rate_key)
                    pipe.expire(rate_key, window)
                    pipe.execute()
                    
                except redis.RedisError as e:
                    logger.error(f"Redis error in rate limiting: {e}")
                    # Fail open: allow request if Redis is down
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def log_request(func):
    """
    Decorator: Logs request details for audit trail
    Professional use case: Compliance, debugging, security monitoring
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request object
        request: Optional[Request] = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            request = kwargs.get('request')
        
        if request:
            client_ip = request.client.host if request.client else "unknown"
            method = request.method
            url = str(request.url)
            timestamp = datetime.now().isoformat()
            
            logger.info(f"📝 [{timestamp}] {method} {url} from {client_ip}")
        
        return await func(*args, **kwargs)
    return wrapper


# ============= GENERATORS =============

def read_file_in_chunks(file_path: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """
    Generator: Reads file in chunks for memory efficiency
    Professional use case: Handle 500MB+ PDF files without loading entire file into memory
    
    Args:
        file_path: Path to file
        chunk_size: Size of each chunk in bytes (default 8KB)
    
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
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def get_all_tasks_generator(batch_size: int = 50) -> Generator[Dict[str, Any], None, None]:
    """
    Generator: Yields tasks from Redis in batches
    Professional use case: Pagination for 500+ tasks without loading all into memory
    
    Args:
        batch_size: Number of tasks to fetch per batch
    
    Yields:
        dict: Task data
    """
    try:
        # Get all task IDs
        task_ids = redis_client.lrange("all_tasks", 0, -1)
        
        # Process in batches
        for i in range(0, len(task_ids), batch_size):
            batch = task_ids[i:i + batch_size]
            
            for task_id in batch:
                task_data = redis_client.hgetall(f"task:{task_id}")
                if task_data:
                    yield task_data
    
    except redis.RedisError as e:
        logger.error(f"Redis error in get_all_tasks_generator: {e}")
        raise


def stream_task_results(task_id: str) -> Generator[str, None, None]:
    """
    Generator: Streams task results in JSON lines format
    Professional use case: Large result sets without overwhelming client
    
    Args:
        task_id: Task identifier
    
    Yields:
        str: JSON string per line
    """
    try:
        # Get result from Redis
        result_json = redis_client.get(f"result:{task_id}")
        if result_json:
            # For demonstration, yield the entire result
            # In production, could yield page-by-page results
            yield result_json + "\n"
        else:
            yield '{"error": "Result not found"}\n'
    
    except redis.RedisError as e:
        logger.error(f"Redis error in stream_task_results: {e}")
        yield f'{{"error": "Redis error: {str(e)}"}}\n'


# Need to import asyncio for checking coroutine functions
import asyncio
