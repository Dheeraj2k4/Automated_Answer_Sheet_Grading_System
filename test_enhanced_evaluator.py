import os
from scan.enhanced_evaluator import EnhancedEvaluator

def main():
    # Get the absolute paths to our files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    answer_sheet_path = os.path.join(current_dir, 'uploads', 'answer_sheets', 'answer_sheet.pdf')
    answer_key_path = os.path.join(current_dir, 'uploads', 'answer_keys', 'answer_key.docx')
    output_file = os.path.join(current_dir, 'results', 'evaluation_results.json')

    # Create results directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"Processing answer sheet: {answer_sheet_path}")
    print(f"Using answer key: {answer_key_path}")
    print(f"Results will be saved to: {output_file}")

    # Initialize and run the evaluator
    evaluator = EnhancedEvaluator()
    evaluator.process_answer_sheet(answer_sheet_path, answer_key_path, output_file)

if __name__ == "__main__":
    main() 