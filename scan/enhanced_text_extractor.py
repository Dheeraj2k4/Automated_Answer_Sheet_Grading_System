import os
from google.cloud import vision
from pdf2image import convert_from_path
from PIL import Image
import io
import sys
import json
import requests
from typing import Dict, List, Tuple

# Configure Poppler path - Update this path to where you extracted Poppler
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"

class EnhancedTextExtractor:
    def __init__(self):
        # Verify Google Cloud credentials
        if not self.verify_credentials():
            raise Exception("Google Cloud credentials not properly configured")
            
        # Initialize Vision API client
        self.vision_client = vision.ImageAnnotatorClient()
        
        # Mistral API configuration
        self.mistral_api_endpoint = os.getenv("MISTRAL_API_ENDPOINT", "YOUR_MISTRAL_API_ENDPOINT")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY", "YOUR_MISTRAL_API_KEY")

    def verify_credentials(self) -> bool:
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

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from an image using Google Cloud Vision API."""
        try:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Create Vision API image object
            vision_image = vision.Image(content=img_byte_arr)
            
            # Perform text detection
            response = self.vision_client.document_text_detection(image=vision_image)
            
            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))
            
            return response.full_text_annotation.text
        except Exception as e:
            print(f"Error in text extraction: {str(e)}")
            return ""

    def correct_text_with_mistral(self, text: str) -> str:
        """Use Mistral 7B to correct and improve the extracted text."""
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""You are a precise text correction system. Your task is to fix ONLY obvious errors in the following text while preserving the original content as much as possible.

Rules:
1. Only fix clear spelling mistakes and obvious grammatical errors
2. DO NOT change the meaning or rephrase the text
3. DO NOT modify technical terms, equations, or special formatting
4. DO NOT add or remove content
5. If a word is unclear but could be correct, leave it as is
6. Preserve all numbers, dates, and measurements exactly as they appear
7. Keep all original punctuation and formatting

Text to correct:
{text}

Corrected text (only fix obvious errors):"""
        
        data = {
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.3,  # Lower temperature for more conservative output
            "top_p": 0.1,       # Lower top_p for more focused corrections
            "frequency_penalty": 0.5,  # Penalize frequent corrections
            "presence_penalty": 0.5    # Penalize adding new content
        }
        
        try:
            response = requests.post(
                self.mistral_api_endpoint,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            corrected_text = response.json()["choices"][0]["text"].strip()
            
            # Additional validation to ensure minimal changes
            original_words = set(text.lower().split())
            corrected_words = set(corrected_text.lower().split())
            
            # If more than 20% of words were changed, return original text
            if len(original_words.symmetric_difference(corrected_words)) / len(original_words) > 0.2:
                print("Warning: Too many changes detected, returning original text")
                return text
                
            return corrected_text
            
        except Exception as e:
            print(f"Error calling Mistral API: {str(e)}")
            return text  # Return original text if API call fails

    def process_pdf(self, pdf_path: str, output_file: str, correct_text: bool = True) -> None:
        """Process PDF and extract text from each page, with optional Mistral correction."""
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
        
        # Extract and process text from each page
        all_text = []
        for i, image in enumerate(images):
            print(f"Processing page {i+1}/{len(images)}")
            try:
                # Extract text using Vision API
                text = self.extract_text_from_image(image)
                if text:
                    if correct_text:
                        print(f"Correcting text for page {i+1}...")
                        text = self.correct_text_with_mistral(text)
                    
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
    # Get PDF path from command line argument or prompt
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("Enter the path to your PDF file: ").strip('"')  # Remove quotes if present
    
    # Get output file path
    output_file = "output.txt"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Check if text correction should be skipped
    skip_correction = "--skip-correction" in sys.argv
    
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        return
    
    try:
        extractor = EnhancedTextExtractor()
        extractor.process_pdf(pdf_path, output_file, correct_text=not skip_correction)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 