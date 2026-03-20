"""Utility functions for the document processing system"""
import os
import hashlib
from pathlib import Path
from typing import Optional


def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file
    Useful for detecting duplicate uploads
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes"""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def clean_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing dangerous characters
    """
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove other dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")
    
    return filename


def ensure_directory_exists(directory: str) -> None:
    """Create directory if it doesn't exist"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes into human-readable string
    Example: 1024 -> "1.00 KB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def parse_file_extension(filename: str) -> str:
    """
    Extract file extension from filename
    Returns: extension with dot (e.g., ".pdf")
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_valid_pdf(file_path: str) -> bool:
    """
    Quick check if file is a valid PDF by checking header
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except Exception:
        return False
