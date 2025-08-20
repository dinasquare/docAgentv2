"""
Main command-line interface for the document extraction system.
"""

import argparse
import sys
from pathlib import Path
import json
from typing import Optional

from utils import (
    OCRProcessor, DocumentClassifier, GeminiExtractor,
    ConfidenceScorer, DataValidator, get_logger, save_json
)
from config.config import config

logger = get_logger()

def process_document_cli(file_path: str, output_path: Optional[str] = None,
                        use_self_consistency: bool = True,
                        doc_type: Optional[str] = None) -> bool:
    """
    Process a document via command line interface.
    
    Args:
        file_path: Path to the document file
        output_path: Optional output path for results
        use_self_consistency: Whether to use self-consistency extraction
        doc_type: Optional override for document type
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate input file
        input_file = Path(file_path)
        if not input_file.exists():
            print(f"Error: File not found: {file_path}")
            return False
        
        # Check file type
        if input_file.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
            print(f"Error: Unsupported file type: {input_file.suffix}")
            print(f"Supported types: {', '.join(config.SUPPORTED_EXTENSIONS)}")
            return False
        
        print(f"Processing document: {file_path}")
        
        # Initialize processors
        ocr_processor = OCRProcessor(engine=config.OCR_ENGINE)
        classifier = DocumentClassifier()
        extractor = GeminiExtractor()
        confidence_scorer = ConfidenceScorer()
        validator = DataValidator()
        
        # Step 1: OCR Processing
        print("Step 1: Extracting text...")
        ocr_result = ocr_processor.process_file(str(input_file))
        
        if not ocr_result.get('text'):
            print("Error: Could not extract text from document")
            return False
        
        print(f"✓ Text extracted ({ocr_result.get('word_count', 0)} words, "
              f"confidence: {ocr_result.get('confidence', 0):.1%})")
        
        # Step 2: Document Classification
        if not doc_type:
            print("Step 2: Classifying document...")
            doc_type, classification_confidence = classifier.classify(
                ocr_result['text'], extractor
            )
            print(f"✓ Document classified as '{doc_type}' "
                  f"(confidence: {classification_confidence:.1%})")
        else:
            print(f"Step 2: Using provided document type: {doc_type}")
        
        # Step 3: Load Schema
        try:
            schema = config.get_schema(doc_type)
        except FileNotFoundError:
            print(f"Error: Schema not found for document type: {doc_type}")
            return False
        
        # Step 4: Data Extraction
        print("Step 3: Extracting structured data...")
        if use_self_consistency:
            extraction_result = extractor.self_consistency_extraction(
                ocr_result['text'], doc_type, schema
            )
            extracted_data = extraction_result.get('data')
            print(f"✓ Self-consistency: {extraction_result.get('successful_attempts', 0)}/"
                  f"{extraction_result.get('total_attempts', 0)} successful attempts")
        else:
            extraction_result = extractor.extract_structured_data(
                ocr_result['text'], doc_type, schema
            )
            extracted_data = extraction_result.get('data')
        
        if not extracted_data:
            print("Error: Failed to extract structured data")
            return False
        
        print("✓ Structured data extracted")
        
        # Step 5: Confidence Assessment
        print("Step 4: Calculating confidence scores...")
        gemini_confidences = extractor.assess_confidence(
            ocr_result['text'], extracted_data, doc_type
        )
        
        # Calculate detailed confidence scores
        field_confidences = {}
        for field_path, gemini_conf in gemini_confidences.items():
            field_value = _get_nested_value(extracted_data, field_path)
            confidence = confidence_scorer.calculate_field_confidence(
                field_path, field_value, ocr_result['text'], gemini_conf
            )
            field_confidences[field_path] = confidence
        
        overall_confidence = confidence_scorer.calculate_overall_confidence(field_confidences)
        print(f"✓ Overall confidence: {overall_confidence:.1%}")
        
        # Step 6: Data Validation
        print("Step 5: Validating data...")
        validation_result = validator.validate_document(extracted_data, doc_type)
        
        if validation_result.get('is_valid', False):
            print("✓ All validations passed")
        else:
            print(f"⚠ Validation issues found: {len(validation_result.get('errors', []))} errors")
            for error in validation_result.get('errors', []):
                print(f"  - {error}")
        
        # Compile results
        results = {
            'input_file': str(input_file),
            'document_type': doc_type,
            'ocr_result': ocr_result,
            'extracted_data': extracted_data,
            'confidence_scores': field_confidences,
            'overall_confidence': overall_confidence,
            'validation_result': validation_result,
            'processing_metadata': {
                'extraction_method': 'self_consistency' if use_self_consistency else 'single',
                'ocr_engine': config.OCR_ENGINE,
                'model': config.GEMINI_MODEL
            }
        }
        
        # Save results
        if output_path:
            output_file = Path(output_path)
        else:
            output_file = input_file.parent / f"{input_file.stem}_extracted.json"
        
        if save_json(results, output_file):
            print(f"✓ Results saved to: {output_file}")
        else:
            print(f"⚠ Could not save results to: {output_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("EXTRACTION SUMMARY")
        print("="*50)
        print(f"Document Type: {doc_type}")
        print(f"Overall Confidence: {overall_confidence:.1%}")
        print(f"Fields Extracted: {len(field_confidences)}")
        
        low_confidence_fields = [
            field for field, conf in field_confidences.items() 
            if conf < config.LOW_CONFIDENCE_THRESHOLD
        ]
        if low_confidence_fields:
            print(f"Low Confidence Fields: {len(low_confidence_fields)}")
            for field in low_confidence_fields:
                print(f"  - {field}: {field_confidences[field]:.1%}")
        
        print(f"Validation Status: {'✓ PASSED' if validation_result.get('is_valid', False) else '⚠ ISSUES FOUND'}")
        
        return True
        
    except Exception as e:
        logger.log_error("cli_processing", e)
        print(f"Error: {str(e)}")
        return False

def _get_nested_value(data, field_path):
    """Get nested value from data using dot notation."""
    try:
        parts = field_path.split('.')
        value = data
        for part in parts:
            if part.isdigit():
                value = value[int(part)]
            else:
                value = value[part]
        return value
    except (KeyError, IndexError, TypeError):
        return None

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Document AI Extractor - Extract structured data from documents"
    )
    
    parser.add_argument(
        "file_path",
        help="Path to the document file to process"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output path for results (default: input_file_extracted.json)"
    )
    
    parser.add_argument(
        "-t", "--type",
        choices=config.SUPPORTED_DOC_TYPES,
        help="Override document type classification"
    )
    
    parser.add_argument(
        "--no-self-consistency",
        action="store_true",
        help="Disable self-consistency extraction (use single extraction)"
    )
    
    parser.add_argument(
        "--ocr-engine",
        choices=["tesseract", "paddleocr"],
        default=config.OCR_ENGINE,
        help="OCR engine to use"
    )
    
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=config.LOW_CONFIDENCE_THRESHOLD,
        help="Low confidence threshold (0.0-1.0)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    if not config.validate_config():
        print("Configuration validation failed. Please check your environment variables.")
        sys.exit(1)
    
    # Update config from arguments
    if args.ocr_engine:
        config.OCR_ENGINE = args.ocr_engine
    
    if args.confidence_threshold:
        config.LOW_CONFIDENCE_THRESHOLD = args.confidence_threshold
    
    # Process document
    success = process_document_cli(
        file_path=args.file_path,
        output_path=args.output,
        use_self_consistency=not args.no_self_consistency,
        doc_type=args.type
    )
    
    if success:
        print("\n✓ Document processing completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Document processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

