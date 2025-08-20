"""
Configuration management for the document extraction system.
"""

import os
import json
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the document extraction system."""
    
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
    
    # OCR Configuration - Default to EasyOCR on Windows for better compatibility
    import platform
    default_ocr = "easyocr" if platform.system() == "Windows" else "tesseract"
    OCR_ENGINE = os.getenv("OCR_ENGINE", default_ocr)
    
    # Confidence Configuration
    LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.7"))
    
    # Self-consistency Configuration
    SELF_CONSISTENCY_RUNS = int(os.getenv("SELF_CONSISTENCY_RUNS", "3"))
    
    # Paths
    CONFIG_DIR = Path(__file__).parent
    PROJECT_ROOT = CONFIG_DIR.parent
    DATA_DIR = PROJECT_ROOT / "data"
    UTILS_DIR = PROJECT_ROOT / "utils"
    
    # Supported document types
    SUPPORTED_DOC_TYPES = ["invoice", "bill", "prescription"]
    
    # File extensions
    SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]
    SUPPORTED_PDF_EXTENSIONS = [".pdf"]
    SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_PDF_EXTENSIONS
    
    @classmethod
    def get_schema(cls, doc_type: str) -> Dict[str, Any]:
        """Load JSON schema for a specific document type."""
        schema_file = cls.CONFIG_DIR / f"{doc_type}_schema.json"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_all_schemas(cls) -> Dict[str, Dict[str, Any]]:
        """Load all available schemas."""
        schemas = {}
        for doc_type in cls.SUPPORTED_DOC_TYPES:
            try:
                schemas[doc_type] = cls.get_schema(doc_type)
            except FileNotFoundError:
                print(f"Warning: Schema not found for {doc_type}")
        return schemas
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings."""
        if not cls.GEMINI_API_KEY:
            print("Error: GEMINI_API_KEY not found in environment variables")
            return False
        
        if cls.OCR_ENGINE not in ["tesseract", "paddleocr"]:
            print(f"Warning: Unknown OCR engine: {cls.OCR_ENGINE}")
        
        return True

# Global config instance
config = Config()

