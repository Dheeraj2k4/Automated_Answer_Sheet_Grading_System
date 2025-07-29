from paddleocr import PaddleOCR
import os
from typing import Dict, List, Tuple
import requests
import json

class DocumentProcessor:
    def __init__(self):
        # Initialize PaddleOCR with handwriting recognition model
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            rec_model_dir=None  # Will auto-download
        )
        
        # Download handwriting model if not already downloaded
        print("Initializing OCR model...")
        self.ocr.download_model('rec_en_server_handwritten')
        print("OCR model initialized successfully!")
        
        # Mistral API endpoint (you'll need to replace this with your actual endpoint)
        self.mistral_api_endpoint = "YOUR_MISTRAL_API_ENDPOINT"
        self.mistral_api_key = "YOUR_MISTRAL_API_KEY"

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image using PaddleOCR
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        result = self.ocr.ocr(image_path, cls=True)
        extracted_text = ""
        
        if result:
            for line in result[0]:
                if line[1][0]:  # Check if text was detected
                    extracted_text += line[1][0] + "\n"
                    
        return extracted_text.strip()

    def correct_text(self, text: str) -> str:
        """
        Use Mistral 7B to correct and improve the extracted text
        """
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Please correct and improve the following text extracted from a document. 
        Fix any spelling mistakes, grammatical errors, and improve clarity while maintaining the original meaning:
        
        {text}
        
        Corrected text:"""
        
        data = {
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.mistral_api_endpoint,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            corrected_text = response.json()["choices"][0]["text"].strip()
            return corrected_text
            
        except Exception as e:
            print(f"Error calling Mistral API: {str(e)}")
            return text  # Return original text if API call fails

    def process_document(self, image_path: str) -> Dict[str, str]:
        """
        Process a document: extract text and correct it
        """
        # Extract text using OCR
        extracted_text = self.extract_text(image_path)
        
        # Correct text using Mistral
        corrected_text = self.correct_text(extracted_text)
        
        return {
            "original_text": extracted_text,
            "corrected_text": corrected_text
        }

def main():
    # Example usage
    processor = DocumentProcessor()
    
    # Process a test image
    test_image = "test_image.png"  # Replace with your image path
    if os.path.exists(test_image):
        results = processor.process_document(test_image)
        print("\nOriginal Text:")
        print("-" * 50)
        print(results["original_text"])
        print("\nCorrected Text:")
        print("-" * 50)
        print(results["corrected_text"])
    else:
        print(f"Please place a test image at {test_image}")

if __name__ == "__main__":
    main() 