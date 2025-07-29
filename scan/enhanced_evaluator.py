import os
# Set Google Cloud Vision API credentials automatically
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "enhanced-oasis-461811-s7-669a06266020.json")

import sys
import json
from typing import Dict, List, Tuple
import requests
import re

# Add parent directory to path to import ml_project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scan.pdf_text_extractor import process_pdf
# from ml_project.test import evaluate_student_answers

class EnhancedEvaluator:
    def __init__(self):
        # Initialize Ollama endpoint
        self.ollama_endpoint = "http://localhost:11434/api/generate"
        self.model = "mistral"  # or your specific model name

    def extract_answers_from_text(self, text):
        """Extract answers from OCR text, capturing the answer from the start of the question until the next question is found."""
        lines = text.split('\n')
        answers = []
        current_answer = []
        question_pattern = re.compile(r'^(Q\d+\.|Q\d+\)|Q\d+|\d+\)|\d+\.|Q\s*\d+|Q.*\?)', re.IGNORECASE)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Detect question start by previous logic or by number pattern
            if question_pattern.match(line):
                if current_answer:
                    answers.append('\n'.join(current_answer))
                    current_answer = []
            current_answer.append(line)
        if current_answer:
            answers.append('\n'.join(current_answer))
        return answers

    def get_mistral_feedback(self, question: str, student_answer: str, ideal_answer: str) -> Tuple[float, str]:
        """Get feedback from Mistral model running on Ollama."""
        prompt = f"""You are an expert teacher evaluating a student's answer. Please evaluate the following:

Question: {question}
Ideal Answer: {ideal_answer}
Student's Answer: {student_answer}

Please provide:
1. A score out of 10
2. Detailed feedback on what was good and what could be improved
3. Specific suggestions for improvement

Format your response as JSON with these fields:
{{
    "score": <number between 0 and 10>,
    "feedback": "<detailed feedback>",
    "suggestions": ["<suggestion 1>", "<suggestion 2>", ...]
}}"""

        try:
            response = requests.post(
                self.ollama_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()

            # Parse the response
            result = response.json()
            evaluation = json.loads(result['response'])

            return evaluation['score'], evaluation['feedback']

        except Exception as e:
            print(f"Error getting Mistral feedback: {str(e)}")
            # Fallback to basic evaluation
            return self.basic_evaluation(student_answer, ideal_answer)

    def basic_evaluation(self, student_answer: str, ideal_answer: str) -> Tuple[float, str]:
        """Fallback evaluation method if Mistral is not available."""
        student_words = set(student_answer.lower().split())
        ideal_words = set(ideal_answer.lower().split())

        common_words = student_words.intersection(ideal_words)
        if not ideal_words:
            score = 0
        else:
            score = min(10, len(common_words) / len(ideal_words) * 10)

        if score >= 8:
            feedback = "Excellent answer! Shows good understanding of the topic."
        elif score >= 6:
            feedback = "Good answer, but could be more detailed."
        elif score >= 4:
            feedback = "Basic understanding shown, but needs improvement."
        else:
            feedback = "Answer needs significant improvement."

        return score, feedback

    def process_answer_sheet(self, pdf_path: str, answer_key_path: str, output_file: str) -> None:
        """Process an answer sheet PDF and evaluate it against the answer key."""
        # First, extract text from PDF
        temp_text_file = "temp_extracted.txt"
        process_pdf(pdf_path, temp_text_file)

        # Read the extracted text
        with open(temp_text_file, 'r', encoding='utf-8') as f:
            extracted_text = f.read()

        # Extract answers from the text, skipping the first line after each question
        student_answers = self.extract_answers_from_text(extracted_text)

        # Load questions and ideal answers from the answer key
        questions, ideal_answers = self.load_answer_key(answer_key_path)

        results = []
        num_questions = len(questions)
        num_answers = len(student_answers)

        for idx, question in enumerate(questions):
            ideal_answer = ideal_answers[idx] if idx < len(ideal_answers) else ""
            # Map answer by order if available
            if idx < num_answers:
                student_answer = student_answers[idx]
            else:
                student_answer = "No answer provided."

            # Evaluate answer
            try:
                score, feedback = self.get_mistral_feedback(question, student_answer, ideal_answer)
            except Exception:
                score, feedback = self.fallback_evaluate(question, student_answer, ideal_answer)

            results.append({
                "question": question,
                "student_answer": student_answer,
                "ideal_answer": ideal_answer,
                "score": score,
                "feedback": feedback
            })

        # Remove or comment out the old evaluation function call
        # results = evaluate_student_answers(answer_key_path, student_answers)
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Clean up temporary file
        os.remove(temp_text_file)

        print(f"Evaluation complete. Results saved to: {output_file}")

    def load_answer_key(self, answer_key_path):
        """Load questions and ideal answers from a .docx answer key file."""
        import os
        questions = []
        ideal_answers = []
        
        if answer_key_path.lower().endswith('.docx'):
            try:
                from docx import Document
                doc = Document(answer_key_path)
                q = None
                a = []
                print("\nLoading answer key from .docx file:")
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if not text:
                        # Blank line: treat as delimiter between Q&A pairs
                        if q and a:
                            questions.append(q)
                            ideal_answers.append('\n'.join(a).strip())
                            print(f"\nQuestion: {q}")
                            print(f"Answer: {ideal_answers[-1]}")
                            q = None
                            a = []
                        continue
                    if q is None:
                        q = text
                    else:
                        a.append(text)
                # Add last Q&A if present
                if q and a:
                    questions.append(q)
                    ideal_answers.append('\n'.join(a).strip())
                    print(f"\nQuestion: {q}")
                    print(f"Answer: {ideal_answers[-1]}")
                print(f"\nLoaded {len(questions)} questions from docx answer key.")
                return questions, ideal_answers
            except Exception as e:
                print(f"Error loading .docx answer key: {e}")
                return [], []
        else:
            # Fallback to text file logic
            encodings = ['utf-8', 'latin1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(answer_key_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        sections = content.split('\n\n')
                        for section in sections:
                            lines = section.strip().split('\n')
                            if not lines:
                                continue
                            question = lines[0].strip()
                            if not question:
                                continue
                            ideal_answer = '\n'.join(lines[1:]).strip()
                            questions.append(question)
                            ideal_answers.append(ideal_answer)
                        print(f"Successfully loaded answer key using {encoding} encoding")
                        return questions, ideal_answers
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Error loading answer key with {encoding} encoding: {str(e)}")
                    continue
            print("Failed to load answer key with any encoding")
            return [], []

def main():
    if len(sys.argv) < 4:
        print("Usage: python enhanced_evaluator.py <pdf_path> <answer_key_path> <output_file>")
        return

    pdf_path = sys.argv[1]
    answer_key_path = sys.argv[2]
    output_file = sys.argv[3]

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file {pdf_path} does not exist.")
        return

    if not os.path.exists(answer_key_path):
        print(f"Error: Answer key file {answer_key_path} does not exist.")
        return

    evaluator = EnhancedEvaluator()
    evaluator.process_answer_sheet(pdf_path, answer_key_path, output_file)

if __name__ == "__main__":
    main() 