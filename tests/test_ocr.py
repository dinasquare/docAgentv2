"""
Tests for OCR processing module.
"""

import unittest
import numpy as np
from PIL import Image
import tempfile
import os
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.ocr import OCRProcessor

class TestOCRProcessor(unittest.TestCase):
    """Test cases for OCR processor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ocr_processor = OCRProcessor(engine="tesseract")
        
        # Create a simple test image with text
        self.test_image = self._create_test_image()
    
    def _create_test_image(self):
        """Create a simple test image with text."""
        # Create a simple white image with black text
        img = Image.new('RGB', (400, 200), color='white')
        
        # You would normally use PIL.ImageDraw to add text
        # For this test, we'll create a simple pattern
        return np.array(img)
    
    def test_processor_initialization(self):
        """Test OCR processor initialization."""
        processor = OCRProcessor(engine="tesseract")
        self.assertEqual(processor.engine, "tesseract")
    
    def test_preprocess_image(self):
        """Test image preprocessing."""
        processed = self.ocr_processor.preprocess_image(self.test_image)
        
        # Check that preprocessing returns an array
        self.assertIsInstance(processed, np.ndarray)
        
        # Check that dimensions are reasonable
        self.assertEqual(len(processed.shape), 2)  # Should be grayscale
    
    def test_extract_text_tesseract(self):
        """Test Tesseract text extraction."""
        result = self.ocr_processor.extract_text_tesseract(self.test_image)
        
        # Check result structure
        self.assertIsInstance(result, dict)
        self.assertIn('text', result)
        self.assertIn('confidence', result)
        self.assertIn('engine', result)
        
        # Check data types
        self.assertIsInstance(result['text'], str)
        self.assertIsInstance(result['confidence'], float)
        self.assertEqual(result['engine'], 'tesseract')
    
    def test_process_text_file(self):
        """Test processing a text file (should handle gracefully)."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Sample invoice text\nInvoice Number: 12345")
            tmp_path = tmp.name
        
        try:
            # This should handle the error gracefully
            result = self.ocr_processor.process_file(tmp_path)
            
            # Should return an empty result structure
            self.assertIsInstance(result, dict)
            self.assertIn('text', result)
            
        finally:
            os.unlink(tmp_path)
    
    def test_empty_result_structure(self):
        """Test empty result structure."""
        result = self.ocr_processor._empty_result("Test error")
        
        expected_keys = ['text', 'confidence', 'word_count', 'page_count', 'engine', 'source', 'pages', 'error']
        
        for key in expected_keys:
            self.assertIn(key, result)
        
        self.assertEqual(result['text'], '')
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['error'], "Test error")

if __name__ == '__main__':
    unittest.main()

