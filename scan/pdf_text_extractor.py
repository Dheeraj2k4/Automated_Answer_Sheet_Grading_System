import os
# Set Google Cloud Vision API credentials automatically
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "enhanced-oasis-461811-s7-669a06266020.json")

from google.cloud import vision
from pdf2image import convert_from_path
from PIL import Image
import io
import sys
import json
import PyPDF2

# Configure Poppler path - Update this path to where you extracted Poppler
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"

def verify_credentials():
    """Verify that the Google Cloud credentials are properly set up."""
    try:
        credentials_path = "enhanced-oasis-461811-s7-669a06266020.json"
        if not os.path.exists(credentials_path):
            print(f"Error: Credentials file {credentials_path} not found.")
            return False
        
        # Try to read the credentials file
        with open(credentials_path, 'r') as f:
            credentials = json.load(f)
        
        # Set the environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)
        return True
    except Exception as e:
        print(f"Error setting up credentials: {str(e)}")
        return False

def extract_text_from_image(image):
    """Extract text from an image using Google Cloud Vision API."""
    try:
        client = vision.ImageAnnotatorClient()
        
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Create Vision API image object
        vision_image = vision.Image(content=img_byte_arr)
        
        # Perform text detection
        response = client.document_text_detection(image=vision_image)
        
        if response.error.message:
            raise Exception(
                '{}\nFor more info on error messages, check: '
                'https://cloud.google.com/apis/design/errors'.format(
                    response.error.message))
        
        return response.full_text_annotation.text
    except Exception as e:
        print(f"Error in text extraction: {str(e)}")
        return ""

def process_pdf(pdf_path, output_file):
    """Process PDF and extract text from each page."""
    # Convert PDF to images
    print(f"Converting PDF to images: {pdf_path}")
    try:
        if not os.path.exists(POPPLER_PATH):
            print(f"Error: Poppler not found at {POPPLER_PATH}")
            print("Please download Poppler from: https://github.com/oschwartz10612/poppler-windows/releases/")
            print("Extract it to C:\\Program Files\\poppler-24.08.0\\")
            return
            
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        print("Please make sure Poppler is installed at the correct path")
        return
    
    # Extract text from each page
    all_text = []
    for i, image in enumerate(images):
        print(f"Processing page {i+1}/{len(images)}")
        try:
            text = extract_text_from_image(image)
            if text:
                all_text.append(f"\n--- Page {i+1} ---\n")
                all_text.append(text)
            else:
                print(f"No text detected on page {i+1}")
        except Exception as e:
            print(f"Error processing page {i+1}: {str(e)}")
    
    if not all_text:
        print("No text was extracted from any page.")
        return
    
    # Save extracted text to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_text))
        print(f"Text extraction complete. Results saved to: {output_file}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")

def main():
    # Verify credentials first
    if not verify_credentials():
        print("Please ensure you have the correct Google Cloud credentials file in the project directory.")
        return
    
    # Get PDF path from command line argument or prompt
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("Enter the path to your PDF file: ").strip('"')  # Remove quotes if present
    
    # Get output file path
    output_file = "output.txt"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        return
    
    try:
        process_pdf(pdf_path, output_file)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def process_pdf_pypdf2(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

if __name__ == "__main__":
    main() 