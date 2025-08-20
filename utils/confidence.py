"""
Confidence scoring module for extracted data.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from .logger import get_logger, timer

logger = get_logger()

class ConfidenceScorer:
    """Calculate confidence scores for extracted data fields."""
    
    def __init__(self, low_confidence_threshold: float = 0.7):
        """
        Initialize confidence scorer.
        
        Args:
            low_confidence_threshold: Threshold below which confidence is considered low
        """
        self.low_confidence_threshold = low_confidence_threshold
    
    @timer(logger)
    def calculate_field_confidence(self, field_path: str, value: Any, 
                                 original_text: str, 
                                 gemini_confidence: Optional[float] = None) -> float:
        """
        Calculate confidence score for a specific field.
        
        Args:
            field_path: Dot-notation path to the field (e.g., "vendor.name")
            value: Extracted value
            original_text: Original OCR text
            gemini_confidence: Optional Gemini-assessed confidence
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if value is None:
            return 0.0
        
        # Start with Gemini confidence if available
        if gemini_confidence is not None:
            base_confidence = gemini_confidence
        else:
            base_confidence = 0.5  # Default
        
        # Apply heuristic adjustments
        heuristic_score = self._calculate_heuristic_confidence(
            field_path, value, original_text
        )
        
        # Combine scores (weighted average)
        if gemini_confidence is not None:
            # Trust Gemini more, but adjust with heuristics
            final_confidence = 0.7 * base_confidence + 0.3 * heuristic_score
        else:
            # Rely more on heuristics when no Gemini confidence
            final_confidence = heuristic_score
        
        return max(0.0, min(1.0, final_confidence))
    
    def _calculate_heuristic_confidence(self, field_path: str, value: Any, 
                                      original_text: str) -> float:
        """Calculate confidence using heuristic rules."""
        if value is None or value == "":
            return 0.0
        
        confidence_adjustments = []
        
        # Field-specific confidence rules
        if 'date' in field_path.lower():
            confidence_adjustments.append(self._date_confidence(value))
        
        if 'amount' in field_path.lower() or 'total' in field_path.lower() or 'cost' in field_path.lower():
            confidence_adjustments.append(self._amount_confidence(value))
        
        if 'number' in field_path.lower() or field_path.endswith('_number'):
            confidence_adjustments.append(self._number_confidence(value, original_text))
        
        if 'name' in field_path.lower():
            confidence_adjustments.append(self._name_confidence(value, original_text))
        
        if 'email' in field_path.lower():
            confidence_adjustments.append(self._email_confidence(value))
        
        if 'phone' in field_path.lower():
            confidence_adjustments.append(self._phone_confidence(value))
        
        # Text presence confidence
        text_presence = self._text_presence_confidence(str(value), original_text)
        confidence_adjustments.append(text_presence)
        
        # Format consistency confidence
        format_confidence = self._format_confidence(field_path, value)
        confidence_adjustments.append(format_confidence)
        
        # Calculate average confidence
        if confidence_adjustments:
            return np.mean(confidence_adjustments)
        else:
            return 0.5  # Default neutral confidence
    
    def _date_confidence(self, value: str) -> float:
        """Assess confidence for date fields."""
        if not isinstance(value, str):
            return 0.3
        
        # Check for valid date format
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, value):
                # Try to parse the date
                try:
                    if '-' in value and len(value) == 10:
                        datetime.strptime(value, '%Y-%m-%d')
                    elif '/' in value:
                        datetime.strptime(value, '%m/%d/%Y')
                    elif '-' in value and len(value) != 10:
                        datetime.strptime(value, '%m-%d-%Y')
                    return 0.9  # High confidence for valid dates
                except ValueError:
                    return 0.4  # Format matches but invalid date
        
        # Check for partial dates or text dates
        if re.search(r'\d{4}', value) and re.search(r'\d{1,2}', value):
            return 0.6  # Moderate confidence for partial matches
        
        return 0.2  # Low confidence for non-date-like values
    
    def _amount_confidence(self, value: Any) -> float:
        """Assess confidence for monetary amounts."""
        if isinstance(value, (int, float)):
            if value >= 0:
                return 0.85  # High confidence for positive numbers
            else:
                return 0.6   # Lower confidence for negative numbers
        
        if isinstance(value, str):
            # Check for currency patterns
            currency_patterns = [
                r'^\$?[\d,]+\.?\d{0,2}$',  # $1,234.56
                r'^[\d,]+\.?\d{0,2}\s*\$?$',  # 1234.56$
            ]
            
            for pattern in currency_patterns:
                if re.match(pattern, value.strip()):
                    return 0.8
            
            # Check if it contains numbers
            if re.search(r'\d', value):
                return 0.5
        
        return 0.2
    
    def _number_confidence(self, value: str, original_text: str) -> float:
        """Assess confidence for number fields."""
        if not isinstance(value, str):
            return 0.3
        
        # Check if it looks like a proper number/ID
        if re.match(r'^[A-Z0-9\-_]+$', value):
            # Check if it appears in original text
            if value in original_text:
                return 0.9
            else:
                return 0.6
        
        return 0.4
    
    def _name_confidence(self, value: str, original_text: str) -> float:
        """Assess confidence for name fields."""
        if not isinstance(value, str) or len(value) < 2:
            return 0.2
        
        # Check if name appears in original text
        if value.lower() in original_text.lower():
            return 0.8
        
        # Check if it looks like a proper name
        if re.match(r'^[A-Za-z\s\.,]+$', value):
            return 0.7
        
        return 0.4
    
    def _email_confidence(self, value: str) -> float:
        """Assess confidence for email fields."""
        if not isinstance(value, str):
            return 0.2
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, value):
            return 0.95
        
        # Partial email patterns
        if '@' in value and '.' in value:
            return 0.6
        
        return 0.2
    
    def _phone_confidence(self, value: str) -> float:
        """Assess confidence for phone fields."""
        if not isinstance(value, str):
            return 0.2
        
        # Remove common formatting
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', value)
        
        # Check for valid phone number patterns
        if re.match(r'^\+?1?\d{10}$', clean_phone):
            return 0.9
        
        if re.match(r'^\d{7,15}$', clean_phone):
            return 0.7
        
        return 0.3
    
    def _text_presence_confidence(self, value: str, original_text: str) -> float:
        """Check if the extracted value appears in the original text."""
        if not value or not original_text:
            return 0.0
        
        # Exact match
        if value in original_text:
            return 0.9
        
        # Case-insensitive match
        if value.lower() in original_text.lower():
            return 0.85
        
        # Partial match (for longer strings)
        if len(value) > 5:
            words = value.split()
            matches = sum(1 for word in words if word.lower() in original_text.lower())
            if matches > 0:
                return 0.3 + (matches / len(words)) * 0.4
        
        return 0.1
    
    def _format_confidence(self, field_path: str, value: Any) -> float:
        """Assess confidence based on expected format for field type."""
        if value is None:
            return 0.0
        
        # Basic type checking
        if 'amount' in field_path.lower() or 'total' in field_path.lower():
            if isinstance(value, (int, float)):
                return 0.8
            return 0.3
        
        if 'quantity' in field_path.lower():
            if isinstance(value, (int, float)) and value >= 0:
                return 0.8
            return 0.4
        
        if 'date' in field_path.lower():
            if isinstance(value, str) and len(value) >= 8:
                return 0.7
            return 0.3
        
        return 0.5  # Neutral for unknown field types
    
    @timer(logger)
    def calculate_overall_confidence(self, field_confidences: Dict[str, float],
                                   required_fields: Optional[List[str]] = None) -> float:
        """
        Calculate overall confidence score for the document.
        
        Args:
            field_confidences: Mapping of field paths to confidence scores
            required_fields: List of required field paths
            
        Returns:
            Overall confidence score
        """
        if not field_confidences:
            return 0.0
        
        if required_fields:
            # Weight required fields more heavily
            required_scores = []
            optional_scores = []
            
            for field, confidence in field_confidences.items():
                if field in required_fields:
                    required_scores.append(confidence)
                else:
                    optional_scores.append(confidence)
            
            # Calculate weighted average
            if required_scores:
                required_avg = np.mean(required_scores)
                if optional_scores:
                    optional_avg = np.mean(optional_scores)
                    # 70% weight to required fields, 30% to optional
                    overall = 0.7 * required_avg + 0.3 * optional_avg
                else:
                    overall = required_avg
            else:
                overall = np.mean(list(field_confidences.values()))
        else:
            # Simple average of all fields
            overall = np.mean(list(field_confidences.values()))
        
        return max(0.0, min(1.0, overall))
    
    @timer(logger)
    def identify_low_confidence_fields(self, field_confidences: Dict[str, float]) -> List[Tuple[str, float]]:
        """
        Identify fields with low confidence scores.
        
        Args:
            field_confidences: Mapping of field paths to confidence scores
            
        Returns:
            List of (field_path, confidence_score) tuples for low confidence fields
        """
        low_confidence_fields = []
        
        for field, confidence in field_confidences.items():
            if confidence < self.low_confidence_threshold:
                low_confidence_fields.append((field, confidence))
        
        # Sort by confidence (lowest first)
        low_confidence_fields.sort(key=lambda x: x[1])
        
        return low_confidence_fields
    
    def get_confidence_summary(self, field_confidences: Dict[str, float],
                             overall_confidence: float) -> Dict[str, Any]:
        """
        Generate a summary of confidence scores.
        
        Args:
            field_confidences: Mapping of field paths to confidence scores
            overall_confidence: Overall confidence score
            
        Returns:
            Confidence summary dictionary
        """
        low_confidence_fields = self.identify_low_confidence_fields(field_confidences)
        
        confidence_distribution = {
            'high': len([c for c in field_confidences.values() if c >= 0.8]),
            'medium': len([c for c in field_confidences.values() if 0.5 <= c < 0.8]),
            'low': len([c for c in field_confidences.values() if c < 0.5])
        }
        
        return {
            'overall_confidence': overall_confidence,
            'field_count': len(field_confidences),
            'low_confidence_count': len(low_confidence_fields),
            'low_confidence_fields': low_confidence_fields,
            'confidence_distribution': confidence_distribution,
            'average_confidence': np.mean(list(field_confidences.values())) if field_confidences else 0.0,
            'min_confidence': min(field_confidences.values()) if field_confidences else 0.0,
            'max_confidence': max(field_confidences.values()) if field_confidences else 0.0
        }

