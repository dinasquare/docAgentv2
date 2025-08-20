# Installing Tesseract OCR on Windows

## Quick Fix (Recommended)
The system will automatically fall back to PaddleOCR if Tesseract is not available. PaddleOCR works well on Windows without additional setup.

## If you prefer Tesseract OCR:

### Option 1: Download and Install Tesseract
1. **Download Tesseract for Windows:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download the latest Windows installer (e.g., `tesseract-ocr-w64-setup-5.3.3.20231005.exe`)

2. **Install Tesseract:**
   - Run the installer
   - **Important:** During installation, note the installation path (usually `C:\Program Files\Tesseract-OCR`)

3. **Add to PATH:**
   - Open System Environment Variables
   - Add the Tesseract installation path to your PATH environment variable
   - Example: `C:\Program Files\Tesseract-OCR`

4. **Restart your terminal/IDE**

### Option 2: Using Conda (Alternative)
```bash
conda install -c conda-forge tesseract
```

### Option 3: Using Chocolatey (if you have it)
```bash
choco install tesseract
```

## Verify Installation
After installation, verify Tesseract works:
```bash
tesseract --version
```

## Update Environment
If you installed Tesseract, update your `.env` file:
```
OCR_ENGINE=tesseract
```

## Troubleshooting
- **PATH Issues**: Make sure Tesseract is in your system PATH
- **Permission Issues**: Run installation as Administrator
- **Version Issues**: Use the latest version from the official repository

## Why PaddleOCR is Recommended for Windows
- ✅ No additional installation required
- ✅ Better handling of complex layouts
- ✅ Works well with handwritten text
- ✅ No PATH configuration needed
- ❌ Larger initial download (models)
- ❌ Requires more RAM
