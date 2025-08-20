"""
Gemini-based extraction engine for structured data extraction.
"""

import google.generativeai as genai
import json
import os
import time
from typing import Dict, Any, Optional, List
from config.config import config
from .logger import get_logger, timer
from .prompts import PromptTemplates

logger = get_logger()

class GeminiExtractor:
    """Gemini-based extraction engine."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize Gemini extractor.
        
        Args:
            api_key: Gemini API key (uses config if None)
            model_name: Model name (uses config if None)
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model_name or config.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        try:
            self.model = genai.GenerativeModel(self.model_name)
            logger.logger.info(f"Initialized Gemini model: {self.model_name}")
        except Exception as e:
            logger.log_error("gemini_init", e)
            raise
        
        # Generation configuration
        self.generation_config = {
            "temperature": config.GEMINI_TEMPERATURE,
            "max_output_tokens": config.GEMINI_MAX_TOKENS,
            "top_p": 0.8,
            "top_k": 40
        }
    
    @timer(logger)
    def call_gemini(self, prompt: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Make a call to Gemini API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum output tokens (uses config if None)
            
        Returns:
            Dictionary with response data and metadata
        """
        start_time = time.time()
        
        try:
            # Override max tokens if specified
            gen_config = self.generation_config.copy()
            if max_tokens:
                gen_config["max_output_tokens"] = max_tokens
            
            # Make API call
            response = self.model.generate_content(
                prompt,
                generation_config=gen_config
            )
            
            latency = time.time() - start_time
            
            # Extract response text
            response_text = response.text if response.text else ""
            
            # Estimate token counts (approximate)
            input_tokens = len(prompt.split()) * 1.3  # Rough estimation
            output_tokens = len(response_text.split()) * 1.3
            
            # Log API call
            logger.log_api_call(
                model=self.model_name,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                latency=latency,
                operation="extraction"
            )
            
            return {
                'text': response_text,
                'latency': latency,
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'model': self.model_name
            }
            
        except Exception as e:
            latency = time.time() - start_time
            logger.log_error("gemini_api_call", e, latency=latency)
            
            return {
                'text': '',
                'error': str(e),
                'latency': latency,
                'input_tokens': 0,
                'output_tokens': 0,
                'model': self.model_name
            }
    
    @timer(logger)
    def extract_structured_data(self, text: str, doc_type: str, 
                              schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from text.
        
        Args:
            text: Input text (OCR output)
            doc_type: Document type (invoice, bill, prescription)
            schema: JSON schema for extraction
            
        Returns:
            Dictionary with extracted data and metadata
        """
        try:
            # Generate extraction prompt
            prompt = PromptTemplates.get_extraction_prompt(text, doc_type, schema)
            
            # Call Gemini
            response = self.call_gemini(prompt)
            
            if 'error' in response:
                return {
                    'data': None,
                    'success': False,
                    'error': response['error'],
                    'metadata': response
                }
            
            # Parse JSON response
            try:
                extracted_data = json.loads(response['text'])
                
                # Validate that it contains document_type
                if 'document_type' not in extracted_data:
                    extracted_data['document_type'] = doc_type
                
                return {
                    'data': extracted_data,
                    'success': True,
                    'metadata': response
                }
                
            except json.JSONDecodeError as e:
                logger.log_error("json_parsing", e, response_text=response['text'][:500])
                
                # Try to extract JSON from response if it contains extra text
                cleaned_json = self._extract_json_from_text(response['text'])
                if cleaned_json:
                    try:
                        extracted_data = json.loads(cleaned_json)
                        if 'document_type' not in extracted_data:
                            extracted_data['document_type'] = doc_type
                        
                        return {
                            'data': extracted_data,
                            'success': True,
                            'metadata': response,
                            'warning': 'JSON extracted from mixed response'
                        }
                    except:
                        pass
                
                return {
                    'data': None,
                    'success': False,
                    'error': f"Invalid JSON response: {str(e)}",
                    'raw_response': response['text'],
                    'metadata': response
                }
                
        except Exception as e:
            logger.log_error("extraction", e)
            return {
                'data': None,
                'success': False,
                'error': str(e),
                'metadata': {}
            }
    
    @timer(logger)
    def self_consistency_extraction(self, text: str, doc_type: str, 
                                  schema: Dict[str, Any], 
                                  num_runs: int = None) -> Dict[str, Any]:
        """
        Run multiple extractions and use majority voting for consistency.
        
        Args:
            text: Input text
            doc_type: Document type
            schema: JSON schema
            num_runs: Number of runs (uses config if None)
            
        Returns:
            Dictionary with consensus data and confidence metrics
        """
        num_runs = num_runs or config.SELF_CONSISTENCY_RUNS
        
        logger.logger.info(f"Running self-consistency extraction with {num_runs} attempts")
        
        results = []
        
        for i in range(num_runs):
            # Use slightly varied prompts for diversity
            prompt = PromptTemplates.get_self_consistency_prompt(text, doc_type, schema, i)
            
            response = self.call_gemini(prompt)
            
            if 'error' not in response:
                try:
                    data = json.loads(response['text'])
                    results.append({
                        'data': data,
                        'attempt': i + 1,
                        'success': True
                    })
                except json.JSONDecodeError:
                    # Try to extract JSON
                    cleaned_json = self._extract_json_from_text(response['text'])
                    if cleaned_json:
                        try:
                            data = json.loads(cleaned_json)
                            results.append({
                                'data': data,
                                'attempt': i + 1,
                                'success': True,
                                'warning': 'Cleaned JSON'
                            })
                        except:
                            results.append({
                                'error': 'JSON parsing failed',
                                'attempt': i + 1,
                                'success': False
                            })
                    else:
                        results.append({
                            'error': 'JSON parsing failed',
                            'attempt': i + 1,
                            'success': False
                        })
            else:
                results.append({
                    'error': response['error'],
                    'attempt': i + 1,
                    'success': False
                })
        
        # Analyze results for consensus
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            return {
                'data': None,
                'success': False,
                'error': 'All extraction attempts failed',
                'results': results
            }
        
        # For now, use the first successful result
        # TODO: Implement proper majority voting for field-level consensus
        consensus_data = successful_results[0]['data']
        
        # Calculate confidence based on consistency
        consistency_rate = len(successful_results) / num_runs
        
        return {
            'data': consensus_data,
            'success': True,
            'consistency_rate': consistency_rate,
            'successful_attempts': len(successful_results),
            'total_attempts': num_runs,
            'results': results
        }
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from text that might contain extra content.
        
        Args:
            text: Text that might contain JSON
            
        Returns:
            Cleaned JSON string or None
        """
        # Try to find JSON between braces
        import re
        
        # Look for JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Look for JSON array
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        if array_match:
            return array_match.group(0)
        
        return None
    
    @timer(logger)
    def assess_confidence(self, text: str, extracted_data: Dict[str, Any], 
                         doc_type: str) -> Dict[str, float]:
        """
        Assess confidence scores for extracted fields.
        
        Args:
            text: Original OCR text
            extracted_data: Extracted data
            doc_type: Document type
            
        Returns:
            Dictionary mapping field paths to confidence scores
        """
        try:
            prompt = PromptTemplates.get_confidence_prompt(text, extracted_data, doc_type)
            
            response = self.call_gemini(prompt, max_tokens=512)
            
            if 'error' in response:
                logger.log_error("confidence_assessment", Exception(response['error']))
                return self._default_confidence_scores(extracted_data)
            
            try:
                response_text = response['text'].strip()
                
                # Handle empty response
                if not response_text:
                    logger.logger.warning("Empty confidence response from Gemini")
                    return self._default_confidence_scores(extracted_data)
                
                confidence_scores = json.loads(response_text)
                
                # Validate confidence scores
                validated_scores = {}
                for field, score in confidence_scores.items():
                    if isinstance(score, (int, float)) and 0 <= score <= 1:
                        validated_scores[field] = float(score)
                    else:
                        validated_scores[field] = 0.5  # Default for invalid scores
                
                return validated_scores
                
            except json.JSONDecodeError as e:
                logger.log_error("confidence_json_parsing", 
                                Exception(f"Failed to parse confidence JSON: {response['text'][:100]}"))
                return self._default_confidence_scores(extracted_data)
                
        except Exception as e:
            logger.log_error("confidence_assessment", e)
            return self._default_confidence_scores(extracted_data)
    
    def _default_confidence_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Generate default confidence scores for all fields."""
        scores = {}
        
        def add_scores(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    field_path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        add_scores(value, field_path)
                    else:
                        scores[field_path] = 0.5  # Default moderate confidence
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        add_scores(item, f"{prefix}.{i}")
        
        add_scores(data)
        return scores
    
    @timer(logger)
    def fix_validation_errors(self, data: Dict[str, Any], 
                            validation_errors: List[str]) -> Dict[str, Any]:
        """
        Fix validation errors using Gemini.
        
        Args:
            data: Original extracted data
            validation_errors: List of validation error messages
            
        Returns:
            Fixed data
        """
        try:
            prompt = PromptTemplates.get_validation_prompt(data, validation_errors)
            
            response = self.call_gemini(prompt)
            
            if 'error' in response:
                logger.log_error("validation_fix", Exception(response['error']))
                return data  # Return original data if fix fails
            
            try:
                fixed_data = json.loads(response['text'])
                return fixed_data
            except json.JSONDecodeError:
                logger.log_error("validation_fix_json", 
                                Exception("Failed to parse fixed JSON"))
                return data  # Return original data if parsing fails
                
        except Exception as e:
            logger.log_error("validation_fix", e)
            return data  # Return original data if fix fails

