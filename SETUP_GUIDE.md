# Quick Setup Guide

## 🚀 Quick Start

1. **Activate Environment**
   ```bash
   conda activate doc
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**
   Create a `.env` file with:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GEMINI_MODEL=gemini-1.5-flash
   GEMINI_TEMPERATURE=0.2
   GEMINI_MAX_TOKENS=2048
   OCR_ENGINE=tesseract
   LOW_CONFIDENCE_THRESHOLD=0.7
   SELF_CONSISTENCY_RUNS=3
   ```

4. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## 🧪 Test the System

1. **Run Tests**
   ```bash
   python tests/run_tests.py
   ```

2. **Test with Sample Data**
   Use the sample text files in the `data/` directory to test the extraction pipeline.

3. **Test CLI**
   ```bash
   python main.py data/sample_text_invoice.txt
   ```

## 📁 Project Structure

```
docAgentv2/
├── app.py                    # Streamlit web app
├── main.py                  # CLI interface
├── requirements.txt         # Dependencies
├── README.md               # Full documentation
├── SETUP_GUIDE.md          # This file
│
├── config/                 # Schemas & configuration
│   ├── config.py
│   ├── invoice_schema.json
│   ├── bill_schema.json
│   └── prescription_schema.json
│
├── utils/                  # Core modules
│   ├── ocr.py             # OCR processing
│   ├── doc_classifier.py  # Document classification
│   ├── extractor.py       # Gemini extraction
│   ├── confidence.py      # Confidence scoring
│   ├── validation.py      # Data validation
│   ├── prompts.py         # AI prompts
│   ├── logger.py          # Logging
│   └── io_helpers.py      # File utilities
│
├── data/                  # Sample documents
├── tests/                 # Unit tests
└── env.example           # Environment template
```

## 🎯 Key Features

- **Multi-format Processing**: PDFs and images
- **Intelligent OCR**: Tesseract and PaddleOCR support
- **Auto-classification**: Invoice/Bill/Prescription detection
- **Gemini AI Extraction**: Structured JSON output
- **Confidence Scoring**: Per-field and overall confidence
- **Data Validation**: Automatic error detection
- **Modern UI**: Streamlit interface with visualizations
- **Self-consistency**: Multiple extraction runs for accuracy

## 🔧 Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure GEMINI_API_KEY is set in .env file
   - Verify API key is valid in Google AI Studio

2. **OCR Issues**
   - Install Tesseract: `sudo apt-get install tesseract-ocr` (Linux)
   - For Windows: Download from GitHub releases
   - Add to PATH environment variable

3. **Import Errors**
   - Run `pip install -r requirements.txt`
   - Ensure conda environment is activated

4. **Performance Issues**
   - Reduce SELF_CONSISTENCY_RUNS for faster processing
   - Use single extraction instead of self-consistency
   - Optimize image quality before processing

## ✅ Validation

The system has been tested with:
- ✅ All unit tests passing
- ✅ Streamlit UI functional
- ✅ CLI interface working
- ✅ Sample data processing
- ✅ Confidence scoring accurate
- ✅ Validation rules working
- ✅ Error handling robust

This completes a production-ready document extraction system using Gemini AI!

