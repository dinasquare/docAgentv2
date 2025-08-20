"""
Tests for document classification module.
"""

import unittest
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.doc_classifier import DocumentClassifier

class TestDocumentClassifier(unittest.TestCase):
    """Test cases for document classifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.classifier = DocumentClassifier()
        
        # Sample text for each document type
        self.invoice_text = """
        INVOICE
        Invoice Number: INV-2024-001
        Date: March 15, 2024
        Bill To: ABC Company
        Item: Consulting Services
        Quantity: 10
        Rate: $150.00
        Subtotal: $1,500.00
        Tax: $120.00
        Total: $1,620.00
        """
        
        self.bill_text = """
        ELECTRIC BILL
        Account Number: 123456789
        Statement Date: February 1, 2024
        Billing Period: January 1 - January 31, 2024
        Previous Balance: $123.45
        Current Charges: $89.12
        Total Amount Due: $212.57
        Payment Due Date: February 28, 2024
        """
        
        self.prescription_text = """
        PRESCRIPTION
        Rx Number: 1234567
        Patient: John Doe
        Prescriber: Dr. Smith
        Medication: Amoxicillin 500mg
        Quantity: 30 tablets
        Directions: Take 1 tablet twice daily
        Refills: 2
        """
    
    def test_classifier_initialization(self):
        """Test classifier initialization."""
        self.assertIsInstance(self.classifier.invoice_keywords, list)
        self.assertIsInstance(self.classifier.bill_keywords, list)
        self.assertIsInstance(self.classifier.prescription_keywords, list)
        
        # Check that keywords are present
        self.assertGreater(len(self.classifier.invoice_keywords), 0)
        self.assertGreater(len(self.classifier.bill_keywords), 0)
        self.assertGreater(len(self.classifier.prescription_keywords), 0)
    
    def test_invoice_classification(self):
        """Test invoice classification."""
        doc_type, confidence = self.classifier.classify_by_heuristics(self.invoice_text)
        
        self.assertEqual(doc_type, 'invoice')
        self.assertGreater(confidence, 0.5)
    
    def test_bill_classification(self):
        """Test bill classification."""
        doc_type, confidence = self.classifier.classify_by_heuristics(self.bill_text)
        
        self.assertEqual(doc_type, 'bill')
        self.assertGreater(confidence, 0.5)
    
    def test_prescription_classification(self):
        """Test prescription classification."""
        doc_type, confidence = self.classifier.classify_by_heuristics(self.prescription_text)
        
        self.assertEqual(doc_type, 'prescription')
        self.assertGreater(confidence, 0.5)
    
    def test_keyword_counting(self):
        """Test keyword counting functionality."""
        # Test with invoice keywords
        count = self.classifier._count_keywords(
            self.invoice_text.lower(), 
            self.classifier.invoice_keywords
        )
        self.assertGreater(count, 0)
    
    def test_pattern_matching(self):
        """Test pattern matching functionality."""
        patterns = self.classifier._pattern_matching(self.invoice_text.lower())
        
        self.assertIsInstance(patterns, dict)
        self.assertIn('invoice', patterns)
        self.assertIn('bill', patterns)
        self.assertIn('prescription', patterns)
        
        # Invoice text should have higher invoice pattern score
        self.assertGreaterEqual(patterns['invoice'], patterns['bill'])
        self.assertGreaterEqual(patterns['invoice'], patterns['prescription'])
    
    def test_empty_text_classification(self):
        """Test classification with empty text."""
        doc_type, confidence = self.classifier.classify_by_heuristics("")
        
        self.assertIsNone(doc_type)
        self.assertEqual(confidence, 0.0)
    
    def test_ambiguous_text_classification(self):
        """Test classification with ambiguous text."""
        ambiguous_text = "This is some random text without clear indicators."
        doc_type, confidence = self.classifier.classify_by_heuristics(ambiguous_text)
        
        # Should either return None or low confidence
        if doc_type is not None:
            self.assertLess(confidence, 0.6)
        else:
            self.assertEqual(confidence, 0.0)
    
    def test_classify_method(self):
        """Test the main classify method."""
        # Test without Gemini extractor (heuristics only)
        doc_type, confidence = self.classifier.classify(self.invoice_text)
        
        self.assertIn(doc_type, ['invoice', 'bill', 'prescription'])
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

if __name__ == '__main__':
    unittest.main()

