"""
Input/output helper functions for JSON operations and file handling.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import tempfile
import base64
from .logger import get_logger, timer

logger = get_logger()

@timer(logger)
def save_json(data: Dict[str, Any], file_path: Union[str, Path], 
              pretty: bool = True, backup: bool = True) -> bool:
    """
    Save data to JSON file with error handling and optional backup.
    
    Args:
        data: Data to save
        file_path: Path to save the file
        pretty: Whether to format JSON nicely
        backup: Whether to create backup if file exists
        
    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if file exists and backup is requested
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(f'.backup_{int(datetime.now().timestamp())}.json')
            file_path.rename(backup_path)
            logger.logger.info(f"Created backup: {backup_path}")
        
        # Save JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
        
        logger.logger.info(f"Successfully saved JSON to: {file_path}")
        return True
        
    except Exception as e:
        logger.log_error("save_json", e, file_path=str(file_path))
        return False

@timer(logger)
def load_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file with error handling.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data or None if failed
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.logger.warning(f"JSON file not found: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.logger.info(f"Successfully loaded JSON from: {file_path}")
        return data
        
    except json.JSONDecodeError as e:
        logger.log_error("json_decode", e, file_path=str(file_path))
        return None
    except Exception as e:
        logger.log_error("load_json", e, file_path=str(file_path))
        return None

def save_extraction_result(result: Dict[str, Any], output_dir: Union[str, Path], 
                          filename_prefix: str = "extraction") -> Optional[str]:
    """
    Save extraction result with timestamp and metadata.
    
    Args:
        result: Extraction result to save
        output_dir: Directory to save the file
        filename_prefix: Prefix for the filename
        
    Returns:
        Path to saved file or None if failed
    """
    try:
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        file_path = output_dir / filename
        
        # Add metadata
        result_with_metadata = {
            "extraction_timestamp": datetime.now().isoformat(),
            "version": "1.0",
            **result
        }
        
        if save_json(result_with_metadata, file_path):
            return str(file_path)
        return None
        
    except Exception as e:
        logger.log_error("save_extraction_result", e)
        return None

def create_download_data(data: Dict[str, Any], filename: str = "extraction_result.json") -> Dict[str, str]:
    """
    Create data for Streamlit download.
    
    Args:
        data: Data to prepare for download
        filename: Suggested filename
        
    Returns:
        Dictionary with download data
    """
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        return {
            "data": json_str,
            "filename": filename,
            "mime_type": "application/json",
            "size": len(json_str.encode('utf-8'))
        }
        
    except Exception as e:
        logger.log_error("create_download_data", e)
        return {
            "data": "{}",
            "filename": filename,
            "mime_type": "application/json",
            "size": 2
        }

def encode_file_for_storage(file_bytes: bytes, filename: str) -> Dict[str, str]:
    """
    Encode file bytes for storage/transmission.
    
    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        
    Returns:
        Dictionary with encoded data and metadata
    """
    try:
        encoded_data = base64.b64encode(file_bytes).decode('utf-8')
        
        return {
            "encoded_data": encoded_data,
            "filename": filename,
            "size": len(file_bytes),
            "encoding": "base64"
        }
        
    except Exception as e:
        logger.log_error("encode_file", e)
        return {
            "encoded_data": "",
            "filename": filename,
            "size": 0,
            "encoding": "base64",
            "error": str(e)
        }

def decode_file_from_storage(encoded_data: str) -> Optional[bytes]:
    """
    Decode file bytes from storage.
    
    Args:
        encoded_data: Base64 encoded data
        
    Returns:
        Decoded bytes or None if failed
    """
    try:
        return base64.b64decode(encoded_data)
    except Exception as e:
        logger.log_error("decode_file", e)
        return None

def create_temp_file(content: Union[str, bytes], suffix: str = ".tmp") -> Optional[str]:
    """
    Create a temporary file with content.
    
    Args:
        content: Content to write to temp file
        suffix: File suffix
        
    Returns:
        Path to temp file or None if failed
    """
    try:
        with tempfile.NamedTemporaryFile(mode='wb' if isinstance(content, bytes) else 'w',
                                       suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    except Exception as e:
        logger.log_error("create_temp_file", e)
        return None

def cleanup_temp_file(file_path: str) -> bool:
    """
    Clean up temporary file.
    
    Args:
        file_path: Path to temp file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            return True
        return False
    except Exception as e:
        logger.log_error("cleanup_temp_file", e)
        return False

def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """
    Validate file type based on extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (with dots)
        
    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in [ext.lower() for ext in allowed_extensions]

def get_file_info(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Get information about an uploaded file.
    
    Args:
        file_bytes: File bytes
        filename: Original filename
        
    Returns:
        Dictionary with file information
    """
    file_path = Path(filename)
    
    return {
        "filename": filename,
        "size": len(file_bytes),
        "size_mb": round(len(file_bytes) / (1024 * 1024), 2),
        "extension": file_path.suffix.lower(),
        "stem": file_path.stem,
        "is_pdf": file_path.suffix.lower() == '.pdf',
        "is_image": file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    }

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def create_session_state_key(prefix: str, *args) -> str:
    """
    Create a unique session state key.
    
    Args:
        prefix: Key prefix
        *args: Additional arguments to include in key
        
    Returns:
        Unique session state key
    """
    key_parts = [prefix] + [str(arg) for arg in args]
    return "_".join(key_parts)

def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    import re
    
    # Replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # Remove leading/trailing underscores
    safe_name = safe_name.strip('_')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = "document"
    
    return safe_name

