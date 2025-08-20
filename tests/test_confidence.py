"""
Tests for confidence scoring module.
"""

import unittest
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.confidence import ConfidenceScorer

class TestConfidenceScorer(unittest.TestCase):
    """Test cases for confidence scorer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scorer = ConfidenceScorer(low_confidence_threshold=0.7)
        
        self.sample_text = """
        INVOICE INV-2024-001
        Date: 2024-03-15
        Amount: $1,500.00
        Email: test@example.com
        Phone: (555) 123-4567
        """
    
    def test_scorer_initialization(self):
        """Test scorer initialization."""
        self.assertEqual(self.scorer.low_confidence_threshold, 0.7)
    
    def test_date_confidence(self):
        """Test date field confidence assessment."""
        # Valid date formats
        self.assertGreater(self.scorer._date_confidence("2024-03-15"), 0.8)
        self.assertGreater(self.scorer._date_confidence("03/15/2024"), 0.8)
        
        # Invalid date formats
        self.assertLess(self.scorer._date_confidence("invalid-date"), 0.5)
        self.assertLess(self.scorer._date_confidence("2024-13-45"), 0.5)  # Invalid date
    
    def test_amount_confidence(self):
        """Test amount field confidence assessment."""
        # Valid amounts
        self.assertGreater(self.scorer._amount_confidence(150.50), 0.8)
        self.assertGreater(self.scorer._amount_confidence("$1,500.00"), 0.7)
        
        # Invalid amounts
        self.assertLess(self.scorer._amount_confidence(-50.0), 0.7)
        self.assertLess(self.scorer._amount_confidence("not-a-number"), 0.5)
    
    def test_email_confidence(self):
        """Test email field confidence assessment."""
        # Valid email
        self.assertGreater(self.scorer._email_confidence("test@example.com"), 0.9)
        
        # Invalid email
        self.assertLess(self.scorer._email_confidence("invalid-email"), 0.5)
        self.assertLess(self.scorer._email_confidence("test@"), 0.7)
    
    def test_phone_confidence(self):
        """Test phone field confidence assessment."""
        # Valid phone numbers
        self.assertGreater(self.scorer._phone_confidence("(555) 123-4567"), 0.8)
        self.assertGreater(self.scorer._phone_confidence("555-123-4567"), 0.8)
        self.assertGreater(self.scorer._phone_confidence("5551234567"), 0.8)
        
        # Invalid phone numbers
        self.assertLess(self.scorer._phone_confidence("123"), 0.5)
        self.assertLess(self.scorer._phone_confidence("not-a-phone"), 0.5)
    
    def test_text_presence_confidence(self):
        """Test text presence confidence assessment."""
        # Text that exists in original
        self.assertGreater(
            self.scorer._text_presence_confidence("INV-2024-001", self.sample_text),
            0.8
        )
        
        # Text that doesn't exist
        self.assertLess(
            self.scorer._text_presence_confidence("nonexistent-text", self.sample_text),
            0.2
        )
    
    def test_calculate_field_confidence(self):
        """Test field confidence calculation."""
        # Test with different field types
        confidence = self.scorer.calculate_field_confidence(
            "invoice_date", "2024-03-15", self.sample_text, 0.9
        )
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # Test with amount field
        confidence = self.scorer.calculate_field_confidence(
            "total_amount", 1500.00, self.sample_text, 0.8
        )
        self.assertGreater(confidence, 0.5)
    
    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation."""
        field_confidences = {
            'invoice_number': 0.9,
            'date': 0.8,
            'amount': 0.85,
            'vendor.name': 0.7
        }
        
        overall = self.scorer.calculate_overall_confidence(field_confidences)
        
        self.assertIsInstance(overall, float)
        self.assertGreaterEqual(overall, 0.0)
        self.assertLessEqual(overall, 1.0)
        
        # Should be around the average
        expected_avg = sum(field_confidences.values()) / len(field_confidences)
        self.assertAlmostEqual(overall, expected_avg, places=1)
    
    def test_identify_low_confidence_fields(self):
        """Test identification of low confidence fields."""
        field_confidences = {
            'high_conf_field': 0.9,
            'medium_conf_field': 0.75,
            'low_conf_field1': 0.6,
            'low_conf_field2': 0.5
        }
        
        low_fields = self.scorer.identify_low_confidence_fields(field_confidences)
        
        self.assertIsInstance(low_fields, list)
        self.assertEqual(len(low_fields), 2)  # Two fields below 0.7 threshold
        
        # Check that they're sorted by confidence (lowest first)
        confidences = [conf for _, conf in low_fields]
        self.assertEqual(confidences, sorted(confidences))
    
    def test_confidence_summary(self):
        """Test confidence summary generation."""
        field_confidences = {
            'field1': 0.9,  # High
            'field2': 0.7,  # Medium
            'field3': 0.4,  # Low
            'field4': 0.8   # High
        }
        
        overall_confidence = 0.725
        
        summary = self.scorer.get_confidence_summary(field_confidences, overall_confidence)
        
        # Check summary structure
        expected_keys = [
            'overall_confidence', 'field_count', 'low_confidence_count',
            'low_confidence_fields', 'confidence_distribution',
            'average_confidence', 'min_confidence', 'max_confidence'
        ]
        
        for key in expected_keys:
            self.assertIn(key, summary)
        
        # Check specific values
        self.assertEqual(summary['field_count'], 4)
        self.assertEqual(summary['low_confidence_count'], 1)  # Only field3 is below 0.7
        self.assertEqual(summary['confidence_distribution']['high'], 2)  # field1, field4
        self.assertEqual(summary['confidence_distribution']['medium'], 1)  # field2
        self.assertEqual(summary['confidence_distribution']['low'], 1)  # field3

if __name__ == '__main__':
    unittest.main()

