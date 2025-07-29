# PDF Text Extractor

This application extracts text from scanned PDFs containing handwritten text using Google Cloud Vision API.

## Prerequisites

1. Python 3.7 or higher
2. Google Cloud Vision API credentials (JSON key file)
3. Poppler (required for PDF processing)

## Installation

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Install Poppler:
   - Windows: Download and install from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Add the Poppler bin directory to your system PATH

3. Place your Google Cloud Vision API JSON key file in the project directory

## Usage

1. Run the script:
```bash
python pdf_text_extractor.py
```

2. When prompted:
   - Enter the path to your PDF file
   - Enter the desired output text file path (or press Enter for default: output.txt)

3. The script will:
   - Convert the PDF to images
   - Process each page using Google Cloud Vision API
   - Save the extracted text to the specified output file

## Notes

- The application uses Google Cloud Vision API's document text detection feature, which is optimized for handwritten text
- Processing time depends on the number of pages and image quality
- Make sure your PDF is readable and the handwritten text is clear 