import pytesseract
from PIL import Image
import cv2
import numpy as np
import fitz  # PyMuPDF

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_tesseract():
    """Test if Tesseract is properly configured."""
    try:
        print("Tesseract version:", pytesseract.get_tesseract_version())
        print("Tesseract path:", pytesseract.tesseract_cmd)
        return True
    except Exception as e:
        print("Error testing Tesseract:", str(e))
        return False

def test_opencv():
    """Test if OpenCV is properly installed."""
    try:
        print("OpenCV version:", cv2.__version__)
        return True
    except Exception as e:
        print("Error testing OpenCV:", str(e))
        return False

def test_pymupdf():
    """Test if PyMuPDF is properly installed."""
    try:
        print("PyMuPDF version:", fitz.__version__)
        return True
    except Exception as e:
        print("Error testing PyMuPDF:", str(e))
        return False

if __name__ == "__main__":
    print("Testing OCR setup...")
    print("\n1. Testing Tesseract:")
    tesseract_ok = test_tesseract()
    
    print("\n2. Testing OpenCV:")
    opencv_ok = test_opencv()
    
    print("\n3. Testing PyMuPDF:")
    pymupdf_ok = test_pymupdf()
    
    print("\nSummary:")
    print(f"Tesseract: {'✓' if tesseract_ok else '✗'}")
    print(f"OpenCV: {'✓' if opencv_ok else '✗'}")
    print(f"PyMuPDF: {'✓' if pymupdf_ok else '✗'}")
    
    if all([tesseract_ok, opencv_ok, pymupdf_ok]):
        print("\nAll components are properly installed and configured!")
    else:
        print("\nSome components are not properly configured. Please check the errors above.") 