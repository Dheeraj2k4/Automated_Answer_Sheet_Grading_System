from paddleocr import PaddleOCR
import os

# Initialize PaddleOCR with handwriting recognition model
ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en",
    rec_model_dir=None  # Will auto-download
)

# Download handwriting model
print("Downloading handwriting recognition model...")
ocr.download_model('rec_en_server_handwritten')
print("Model downloaded successfully!")

# Test OCR on a sample image
def test_ocr(image_path):
    result = ocr.ocr(image_path, cls=True)
    print("\nOCR Results:")
    print("-" * 50)
    if result:
        for line in result[0]:
            if line[1][0]:  # Check if text was detected
                print(line[1][0])
    print("-" * 50)

if __name__ == "__main__":
    # Test with a sample image
    test_image = "test_image.png"  # Replace with your image path
    if os.path.exists(test_image):
        test_ocr(test_image)
    else:
        print(f"Please place a test image at {test_image}") 