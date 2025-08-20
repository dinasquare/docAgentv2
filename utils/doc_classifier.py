"""
Document type classification using heuristics and Gemini fallback.
"""

import re
from typing import Dict, Any, Optional, Tuple
from .logger import get_logger, timer

logger = get_logger()

class DocumentClassifier:
    """Classify documents by type using heuristics and AI fallback."""
    
    def __init__(self):
        """Initialize the document classifier."""
        self.invoice_keywords = [
            'invoice', 'bill to', 'ship to', 'subtotal', 'tax', 'total due',
            'invoice number', 'invoice date', 'due date', 'remit to',
            'item', 'description', 'quantity', 'rate', 'amount'
        ]
        
        self.bill_keywords = [
            'statement', 'account number', 'billing period', 'previous balance',
            'payment due', 'current charges', 'service period', 'usage',
            'meter reading', 'kilowatt', 'gallons', 'minutes'
        ]
        
        self.prescription_keywords = [
            'prescription', 'rx', 'medication', 'prescriber', 'pharmacy',
            'patient', 'dosage', 'instructions', 'refill', 'ndc',
            'generic', 'brand', 'tablet', 'capsule', 'mg', 'ml'
        ]
    
    @timer(logger)
    def classify_by_heuristics(self, text: str) -> Tuple[Optional[str], float]:
        """
        Classify document using keyword-based heuristics.
        
        Args:
            text: Document text to classify
            
        Returns:
            Tuple of (document_type, confidence_score)
        """
        text_lower = text.lower()
        
        # Count keyword matches for each document type
        invoice_score = self._count_keywords(text_lower, self.invoice_keywords)
        bill_score = self._count_keywords(text_lower, self.bill_keywords)
        prescription_score = self._count_keywords(text_lower, self.prescription_keywords)
        
        # Specific pattern matching for higher confidence
        pattern_scores = self._pattern_matching(text_lower)
        
        # Combine scores
        invoice_total = invoice_score + pattern_scores.get('invoice', 0)
        bill_total = bill_score + pattern_scores.get('bill', 0)
        prescription_total = prescription_score + pattern_scores.get('prescription', 0)
        
        scores = {
            'invoice': invoice_total,
            'bill': bill_total,
            'prescription': prescription_total
        }
        
        # Find the highest scoring type
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        # Calculate confidence based on score difference
        sorted_scores = sorted(scores.values(), reverse=True)
        
        if max_score == 0:
            return None, 0.0
        
        if len(sorted_scores) > 1 and sorted_scores[1] > 0:
            # Confidence based on margin between top two scores
            confidence = min(0.95, max_score / (max_score + sorted_scores[1]))
        else:
            # Only one type detected
            confidence = min(0.9, max_score / 10.0)  # Normalize to reasonable confidence
        
        # Minimum threshold for heuristic classification
        if confidence < 0.6:
            return None, confidence
        
        logger.logger.info(f"Heuristic classification: {max_type} (confidence: {confidence:.2f})")
        return max_type, confidence
    
    def _count_keywords(self, text: str, keywords: list) -> int:
        """Count keyword matches in text."""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    def _pattern_matching(self, text: str) -> Dict[str, int]:
        """Match specific patterns to boost classification confidence."""
        patterns = {
            'invoice': [
                r'invoice\s*#?\s*\d+',
                r'invoice\s*number',
                r'bill\s*to:',
                r'subtotal.*\$',
                r'tax.*\$.*total.*\$'
            ],
            'bill': [
                r'account\s*#?\s*\d+',
                r'statement\s*date',
                r'billing\s*period',
                r'previous\s*balance.*\$',
                r'payment\s*due.*\$'
            ],
            'prescription': [
                r'rx\s*#?\s*\d+',
                r'prescription\s*#?\s*\d+',
                r'\d+\s*mg\s*tablet',
                r'take\s*\d+.*daily',
                r'refill.*\d+'
            ]
        }
        
        scores = {}
        for doc_type, pattern_list in patterns.items():
            score = 0
            for pattern in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 2  # Higher weight for pattern matches
            scores[doc_type] = score
        
        return scores
    
    @timer(logger)
    def classify_with_gemini(self, text: str, gemini_extractor) -> Tuple[str, float]:
        """
        Classify document using Gemini as fallback.
        
        Args:
            text: Document text to classify
            gemini_extractor: GeminiExtractor instance
            
        Returns:
            Tuple of (document_type, confidence_score)
        """
        try:
            from .prompts import PromptTemplates
            
            prompt = PromptTemplates.get_classification_prompt(text)
            
            response = gemini_extractor.call_gemini(prompt, max_tokens=10)
            
            classification = response.get('text', '').strip().lower()
            
            # Validate response
            valid_types = ['invoice', 'bill', 'prescription']
            if classification in valid_types:
                # Use a moderate confidence for AI classification
                confidence = 0.75
                logger.logger.info(f"Gemini classification: {classification} (confidence: {confidence:.2f})")
                return classification, confidence
            else:
                logger.logger.warning(f"Invalid Gemini classification: {classification}")
                return 'invoice', 0.5  # Default fallback
                
        except Exception as e:
            logger.log_error("gemini_classification", e)
            # Fallback to most common type
            return 'invoice', 0.3
    
    @timer(logger)
    def classify(self, text: str, gemini_extractor=None) -> Tuple[str, float]:
        """
        Classify document type using heuristics first, then Gemini fallback.
        
        Args:
            text: Document text to classify
            gemini_extractor: Optional GeminiExtractor for fallback
            
        Returns:
            Tuple of (document_type, confidence_score)
        """
        # Try heuristics first
        doc_type, confidence = self.classify_by_heuristics(text)
        
        if doc_type and confidence > 0.7:
            return doc_type, confidence
        
        # Fall back to Gemini if available and heuristics are uncertain
        if gemini_extractor and confidence < 0.7:
            try:
                gemini_type, gemini_confidence = self.classify_with_gemini(text, gemini_extractor)
                
                # If Gemini is more confident, use its result
                if gemini_confidence > confidence:
                    return gemini_type, gemini_confidence
            except Exception as e:
                logger.log_error("gemini_fallback", e)
        
        # Return heuristic result or default
        if doc_type:
            return doc_type, confidence
        else:
            # Default to invoice if no classification possible
            return 'invoice', 0.3

