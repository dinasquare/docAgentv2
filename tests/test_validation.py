"""
Tests for data validation module.
"""

import unittest
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.validation import DataValidator

class TestDataValidator(unittest.TestCase):
    """Test cases for data validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
        
        # Sample valid invoice data
        self.valid_invoice = {
            "document_type": "invoice",
            "invoice_number": "INV-2024-001",
            "date": "2024-03-15",
            "due_date": "2024-04-15",
            "vendor": {
                "name": "TechServices Inc.",
                "address": "123 Business St"
            },
            "customer": {
                "name": "ABC Corp"
            },
            "items": [
                {
                    "description": "Consulting",
                    "quantity": 10,
                    "unit_price": 150.0,
                    "total": 1500.0
                }
            ],
            "subtotal": 1500.0,
            "tax_amount": 120.0,
            "total_amount": 1620.0,
            "currency": "USD"
        }
        
        # Sample valid bill data
        self.valid_bill = {
            "document_type": "bill",
            "bill_number": "123456",
            "statement_date": "2024-02-01",
            "due_date": "2024-02-28",
            "service_provider": {
                "name": "Electric Company"
            },
            "customer": {
                "name": "John Doe"
            },
            "previous_balance": 100.0,
            "current_charges": 50.0,
            "payments": 0.0,
            "total_amount_due": 150.0,
            "currency": "USD"
        }
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        self.assertIsInstance(self.validator.validation_rules, dict)
        self.assertIn('date', self.validator.validation_rules)
        self.assertIn('amount', self.validator.validation_rules)
    
    def test_validate_date(self):
        """Test date validation."""
        # Valid dates
        valid, msg = self.validator._validate_date("2024-03-15")
        self.assertTrue(valid)
        self.assertEqual(msg, "")
        
        valid, msg = self.validator._validate_date("03/15/2024")
        self.assertTrue(valid)
        
        # Invalid dates
        valid, msg = self.validator._validate_date("invalid-date")
        self.assertFalse(valid)
        self.assertIn("Invalid date format", msg)
        
        valid, msg = self.validator._validate_date("2024-13-45")
        self.assertFalse(valid)
    
    def test_validate_amount(self):
        """Test amount validation."""
        # Valid amounts
        valid, msg = self.validator._validate_amount(150.50)
        self.assertTrue(valid)
        
        valid, msg = self.validator._validate_amount("$1,500.00")
        self.assertTrue(valid)
        
        # Invalid amounts
        valid, msg = self.validator._validate_amount(-50.0)
        self.assertFalse(valid)
        self.assertIn("cannot be negative", msg)
        
        valid, msg = self.validator._validate_amount("not-a-number")
        self.assertFalse(valid)
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid email
        valid, msg = self.validator._validate_email("test@example.com")
        self.assertTrue(valid)
        
        # Invalid email
        valid, msg = self.validator._validate_email("invalid-email")
        self.assertFalse(valid)
    
    def test_validate_currency(self):
        """Test currency validation."""
        # Valid currencies
        valid, msg = self.validator._validate_currency("USD")
        self.assertTrue(valid)
        
        valid, msg = self.validator._validate_currency("EUR")
        self.assertTrue(valid)
        
        # Invalid currency
        valid, msg = self.validator._validate_currency("INVALID")
        self.assertFalse(valid)
    
    def test_validate_valid_invoice(self):
        """Test validation of valid invoice."""
        result = self.validator.validate_document(self.valid_invoice, "invoice")
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_valid', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        
        # Should be valid
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_valid_bill(self):
        """Test validation of valid bill."""
        result = self.validator.validate_document(self.valid_bill, "bill")
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_invoice = self.valid_invoice.copy()
        del invalid_invoice['invoice_number']  # Remove required field
        
        result = self.validator.validate_document(invalid_invoice, "invoice")
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
        
        # Check that the error mentions the missing field
        error_text = ' '.join(result['errors'])
        self.assertIn('invoice_number', error_text)
    
    def test_validate_invalid_dates(self):
        """Test validation with invalid dates."""
        invalid_invoice = self.valid_invoice.copy()
        invalid_invoice['date'] = "invalid-date"
        
        result = self.validator.validate_document(invalid_invoice, "invoice")
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_negative_amounts(self):
        """Test validation with negative amounts."""
        invalid_invoice = self.valid_invoice.copy()
        invalid_invoice['total_amount'] = -100.0
        
        result = self.validator.validate_document(invalid_invoice, "invoice")
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_invoice_calculations(self):
        """Test validation of invoice calculations."""
        # Create invoice with incorrect total
        invalid_invoice = self.valid_invoice.copy()
        invalid_invoice['total_amount'] = 9999.0  # Wrong total
        
        result = self.validator.validate_document(invalid_invoice, "invoice")
        
        # Might be valid but should have warnings about calculation mismatch
        if result['is_valid']:
            self.assertGreater(len(result['warnings']), 0)
    
    def test_suggest_corrections(self):
        """Test correction suggestions."""
        invalid_data = {
            "date": "03/15/2024",  # Wrong format
            "amount": -50.0        # Negative amount
        }
        
        validation_result = {
            'errors': [
                "Field 'date': Invalid date format",
                "Field 'amount': Amount cannot be negative"
            ],
            'field_validations': {
                'date': {'is_valid': False, 'value': "03/15/2024", 'type': 'date'},
                'amount': {'is_valid': False, 'value': -50.0, 'type': 'amount'}
            }
        }
        
        suggestions = self.validator.suggest_corrections(invalid_data, validation_result)
        
        self.assertIsInstance(suggestions, dict)
        self.assertIn('field_corrections', suggestions)
        self.assertIn('general_suggestions', suggestions)
        
        # Should have suggestions for both fields
        self.assertIn('date', suggestions['field_corrections'])
        self.assertIn('amount', suggestions['field_corrections'])

if __name__ == '__main__':
    unittest.main()

