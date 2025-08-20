"""
Gemini-optimized prompts for document extraction.
"""

from typing import Dict, Any, List
import json

class PromptTemplates:
    """Collection of optimized prompts for Gemini."""
    
    @staticmethod
    def get_classification_prompt(text: str) -> str:
        """
        Generate prompt for document type classification.
        
        Args:
            text: OCR extracted text
            
        Returns:
            Classification prompt
        """
        return f"""Analyze the following document text and classify it as one of these types: invoice, bill, or prescription.

Look for these key indicators:
- INVOICE: Contains invoice number, vendor details, itemized charges, tax calculations
- BILL: Contains account numbers, billing periods, service charges, payment due dates
- PRESCRIPTION: Contains medication names, dosages, prescriber information, pharmacy details

Document text:
{text[:2000]}...

Respond with ONLY one word: invoice, bill, or prescription"""

    @staticmethod
    def get_extraction_prompt(text: str, doc_type: str, schema: Dict[str, Any]) -> str:
        """
        Generate extraction prompt for specific document type.
        
        Args:
            text: OCR extracted text
            doc_type: Document type (invoice, bill, prescription)
            schema: JSON schema for the document type
            
        Returns:
            Extraction prompt
        """
        
        # Get examples based on document type
        examples = PromptTemplates._get_examples(doc_type)
        
        prompt = f"""Extract structured information from this {doc_type} document and return ONLY valid JSON.

REQUIRED JSON SCHEMA:
{json.dumps(schema, indent=2)}

EXAMPLES:
{examples}

IMPORTANT RULES:
1. Return ONLY valid JSON - no explanations or markdown
2. Use null for missing values, not empty strings
3. Ensure dates are in YYYY-MM-DD format
4. Ensure numbers are numeric, not strings
5. Be precise with field mapping
6. If uncertain about a value, use null

DOCUMENT TEXT:
{text}

JSON OUTPUT:"""
        
        return prompt
    
    @staticmethod
    def get_confidence_prompt(text: str, extracted_data: Dict[str, Any], doc_type: str) -> str:
        """
        Generate prompt for confidence assessment.
        
        Args:
            text: Original OCR text
            extracted_data: Previously extracted data
            doc_type: Document type
            
        Returns:
            Confidence assessment prompt
        """
        return f"""Assess the confidence of each extracted field from this {doc_type} document.

ORIGINAL TEXT:
{text[:1500]}...

EXTRACTED DATA:
{json.dumps(extracted_data, indent=2)}

For each field in the extracted data, assess confidence as a decimal between 0.0 and 1.0 based on:
- How clearly the value appears in the source text
- Whether the format is correct for the field type
- If the value makes logical sense in context

Return ONLY a JSON object with field paths as keys and confidence scores as values:

Example format:
{{
    "invoice_number": 0.95,
    "date": 0.87,
    "vendor.name": 0.92,
    "total_amount": 0.88,
    "items.0.description": 0.85
}}

JSON OUTPUT:"""
    
    @staticmethod
    def get_validation_prompt(data: Dict[str, Any], validation_errors: List[str]) -> str:
        """
        Generate prompt for fixing validation errors.
        
        Args:
            data: Original extracted data
            validation_errors: List of validation error messages
            
        Returns:
            Validation fix prompt
        """
        return f"""Fix the following validation errors in the extracted data:

VALIDATION ERRORS:
{chr(10).join(f"- {error}" for error in validation_errors)}

CURRENT DATA:
{json.dumps(data, indent=2)}

Return the corrected JSON with all validation errors fixed. Follow these rules:
1. Fix date formats to YYYY-MM-DD
2. Ensure numeric fields contain only numbers
3. Correct obvious typos or formatting issues
4. Maintain all other correct values unchanged

CORRECTED JSON:"""
    
    @staticmethod
    def _get_examples(doc_type: str) -> str:
        """Get few-shot examples for specific document type."""
        
        if doc_type == "invoice":
            return """EXAMPLE INPUT: "INVOICE #INV-2024-001 Date: 03/15/2024 From: ABC Corp To: XYZ Ltd Item: Consulting Services Qty: 10 hours Rate: $150/hr Total: $1,500.00"

EXAMPLE OUTPUT:
{
    "document_type": "invoice",
    "invoice_number": "INV-2024-001",
    "date": "2024-03-15",
    "vendor": {
        "name": "ABC Corp"
    },
    "customer": {
        "name": "XYZ Ltd"
    },
    "items": [
        {
            "description": "Consulting Services",
            "quantity": 10,
            "unit_price": 150.0,
            "total": 1500.0
        }
    ],
    "total_amount": 1500.0,
    "currency": "USD"
}"""
        
        elif doc_type == "bill":
            return """EXAMPLE INPUT: "Electric Bill Account #12345 Statement Date: 02/01/2024 Due Date: 02/28/2024 Previous Balance: $145.30 Current Charges: $89.45 Total Due: $234.75"

EXAMPLE OUTPUT:
{
    "document_type": "bill",
    "bill_number": "12345",
    "statement_date": "2024-02-01",
    "due_date": "2024-02-28",
    "service_provider": {
        "name": "Electric Company"
    },
    "previous_balance": 145.30,
    "current_charges": 89.45,
    "total_amount_due": 234.75,
    "currency": "USD"
}"""
        
        elif doc_type == "prescription":
            return """EXAMPLE INPUT: "Rx #123456 Date: 01/15/2024 Dr. Smith Medication: Amoxicillin 500mg Take 1 tablet twice daily Qty: 20 tablets Refills: 2"

EXAMPLE OUTPUT:
{
    "document_type": "prescription",
    "prescription_number": "123456",
    "date_prescribed": "2024-01-15",
    "doctor": {
        "name": "Dr. Smith"
    },
    "patient": {
        "name": null
    },
    "medications": [
        {
            "name": "Amoxicillin",
            "strength": "500mg",
            "quantity": "20 tablets",
            "directions": "Take 1 tablet twice daily",
            "refills": "2"
        }
    ]
}"""
        
        return ""
    
    @staticmethod
    def get_self_consistency_prompt(text: str, doc_type: str, schema: Dict[str, Any], attempt: int) -> str:
        """
        Generate slightly varied prompt for self-consistency checking.
        
        Args:
            text: OCR extracted text
            doc_type: Document type
            schema: JSON schema
            attempt: Attempt number (for variation)
            
        Returns:
            Varied extraction prompt
        """
        variations = [
            "Extract the key information from this document:",
            "Parse the following document and extract structured data:",
            "Analyze this document and return the structured information:",
            "Process this document text and extract the relevant fields:"
        ]
        
        intro = variations[attempt % len(variations)]
        
        base_prompt = PromptTemplates.get_extraction_prompt(text, doc_type, schema)
        
        # Replace the first line with variation
        lines = base_prompt.split('\n')
        lines[0] = f"{intro} {doc_type} document and return ONLY valid JSON."
        
        return '\n'.join(lines)

