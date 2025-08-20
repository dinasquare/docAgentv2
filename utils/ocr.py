"""
OCR processing module supporting Tesseract and PaddleOCR.
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import List, Dict, Any, Optional, Union, Tuple
import os
import tempfile
from pdf2image import convert_from_bytes, convert_from_path
from pathlib import Path

from .logger import get_logger, timer

logger = get_logger()

class OCRProcessor:
    """OCR processor supporting multiple engines."""
    
    def __init__(self, engine: str = "tesseract"):
        """
        Initialize OCR processor.
        
        Args:
            engine: OCR engine to use ("tesseract" or "paddleocr")
        """
        self.engine = engine.lower()
        self.paddleocr_instance = None
        self.easyocr_instance = None
        
        if self.engine == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                # Initialize with minimal configuration to avoid version conflicts
                self.paddleocr_instance = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en'
                    # Note: show_log parameter removed due to version compatibility
                )
                logger.logger.info("PaddleOCR initialized successfully")
            except ImportError:
                logger.logger.warning("PaddleOCR not available, falling back to Tesseract")
                self.engine = "tesseract"
            except Exception as e:
                logger.log_error("paddleocr_init", e)
                logger.logger.warning("PaddleOCR initialization failed, falling back to Tesseract")
                self.engine = "tesseract"
        
        if self.engine == "tesseract":
            # Test Tesseract availability
            try:
                pytesseract.get_tesseract_version()
                logger.logger.info("Tesseract initialized successfully")
            except Exception as e:
                logger.log_error("tesseract_init", e)
                logger.logger.warning("Tesseract not available, falling back to PaddleOCR")
                self.engine = "paddleocr"
                
                # Try to initialize PaddleOCR as fallback
                try:
                    from paddleocr import PaddleOCR
                    self.paddleocr_instance = PaddleOCR(
                        use_angle_cls=True, 
                        lang='en'
                        # Note: show_log parameter removed due to version compatibility
                    )
                    logger.logger.info("PaddleOCR initialized as fallback")
                except ImportError:
                    logger.logger.error("Neither Tesseract nor PaddleOCR available")
                    raise RuntimeError(
                        "No OCR engine available. Please install either:\n"
                        "1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki\n"
                        "2. PaddleOCR: pip install paddlepaddle==2.5.2 paddleocr==2.7.0.3"
                    )
                except Exception as paddle_error:
                    logger.log_error("paddleocr_fallback_init", paddle_error)
                    
                    # Try EasyOCR as final fallback
                    try:
                        import easyocr
                        self.easyocr_instance = easyocr.Reader(['en'])
                        self.engine = "easyocr"
                        logger.logger.info("EasyOCR initialized as final fallback")
                    except Exception as easy_error:
                        logger.log_error("easyocr_init", easy_error)
                        raise RuntimeError(
                            "All OCR engines failed. Please try:\n"
                            "1. Reinstall OCR packages: pip uninstall paddlepaddle paddleocr easyocr && pip install easyocr\n"
                            "2. Or install Tesseract: see install_tesseract_windows.md\n"
                            f"PaddleOCR Error: {str(paddle_error)}\n"
                            f"EasyOCR Error: {str(easy_error)}"
                        )
    
    @timer(logger)
    def preprocess_image(self, image: Union[np.ndarray, Image.Image]) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: Input image
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Convert PIL to numpy if needed
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Convert to grayscale if colored
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.log_error("image_preprocessing", e)
            # Return original image if preprocessing fails
            if isinstance(image, Image.Image):
                return np.array(image)
            return image
    
    @timer(logger)
    def extract_text_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text using Tesseract OCR.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with extracted text and confidence data
        """
        try:
            # Get detailed data from Tesseract
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, config='--psm 6'
            )
            
            # Extract text with confidence
            text_blocks = []
            confidences = []
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = data['conf'][i]
                
                if text and conf > 0:  # Only include text with positive confidence
                    text_blocks.append(text)
                    confidences.append(conf / 100.0)  # Convert to 0-1 scale
            
            # Combine all text
            full_text = ' '.join(text_blocks)
            
            # Calculate overall confidence
            overall_confidence = np.mean(confidences) if confidences else 0.0
            
            return {
                'text': full_text,
                'confidence': overall_confidence,
                'word_confidences': confidences,
                'word_count': len(text_blocks),
                'engine': 'tesseract'
            }
            
        except Exception as e:
            logger.log_error("tesseract_extraction", e)
            return {
                'text': '',
                'confidence': 0.0,
                'word_confidences': [],
                'word_count': 0,
                'engine': 'tesseract',
                'error': str(e)
            }
    
    @timer(logger)
    def extract_text_paddleocr(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text using PaddleOCR.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with extracted text and confidence data
        """
        try:
            if self.paddleocr_instance is None:
                raise RuntimeError("PaddleOCR not initialized")
            
            # PaddleOCR expects RGB image
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Assume it's already RGB
                rgb_image = image
            else:
                # Convert grayscale to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            # Run OCR
            results = self.paddleocr_instance.ocr(rgb_image, cls=True)
            
            if not results or not results[0]:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'word_confidences': [],
                    'word_count': 0,
                    'engine': 'paddleocr'
                }
            
            # Extract text and confidences
            text_blocks = []
            confidences = []
            
            for line in results[0]:
                if line:
                    bbox, (text, conf) = line
                    if text.strip():
                        text_blocks.append(text.strip())
                        confidences.append(conf)
            
            # Combine all text
            full_text = ' '.join(text_blocks)
            
            # Calculate overall confidence
            overall_confidence = np.mean(confidences) if confidences else 0.0
            
            return {
                'text': full_text,
                'confidence': overall_confidence,
                'word_confidences': confidences,
                'word_count': len(text_blocks),
                'engine': 'paddleocr'
            }
            
        except Exception as e:
            logger.log_error("paddleocr_extraction", e)
            return {
                'text': '',
                'confidence': 0.0,
                'word_confidences': [],
                'word_count': 0,
                'engine': 'paddleocr',
                'error': str(e)
            }
    
    @timer(logger)
    def extract_text_easyocr(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text using EasyOCR.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with extracted text and confidence data
        """
        try:
            if self.easyocr_instance is None:
                raise RuntimeError("EasyOCR not initialized")
            
            # EasyOCR expects RGB image
            if len(image.shape) == 3 and image.shape[2] == 3:
                rgb_image = image
            else:
                # Convert grayscale to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            # Run OCR
            results = self.easyocr_instance.readtext(rgb_image)
            
            if not results:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'word_confidences': [],
                    'word_count': 0,
                    'engine': 'easyocr'
                }
            
            # Extract text and confidences
            text_blocks = []
            confidences = []
            
            for (bbox, text, conf) in results:
                if text.strip():
                    text_blocks.append(text.strip())
                    confidences.append(conf)
            
            # Combine all text
            full_text = ' '.join(text_blocks)
            
            # Calculate overall confidence
            overall_confidence = np.mean(confidences) if confidences else 0.0
            
            return {
                'text': full_text,
                'confidence': overall_confidence,
                'word_confidences': confidences,
                'word_count': len(text_blocks),
                'engine': 'easyocr'
            }
            
        except Exception as e:
            logger.log_error("easyocr_extraction", e)
            return {
                'text': '',
                'confidence': 0.0,
                'word_confidences': [],
                'word_count': 0,
                'engine': 'easyocr',
                'error': str(e)
            }
    
    @timer(logger)
    def convert_pdf_to_images(self, pdf_path: Union[str, bytes]) -> List[Image.Image]:
        """
        Convert PDF to images.
        
        Args:
            pdf_path: Path to PDF file or PDF bytes
            
        Returns:
            List of PIL Images
        """
        try:
            if isinstance(pdf_path, bytes):
                images = convert_from_bytes(pdf_path)
            else:
                images = convert_from_path(pdf_path)
            
            logger.logger.info(f"Converted PDF to {len(images)} images")
            return images
            
        except Exception as e:
            logger.log_error("pdf_conversion", e)
            
            # Check if it's a Poppler-related error
            if "poppler" in str(e).lower() or "pdfinfo" in str(e).lower():
                logger.logger.warning("Poppler not available for PDF processing. PDF files will not be supported.")
                logger.logger.info("To enable PDF support, install Poppler: https://poppler.freedesktop.org/")
            
            return []
    
    @timer(logger)
    def process_file(self, file_path: Union[str, bytes], 
                    file_type: str = "auto") -> Dict[str, Any]:
        """
        Process a file (image or PDF) and extract text.
        
        Args:
            file_path: Path to file or file bytes
            file_type: Type of file ("image", "pdf", or "auto")
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            if isinstance(file_path, bytes):
                # Handle bytes input
                if file_type == "pdf" or file_type == "auto":
                    # Try as PDF first
                    try:
                        images = self.convert_pdf_to_images(file_path)
                        if images:
                            return self._process_images(images, source="pdf_bytes")
                    except:
                        pass
                
                # Try as image
                try:
                    import io
                    image = Image.open(io.BytesIO(file_path))
                    return self._process_images([image], source="image_bytes")
                except Exception as e:
                    logger.log_error("bytes_processing", e)
                    return self._empty_result()
            
            else:
                # Handle file path
                file_path = Path(file_path)
                
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Determine file type
                ext = file_path.suffix.lower()
                
                if ext == '.pdf' or file_type == "pdf":
                    images = self.convert_pdf_to_images(str(file_path))
                    return self._process_images(images, source=str(file_path))
                
                elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'] or file_type == "image":
                    image = Image.open(file_path)
                    return self._process_images([image], source=str(file_path))
                
                else:
                    raise ValueError(f"Unsupported file type: {ext}")
        
        except Exception as e:
            logger.log_error("file_processing", e)
            return self._empty_result(error=str(e))
    
    def _process_images(self, images: List[Image.Image], source: str = "") -> Dict[str, Any]:
        """Process multiple images and combine results."""
        all_text = []
        all_confidences = []
        total_words = 0
        
        for i, image in enumerate(images):
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text based on engine
            if self.engine == "paddleocr":
                result = self.extract_text_paddleocr(processed_image)
            elif self.engine == "easyocr":
                result = self.extract_text_easyocr(processed_image)
            else:
                result = self.extract_text_tesseract(processed_image)
            
            if result['text']:
                all_text.append(result['text'])
                all_confidences.extend(result['word_confidences'])
                total_words += result['word_count']
        
        # Combine results
        combined_text = '\n'.join(all_text)
        overall_confidence = np.mean(all_confidences) if all_confidences else 0.0
        
        return {
            'text': combined_text,
            'confidence': overall_confidence,
            'word_count': total_words,
            'page_count': len(images),
            'engine': self.engine,
            'source': source,
            'pages': all_text  # Individual page texts
        }
    
    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """Return empty result structure."""
        result = {
            'text': '',
            'confidence': 0.0,
            'word_count': 0,
            'page_count': 0,
            'engine': self.engine,
            'source': '',
            'pages': []
        }
        
        if error:
            result['error'] = error
        
        return result

