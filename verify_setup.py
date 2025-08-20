"""
Setup verification script to check if all components are working.
"""

import sys
import traceback

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        import streamlit
        print("✅ Streamlit")
    except ImportError as e:
        print(f"❌ Streamlit: {e}")
        return False
    
    try:
        import google.generativeai
        print("✅ Google Generative AI")
    except ImportError as e:
        print(f"❌ Google Generative AI: {e}")
        return False
    
    try:
        from config.config import config
        print("✅ Configuration")
    except ImportError as e:
        print(f"❌ Configuration: {e}")
        return False
    
    return True

def test_ocr():
    """Test OCR initialization."""
    print("\n🔍 Testing OCR engines...")
    
    try:
        from utils.ocr import OCRProcessor
        
        # Test EasyOCR
        try:
            ocr = OCRProcessor(engine="easyocr")
            print(f"✅ EasyOCR initialized successfully")
            return True
        except Exception as e:
            print(f"❌ EasyOCR failed: {e}")
        
        # Test PaddleOCR
        try:
            ocr = OCRProcessor(engine="paddleocr")
            print(f"✅ PaddleOCR initialized successfully")
            return True
        except Exception as e:
            print(f"❌ PaddleOCR failed: {e}")
        
        # Test Tesseract
        try:
            ocr = OCRProcessor(engine="tesseract")
            print(f"✅ Tesseract initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Tesseract failed: {e}")
        
        print("❌ No OCR engine available")
        return False
        
    except Exception as e:
        print(f"❌ OCR module import failed: {e}")
        return False

def test_gemini():
    """Test Gemini API connection."""
    print("\n🤖 Testing Gemini AI...")
    
    try:
        from config.config import config
        
        if not config.GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY not found in environment")
            return False
        
        from utils.extractor import GeminiExtractor
        extractor = GeminiExtractor()
        
        # Test a simple call
        response = extractor.call_gemini("Hello, respond with 'OK'", max_tokens=10)
        
        if 'error' in response:
            print(f"❌ Gemini API error: {response['error']}")
            return False
        
        print("✅ Gemini AI connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        traceback.print_exc()
        return False

def test_utilities():
    """Test utility modules."""
    print("\n🔧 Testing utility modules...")
    
    try:
        from utils import (
            DocumentClassifier, ConfidenceScorer, 
            DataValidator, save_json, load_json
        )
        print("✅ All utility modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Utility modules failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🚀 Document AI Extractor - Setup Verification")
    print("=" * 50)
    
    all_tests = [
        test_imports,
        test_utilities,
        test_ocr,
        test_gemini
    ]
    
    results = []
    for test in all_tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    if all(results):
        print("🎉 All tests passed! The system is ready to use.")
        print("\n🚀 Next steps:")
        print("1. Run: streamlit run app.py")
        print("2. Upload a document and test extraction")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Common fixes:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Set GEMINI_API_KEY in .env file")
        print("3. For OCR issues, try: python fix_ocr_dependencies.py")

if __name__ == "__main__":
    main()
