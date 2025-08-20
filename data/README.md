# Sample Documents

This directory contains sample documents for testing the document extraction system.

## Document Types

### Invoices
- `sample_invoice_typed.pdf` - Typed invoice document
- `sample_invoice_handwritten.jpg` - Handwritten invoice image

### Bills
- `sample_bill_typed.pdf` - Typed utility bill
- `sample_bill_handwritten.jpg` - Handwritten bill image

### Prescriptions
- `sample_prescription_typed.pdf` - Typed prescription
- `sample_prescription_handwritten.jpg` - Handwritten prescription

## Usage

These sample documents can be used to test the extraction system both via the Streamlit UI and command-line interface.

### Via Streamlit
1. Run `streamlit run app.py`
2. Upload any of these sample documents
3. Process and review results

### Via CLI
```bash
python main.py data/sample_invoice_typed.pdf
python main.py data/sample_bill_typed.pdf -t bill
python main.py data/sample_prescription_typed.pdf -o results.json
```

## Notes

- Sample documents are placeholder files for demonstration
- In a real implementation, you would have actual document images/PDFs
- The OCR and extraction system will work with real documents
- These samples help test the pipeline and UI functionality

