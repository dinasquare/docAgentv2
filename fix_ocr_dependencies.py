"""
Script to fix OCR dependencies and install the correct versions.
"""

import subprocess
import sys
import platform

def run_command(command):
    """Run a command and return success status."""
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {command}")
        print(f"Error: {e.stderr}")
        return False

def fix_paddle_ocr():
    """Fix PaddleOCR dependencies."""
    print("🔧 Fixing PaddleOCR dependencies...")
    
    # Uninstall existing packages
    commands = [
        "pip uninstall -y paddlepaddle paddleocr",
        "pip install paddlepaddle==2.5.2",
        "pip install paddleocr==2.7.0.3"
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            return False
    
    return True

def install_easyocr():
    """Install EasyOCR as alternative."""
    print("🔧 Installing EasyOCR...")
    return run_command("pip install easyocr")

def main():
    """Main function to fix OCR issues."""
    print("🚀 OCR Dependencies Fix Script")
    print("=" * 40)
    
    print(f"Platform: {platform.system()}")
    
    # Try EasyOCR first (more reliable)
    if install_easyocr():
        print("✅ EasyOCR installed successfully!")
        print("💡 Update your .env file to use: OCR_ENGINE=easyocr")
    else:
        print("❌ EasyOCR installation failed")
        
        # Fallback to fixing PaddleOCR
        print("🔄 Trying to fix PaddleOCR...")
        if fix_paddle_ocr():
            print("✅ PaddleOCR fixed successfully!")
            print("💡 Update your .env file to use: OCR_ENGINE=paddleocr")
        else:
            print("❌ PaddleOCR fix failed")
            print("📋 Manual steps:")
            print("1. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("2. Add Tesseract to your PATH")
            print("3. Update your .env file to use: OCR_ENGINE=tesseract")
    
    print("\n🧪 Test the installation:")
    print("python -c \"from utils.ocr import OCRProcessor; print('OCR Engine:', OCRProcessor().engine)\"")

if __name__ == "__main__":
    main()
