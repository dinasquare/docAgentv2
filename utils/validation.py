"""
Data validation module for extracted document data.
"""

import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
import json
from decimal import Decimal, InvalidOperation
from .logger import get_logger, timer

logger = get_logger()

class DataValidator:
    """Validate extracted document data and suggest corrections."""
    
    def __init__(self):
        """Initialize the data validator."""
        self.validation_rules = {
            'date': self._validate_date,
            'amount': self._validate_amount,
            'number': self._validate_number,
            'email': self._validate_email,
            'phone': self._validate_phone,
            'currency': self._validate_currency
        }
    
    @timer(logger)
    def validate_document(self, data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """
        Validate extracted document data.
        
        Args:
            data: Extracted document data
            doc_type: Document type (invoice, bill, prescription)
            
        Returns:
            Validation result with errors and suggestions
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'field_validations': {}
        }
        
        try:
            # Validate based on document type
            if doc_type == 'invoice':
                self._validate_invoice(data, validation_result)
            elif doc_type == 'bill':
                self._validate_bill(data, validation_result)
            elif doc_type == 'prescription':
                self._validate_prescription(data, validation_result)
            
            # General validations
            self._validate_common_fields(data, validation_result)
            
            # Set overall validity
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            logger.log_error("document_validation", e)
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['is_valid'] = False
        
        return validation_result
    
    def _validate_invoice(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate invoice-specific fields."""
        # Required fields
        required_fields = ['invoice_number', 'date', 'vendor', 'total_amount']
        self._check_required_fields(data, required_fields, result)
        
        # Date validations
        if 'date' in data:
            self._validate_field_type(data, 'date', 'date', result)
        
        if 'due_date' in data:
            self._validate_field_type(data, 'due_date', 'date', result)
            
            # Due date should be after invoice date
            if 'date' in data and data['date'] and data['due_date']:
                try:
                    invoice_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                    due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                    
                    if due_date < invoice_date:
                        result['errors'].append("Due date cannot be before invoice date")
                except ValueError:
                    pass  # Date format errors will be caught elsewhere
        
        # Amount validations
        amount_fields = ['total_amount', 'subtotal', 'tax_amount']
        for field in amount_fields:
            if field in data:
                self._validate_field_type(data, field, 'amount', result)
        
        # Items validation
        if 'items' in data and isinstance(data['items'], list):
            for i, item in enumerate(data['items']):
                self._validate_invoice_item(item, i, result)
        
        # Total calculations
        self._validate_invoice_totals(data, result)
    
    def _validate_bill(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate bill-specific fields."""
        # Required fields
        required_fields = ['bill_number', 'statement_date', 'service_provider', 'total_amount_due']
        self._check_required_fields(data, required_fields, result)
        
        # Date validations
        date_fields = ['statement_date', 'due_date']
        for field in date_fields:
            if field in data:
                self._validate_field_type(data, field, 'date', result)
        
        # Amount validations
        amount_fields = ['total_amount_due', 'previous_balance', 'current_charges', 'payments', 'minimum_payment']
        for field in amount_fields:
            if field in data:
                self._validate_field_type(data, field, 'amount', result)
        
        # Balance calculations
        self._validate_bill_calculations(data, result)
    
    def _validate_prescription(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate prescription-specific fields."""
        # Required fields
        required_fields = ['prescription_number', 'date_prescribed', 'doctor', 'patient', 'medications']
        self._check_required_fields(data, required_fields, result)
        
        # Date validations
        date_fields = ['date_prescribed', 'date_filled']
        for field in date_fields:
            if field in data:
                self._validate_field_type(data, field, 'date', result)
        
        # Medications validation
        if 'medications' in data and isinstance(data['medications'], list):
            if not data['medications']:
                result['errors'].append("At least one medication is required")
            else:
                for i, medication in enumerate(data['medications']):
                    self._validate_medication(medication, i, result)
        
        # Cost validations
        cost_fields = ['total_cost', 'insurance_covered', 'patient_pay']
        for field in cost_fields:
            if field in data:
                self._validate_field_type(data, field, 'amount', result)
    
    def _validate_common_fields(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate common fields across document types."""
        # Currency validation
        if 'currency' in data:
            self._validate_field_type(data, 'currency', 'currency', result)
    
    def _check_required_fields(self, data: Dict[str, Any], required_fields: List[str], result: Dict[str, Any]):
        """Check for required fields."""
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                result['errors'].append(f"Required field '{field}' is missing or empty")
    
    def _validate_field_type(self, data: Dict[str, Any], field: str, field_type: str, result: Dict[str, Any]):
        """Validate a specific field type."""
        if field not in data or data[field] is None:
            return
        
        value = data[field]
        
        if field_type in self.validation_rules:
            is_valid, error_msg = self.validation_rules[field_type](value)
            
            result['field_validations'][field] = {
                'is_valid': is_valid,
                'value': value,
                'type': field_type
            }
            
            if not is_valid:
                result['errors'].append(f"Field '{field}': {error_msg}")
        else:
            result['warnings'].append(f"No validation rule for field type '{field_type}'")
    
    def _validate_date(self, value: Any) -> tuple[bool, str]:
        """Validate date field."""
        if not isinstance(value, str):
            return False, "Date must be a string"
        
        # Check for empty or null
        if not value.strip():
            return False, "Date cannot be empty"
        
        # Try to parse common date formats
        date_formats = [
            '%Y-%m-%d',      # 2024-03-15
            '%m/%d/%Y',      # 03/15/2024
            '%d/%m/%Y',      # 15/03/2024
            '%m-%d-%Y',      # 03-15-2024
            '%d-%m-%Y',      # 15-03-2024
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value, fmt).date()
                
                # Check if date is reasonable (not too far in past/future)
                current_year = datetime.now().year
                if parsed_date.year < 1900 or parsed_date.year > current_year + 10:
                    return False, f"Date year {parsed_date.year} seems unreasonable"
                
                return True, ""
            except ValueError:
                continue
        
        return False, f"Invalid date format: {value}. Expected formats: YYYY-MM-DD, MM/DD/YYYY, etc."
    
    def _validate_amount(self, value: Any) -> tuple[bool, str]:
        """Validate monetary amount."""
        if value is None:
            return False, "Amount cannot be null"
        
        if isinstance(value, (int, float)):
            if value < 0:
                return False, "Amount cannot be negative"
            return True, ""
        
        if isinstance(value, str):
            # Remove currency symbols and commas
            clean_value = re.sub(r'[\$,\s]', '', value)
            
            try:
                amount = float(clean_value)
                if amount < 0:
                    return False, "Amount cannot be negative"
                return True, ""
            except ValueError:
                return False, f"Invalid amount format: {value}"
        
        return False, f"Amount must be a number, got {type(value).__name__}"
    
    def _validate_number(self, value: Any) -> tuple[bool, str]:
        """Validate number/ID field."""
        if not isinstance(value, str):
            return False, "Number must be a string"
        
        if not value.strip():
            return False, "Number cannot be empty"
        
        # Check for reasonable length
        if len(value) > 50:
            return False, "Number seems too long"
        
        return True, ""
    
    def _validate_email(self, value: Any) -> tuple[bool, str]:
        """Validate email address."""
        if not isinstance(value, str):
            return False, "Email must be a string"
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, value):
            return True, ""
        
        return False, f"Invalid email format: {value}"
    
    def _validate_phone(self, value: Any) -> tuple[bool, str]:
        """Validate phone number."""
        if not isinstance(value, str):
            return False, "Phone must be a string"
        
        # Remove formatting
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', value)
        
        if re.match(r'^\+?1?\d{10,15}$', clean_phone):
            return True, ""
        
        return False, f"Invalid phone format: {value}"
    
    def _validate_currency(self, value: Any) -> tuple[bool, str]:
        """Validate currency code."""
        if not isinstance(value, str):
            return False, "Currency must be a string"
        
        # Common currency codes
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY']
        
        if value.upper() in valid_currencies:
            return True, ""
        
        return False, f"Unknown currency code: {value}"
    
    def _validate_invoice_item(self, item: Dict[str, Any], index: int, result: Dict[str, Any]):
        """Validate individual invoice item."""
        required_item_fields = ['description', 'quantity', 'unit_price', 'total']
        
        for field in required_item_fields:
            if field not in item or item[field] is None:
                result['errors'].append(f"Item {index}: missing required field '{field}'")
                continue
            
            if field in ['quantity', 'unit_price', 'total']:
                is_valid, error_msg = self._validate_amount(item[field])
                if not is_valid:
                    result['errors'].append(f"Item {index}, field '{field}': {error_msg}")
        
        # Validate calculation: quantity * unit_price should equal total
        if all(field in item and item[field] is not None for field in ['quantity', 'unit_price', 'total']):
            try:
                expected_total = float(item['quantity']) * float(item['unit_price'])
                actual_total = float(item['total'])
                
                # Allow for small rounding differences
                if abs(expected_total - actual_total) > 0.01:
                    result['warnings'].append(
                        f"Item {index}: calculated total ({expected_total:.2f}) doesn't match stated total ({actual_total:.2f})"
                    )
            except (ValueError, TypeError):
                pass  # Skip calculation if values aren't numeric
    
    def _validate_invoice_totals(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate invoice total calculations."""
        try:
            # Calculate expected subtotal from items
            if 'items' in data and isinstance(data['items'], list):
                calculated_subtotal = 0.0
                for item in data['items']:
                    if 'total' in item and item['total'] is not None:
                        calculated_subtotal += float(item['total'])
                
                # Check against stated subtotal
                if 'subtotal' in data and data['subtotal'] is not None:
                    stated_subtotal = float(data['subtotal'])
                    if abs(calculated_subtotal - stated_subtotal) > 0.01:
                        result['warnings'].append(
                            f"Calculated subtotal ({calculated_subtotal:.2f}) doesn't match stated subtotal ({stated_subtotal:.2f})"
                        )
                
                # Check total calculation
                if all(field in data and data[field] is not None for field in ['subtotal', 'tax_amount', 'total_amount']):
                    expected_total = float(data['subtotal']) + float(data['tax_amount'])
                    actual_total = float(data['total_amount'])
                    
                    if abs(expected_total - actual_total) > 0.01:
                        result['warnings'].append(
                            f"Calculated total ({expected_total:.2f}) doesn't match stated total ({actual_total:.2f})"
                        )
        
        except (ValueError, TypeError) as e:
            result['warnings'].append(f"Could not validate total calculations: {str(e)}")
    
    def _validate_bill_calculations(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate bill balance calculations."""
        try:
            # Check if total_amount_due = previous_balance + current_charges - payments
            required_fields = ['previous_balance', 'current_charges', 'total_amount_due']
            
            if all(field in data and data[field] is not None for field in required_fields):
                previous = float(data['previous_balance'])
                current = float(data['current_charges'])
                payments = float(data.get('payments', 0))
                stated_total = float(data['total_amount_due'])
                
                expected_total = previous + current - payments
                
                if abs(expected_total - stated_total) > 0.01:
                    result['warnings'].append(
                        f"Calculated total due ({expected_total:.2f}) doesn't match stated total ({stated_total:.2f})"
                    )
        
        except (ValueError, TypeError) as e:
            result['warnings'].append(f"Could not validate bill calculations: {str(e)}")
    
    def _validate_medication(self, medication: Dict[str, Any], index: int, result: Dict[str, Any]):
        """Validate individual medication."""
        required_med_fields = ['name', 'strength', 'quantity', 'directions']
        
        for field in required_med_fields:
            if field not in medication or not medication[field]:
                result['errors'].append(f"Medication {index}: missing required field '{field}'")
    
    @timer(logger)
    def suggest_corrections(self, data: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest corrections for validation errors.
        
        Args:
            data: Original extracted data
            validation_result: Validation result with errors
            
        Returns:
            Dictionary with suggested corrections
        """
        suggestions = {
            'field_corrections': {},
            'general_suggestions': []
        }
        
        try:
            for error in validation_result['errors']:
                if 'date' in error.lower() and 'format' in error.lower():
                    suggestions['general_suggestions'].append(
                        "Check date formats - ensure they are in YYYY-MM-DD format"
                    )
                
                if 'amount' in error.lower() and 'negative' in error.lower():
                    suggestions['general_suggestions'].append(
                        "Ensure all monetary amounts are positive values"
                    )
                
                if 'missing' in error.lower() or 'required' in error.lower():
                    suggestions['general_suggestions'].append(
                        "Review the document for missing required information"
                    )
            
            # Specific field suggestions
            for field, validation_info in validation_result.get('field_validations', {}).items():
                if not validation_info['is_valid']:
                    if validation_info['type'] == 'date':
                        suggestions['field_corrections'][field] = self._suggest_date_correction(validation_info['value'])
                    elif validation_info['type'] == 'amount':
                        suggestions['field_corrections'][field] = self._suggest_amount_correction(validation_info['value'])
        
        except Exception as e:
            logger.log_error("suggestion_generation", e)
            suggestions['general_suggestions'].append("Unable to generate specific suggestions due to an error")
        
        return suggestions
    
    def _suggest_date_correction(self, value: str) -> str:
        """Suggest date format correction."""
        # Try to detect the intended format and suggest YYYY-MM-DD
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', value):
            parts = value.split('/')
            if len(parts) == 3:
                return f"Try format: {parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        
        return "Use YYYY-MM-DD format (e.g., 2024-03-15)"
    
    def _suggest_amount_correction(self, value: Any) -> str:
        """Suggest amount format correction."""
        if isinstance(value, str):
            # Try to clean the amount
            cleaned = re.sub(r'[^\d\.\-]', '', value)
            try:
                amount = float(cleaned)
                if amount < 0:
                    return f"Use positive value: {abs(amount)}"
                return f"Use numeric format: {amount}"
            except ValueError:
                pass
        
        return "Use numeric format (e.g., 123.45)"

