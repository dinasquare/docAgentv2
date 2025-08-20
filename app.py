"""
Streamlit application for document extraction with Gemini AI.
"""

import streamlit as st
import pandas as pd

import json
import time
from pathlib import Path
import tempfile
import os

# Import our utilities
from utils import (
    OCRProcessor, DocumentClassifier, GeminiExtractor, 
    ConfidenceScorer, DataValidator, save_json, load_json
)
from utils.io_helpers import (
    create_download_data, get_file_info, format_file_size,
    create_temp_file, cleanup_temp_file, validate_file_type
)
from config.config import config

# Configure Streamlit page
st.set_page_config(
    page_title="Document AI Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .confidence-high { color: #28a745; font-weight: bold; }
    .confidence-medium { color: #ffc107; font-weight: bold; }
    .confidence-low { color: #dc3545; font-weight: bold; }
    
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    if 'confidence_scores' not in st.session_state:
        st.session_state.confidence_scores = {}
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None
    if 'ocr_result' not in st.session_state:
        st.session_state.ocr_result = None
    if 'doc_type' not in st.session_state:
        st.session_state.doc_type = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

def create_confidence_chart(confidence_scores):
    """Create confidence visualization chart using Streamlit."""
    if not confidence_scores:
        return None
    
    # Prepare data for visualization
    df = pd.DataFrame({
        'Field': list(confidence_scores.keys()),
        'Confidence': list(confidence_scores.values())
    })
    
    # Sort by confidence for better visualization
    df = df.sort_values('Confidence', ascending=True)
    
    return df

def display_confidence_summary(confidence_summary):
    """Display confidence summary metrics."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        overall_conf = confidence_summary.get('overall_confidence', 0)
        color_class = 'confidence-high' if overall_conf >= 0.8 else 'confidence-medium' if overall_conf >= 0.6 else 'confidence-low'
        st.markdown(f"""
        <div class="metric-card">
            <h4>Overall Confidence</h4>
            <p class="{color_class}">{overall_conf:.1%}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        low_conf_count = confidence_summary.get('low_confidence_count', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Low Confidence Fields</h4>
            <p style="color: #dc3545; font-weight: bold;">{low_conf_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        field_count = confidence_summary.get('field_count', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Total Fields</h4>
            <p style="color: #6c757d; font-weight: bold;">{field_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_conf = confidence_summary.get('average_confidence', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Average Confidence</h4>
            <p style="color: #6c757d; font-weight: bold;">{avg_conf:.1%}</p>
        </div>
        """, unsafe_allow_html=True)

def display_low_confidence_warnings(low_confidence_fields):
    """Display warnings for low confidence fields."""
    if not low_confidence_fields:
        return
    
    st.markdown("""
    <div class="warning-box">
        <h4>⚠️ Low Confidence Fields</h4>
        <p>The following fields have low confidence scores and may need manual review:</p>
    </div>
    """, unsafe_allow_html=True)
    
    for field, confidence in low_confidence_fields:
        st.markdown(f"- **{field}**: {confidence:.1%} confidence")

def display_validation_results(validation_result):
    """Display validation results."""
    if not validation_result:
        return
    
    if validation_result.get('is_valid', False):
        st.markdown("""
        <div class="success-box">
            <h4>✅ Validation Passed</h4>
            <p>All extracted data passed validation checks.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="error-box">
            <h4>❌ Validation Errors</h4>
            <p>The following validation errors were found:</p>
        </div>
        """, unsafe_allow_html=True)
        
        for error in validation_result.get('errors', []):
            st.markdown(f"- {error}")
    
    # Show warnings if any
    warnings = validation_result.get('warnings', [])
    if warnings:
        st.markdown("**Warnings:**")
        for warning in warnings:
            st.markdown(f"- {warning}")

def process_document(uploaded_file):
    """Process uploaded document through the full pipeline."""
    try:
        # Initialize processors with error handling
        try:
            ocr_processor = OCRProcessor(engine=config.OCR_ENGINE)
            st.write(f"✅ **OCR Engine**: {ocr_processor.engine}")
        except RuntimeError as e:
            st.error(f"❌ OCR Initialization Error: {str(e)}")
            return False
        
        classifier = DocumentClassifier()
        extractor = GeminiExtractor()
        confidence_scorer = ConfidenceScorer()
        validator = DataValidator()
        
        # Get file info
        file_bytes = uploaded_file.read()
        file_info = get_file_info(file_bytes, uploaded_file.name)
        
        st.write(f"📁 **File:** {file_info['filename']} ({format_file_size(file_info['size'])})")
        
        # Step 1: OCR Processing
        with st.spinner("🔍 Extracting text from document..."):
            ocr_result = ocr_processor.process_file(file_bytes, file_type="auto")
            st.session_state.ocr_result = ocr_result
        
        if not ocr_result.get('text'):
            if file_info['is_pdf']:
                st.error("❌ Could not extract text from PDF. This may be due to missing Poppler installation.")
                st.info("💡 **Solution**: Try uploading the document as an image (JPG, PNG) instead, or install Poppler for PDF support.")
            else:
                st.error("❌ Could not extract text from the document. Please check if the image contains readable text.")
            return False
        
        st.success(f"✅ Text extracted ({ocr_result.get('word_count', 0)} words, confidence: {ocr_result.get('confidence', 0):.1%})")
        
        # Step 2: Document Classification
        with st.spinner("🏷️ Classifying document type..."):
            doc_type, classification_confidence = classifier.classify(
                ocr_result['text'], extractor
            )
            st.session_state.doc_type = doc_type
        
        st.success(f"✅ Document classified as **{doc_type}** (confidence: {classification_confidence:.1%})")
        
        # Step 3: Schema Loading
        try:
            schema = config.get_schema(doc_type)
        except FileNotFoundError:
            st.error(f"❌ Schema not found for document type: {doc_type}")
            return False
        
        # Step 4: Data Extraction
        with st.spinner("🤖 Extracting structured data with Gemini..."):
            if st.sidebar.checkbox("Use Self-Consistency", value=True):
                extraction_result = extractor.self_consistency_extraction(
                    ocr_result['text'], doc_type, schema
                )
                extracted_data = extraction_result.get('data')
                st.write(f"🔄 Self-consistency: {extraction_result.get('successful_attempts', 0)}/{extraction_result.get('total_attempts', 0)} successful attempts")
            else:
                extraction_result = extractor.extract_structured_data(
                    ocr_result['text'], doc_type, schema
                )
                extracted_data = extraction_result.get('data')
        
        if not extracted_data:
            st.error("❌ Failed to extract structured data.")
            return False
        
        st.session_state.extracted_data = extracted_data
        st.success("✅ Structured data extracted successfully")
        
        # Step 5: Confidence Assessment
        with st.spinner("📊 Calculating confidence scores..."):
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
            
            st.session_state.confidence_scores = field_confidences
        
        st.success("✅ Confidence scores calculated")
        
        # Step 6: Data Validation
        with st.spinner("✅ Validating extracted data..."):
            validation_result = validator.validate_document(extracted_data, doc_type)
            st.session_state.validation_result = validation_result
        
        st.success("✅ Data validation completed")
        
        st.session_state.processing_complete = True
        return True
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
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
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📄 Document AI Extractor</h1>
        <p>Extract structured data from invoices, bills, and prescriptions using Gemini AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # API Key check
    if not config.GEMINI_API_KEY:
        st.sidebar.error("❌ Gemini API key not configured!")
        st.sidebar.write("Please set GEMINI_API_KEY in your environment variables.")
        return
    
    st.sidebar.success("✅ Gemini API configured")
    
    # OCR Engine selection
    ocr_engine = st.sidebar.selectbox(
        "OCR Engine",
        ["tesseract", "paddleocr"],
        index=0 if config.OCR_ENGINE == "tesseract" else 1
    )
    
    # Confidence threshold
    confidence_threshold = st.sidebar.slider(
        "Low Confidence Threshold",
        min_value=0.1,
        max_value=0.9,
        value=config.LOW_CONFIDENCE_THRESHOLD,
        step=0.05
    )
    
    # Custom schema option
    st.sidebar.subheader("🛠️ Custom Schema")
    use_custom_schema = st.sidebar.checkbox("Use Custom Schema")
    
    if use_custom_schema:
        custom_schema_text = st.sidebar.text_area(
            "Custom JSON Schema",
            height=200,
            help="Enter a custom JSON schema for extraction"
        )
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload & Extract", "📊 Results", "🔍 Confidence Analysis", "⚙️ Advanced"])
    
    with tab1:
        st.header("Upload Document")
        
        uploaded_file = st.file_uploader(
            "Choose a document file",
            type=['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'],
            help="Supported formats: PDF, JPEG, PNG, BMP, TIFF"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.write("**File Details:**")
                file_info = get_file_info(uploaded_file.getvalue(), uploaded_file.name)
                st.write(f"- **Name:** {file_info['filename']}")
                st.write(f"- **Size:** {format_file_size(file_info['size'])}")
                st.write(f"- **Type:** {file_info['extension'].upper()}")
                
                # Process button
                if st.button("🚀 Process Document", type="primary"):
                    success = process_document(uploaded_file)
                    if success:
                        st.rerun()
            
            with col2:
                # Show file preview if it's an image
                if file_info['is_image']:
                    st.image(uploaded_file, caption="Document Preview", use_container_width=True)
                elif file_info['is_pdf']:
                    st.write("📄 PDF document uploaded (preview not available)")
    
    with tab2:
        st.header("Extraction Results")
        
        if st.session_state.processing_complete and st.session_state.extracted_data:
            # Display extracted data
            st.subheader("📋 Extracted Data")
            
            # JSON viewer with copy/download options
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.json(st.session_state.extracted_data)
            
            with col2:
                # Download button
                download_data = create_download_data(
                    st.session_state.extracted_data,
                    f"extracted_{st.session_state.doc_type}_{int(time.time())}.json"
                )
                
                st.download_button(
                    label="📥 Download JSON",
                    data=download_data['data'],
                    file_name=download_data['filename'],
                    mime=download_data['mime_type']
                )
                
                # Copy to clipboard (JavaScript)
                if st.button("📋 Copy JSON"):
                    st.write("JSON copied to clipboard!")
                    st.code(json.dumps(st.session_state.extracted_data, indent=2))
            
            # Display validation results
            st.subheader("✅ Validation Results")
            display_validation_results(st.session_state.validation_result)
            
            # Retry/Edit options
            st.subheader("🔄 Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Re-extract"):
                    if uploaded_file is not None:
                        success = process_document(uploaded_file)
                        if success:
                            st.rerun()
            
            with col2:
                if st.button("🛠️ Fix Validation Errors"):
                    if st.session_state.validation_result and not st.session_state.validation_result.get('is_valid', True):
                        with st.spinner("Fixing validation errors..."):
                            extractor = GeminiExtractor()
                            fixed_data = extractor.fix_validation_errors(
                                st.session_state.extracted_data,
                                st.session_state.validation_result.get('errors', [])
                            )
                            st.session_state.extracted_data = fixed_data
                            st.rerun()
            
            with col3:
                if st.button("📝 Manual Edit"):
                    st.info("Manual editing will be available in the Advanced tab.")
        
        else:
            st.info("👆 Please upload and process a document first.")
    
    with tab3:
        st.header("Confidence Analysis")
        
        if st.session_state.processing_complete and st.session_state.confidence_scores:
            # Calculate confidence summary
            confidence_scorer = ConfidenceScorer(confidence_threshold)
            overall_confidence = confidence_scorer.calculate_overall_confidence(
                st.session_state.confidence_scores
            )
            confidence_summary = confidence_scorer.get_confidence_summary(
                st.session_state.confidence_scores,
                overall_confidence
            )
            
            # Display confidence metrics
            display_confidence_summary(confidence_summary)
            
            # Confidence chart
            st.subheader("📊 Field Confidence Scores")
            df = create_confidence_chart(st.session_state.confidence_scores)
            if df is not None:
                # Create a horizontal bar chart using Streamlit
                st.bar_chart(df.set_index('Field')['Confidence'], horizontal=True)
                
                # Also show a color-coded progress bars for each field
                st.subheader("🎯 Detailed Field Confidence")
                for _, row in df.iterrows():
                    field = row['Field']
                    confidence = row['Confidence']
                    
                    # Color coding based on confidence level
                    if confidence >= 0.8:
                        color = "green"
                        status = "High"
                    elif confidence >= 0.6:
                        color = "orange" 
                        status = "Medium"
                    else:
                        color = "red"
                        status = "Low"
                    
                    # Display field with progress bar
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{field}**")
                    with col2:
                        st.progress(confidence)
                    with col3:
                        st.write(f"{confidence:.1%} ({status})")
            
            # Low confidence warnings
            low_confidence_fields = confidence_summary.get('low_confidence_fields', [])
            if low_confidence_fields:
                display_low_confidence_warnings(low_confidence_fields)
            
            # Detailed field analysis
            st.subheader("🔍 Detailed Field Analysis")
            
            # Create DataFrame for detailed view
            field_details = []
            for field, confidence in st.session_state.confidence_scores.items():
                field_value = _get_nested_value(st.session_state.extracted_data, field)
                field_details.append({
                    'Field': field,
                    'Value': str(field_value) if field_value is not None else 'N/A',
                    'Confidence': f"{confidence:.1%}",
                    'Status': '✅ High' if confidence >= 0.8 else '⚠️ Medium' if confidence >= 0.6 else '❌ Low'
                })
            
            df = pd.DataFrame(field_details)
            st.dataframe(df, use_container_width=True)
        
        else:
            st.info("👆 Please process a document first to see confidence analysis.")
    
    with tab4:
        st.header("Advanced Options")
        
        # Manual JSON editing
        if st.session_state.extracted_data:
            st.subheader("📝 Manual Data Editing")
            
            edited_json = st.text_area(
                "Edit JSON Data",
                value=json.dumps(st.session_state.extracted_data, indent=2),
                height=400,
                help="Edit the extracted JSON data manually"
            )
            
            if st.button("💾 Save Changes"):
                try:
                    new_data = json.loads(edited_json)
                    st.session_state.extracted_data = new_data
                    st.success("✅ Changes saved successfully")
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {str(e)}")
        
        # OCR Results
        if st.session_state.ocr_result:
            st.subheader("🔍 OCR Results")
            
            with st.expander("View Raw OCR Text"):
                st.text_area(
                    "Extracted Text",
                    value=st.session_state.ocr_result.get('text', ''),
                    height=200,
                    disabled=True
                )
            
            ocr_metrics = {
                'Engine': st.session_state.ocr_result.get('engine', 'Unknown'),
                'Word Count': st.session_state.ocr_result.get('word_count', 0),
                'Pages': st.session_state.ocr_result.get('page_count', 1),
                'Confidence': f"{st.session_state.ocr_result.get('confidence', 0):.1%}"
            }
            
            st.json(ocr_metrics)
        
        # System Information
        st.subheader("ℹ️ System Information")
        system_info = {
            'Gemini Model': config.GEMINI_MODEL,
            'OCR Engine': config.OCR_ENGINE,
            'Confidence Threshold': config.LOW_CONFIDENCE_THRESHOLD,
            'Self-Consistency Runs': config.SELF_CONSISTENCY_RUNS
        }
        st.json(system_info)

if __name__ == "__main__":
    main()

