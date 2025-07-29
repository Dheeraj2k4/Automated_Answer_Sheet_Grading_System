from docx import Document
import requests
import re
from typing import Dict, List, Tuple

def load_answer_key(docx_path: str) -> Dict[str, str]:
    doc = Document(docx_path)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    qa_pairs = re.findall(r"Q\d+\.\s*(.*?)\nA\d+\.\s*(.*?)(?=\nQ\d+\.|\Z)", full_text, re.DOTALL)
    return {q.strip(): a.strip() for q, a in qa_pairs}

def grade_answer(question: str, student_answer: str, ideal_answer: str) -> Tuple[float, str]:
    # Simple keyword matching for initial testing
    student_words = set(student_answer.lower().split())
    ideal_words = set(ideal_answer.lower().split())
    
    # Calculate word overlap
    common_words = student_words.intersection(ideal_words)
    if not ideal_words:
        score = 0
    else:
        score = min(10, len(common_words) / len(ideal_words) * 10)
    
    # Generate simple feedback
    if score >= 8:
        feedback = "Excellent answer! Shows good understanding of the topic."
    elif score >= 6:
        feedback = "Good answer, but could be more detailed."
    elif score >= 4:
        feedback = "Basic understanding shown, but needs improvement."
    else:
        feedback = "Answer needs significant improvement."
    
    return score, feedback

def evaluate_student_answers(answer_key_path: str, student_answers: Dict[str, str]) -> List[Dict]:
    """
    Evaluate a set of student answers against an answer key.
    
    Args:
        answer_key_path: Path to the answer key docx file
        student_answers: Dictionary mapping questions to student answers
        
    Returns:
        List of dictionaries containing question, student answer, score, and feedback
    """
    answer_key = load_answer_key(answer_key_path)
    results = []
    
    for question, ideal_answer in answer_key.items():
        student_answer = student_answers.get(question, "No answer provided.")
        score, feedback = grade_answer(question, student_answer, ideal_answer)
        
        results.append({
            "question": question,
            "student_answer": student_answer,
            "ideal_answer": ideal_answer,
            "score": score,
            "feedback": feedback
        })
    
    return results

if __name__ == "__main__":
    # Example usage
    answer_key = load_answer_key("answer_key.docx")
    
    # Dummy student answers
    dummy_answers = {
        "What are the causes of global warming?": "Global warming happens because of pollution and cutting trees.",
        "Define Newton's Second Law.": "Force equals mass times acceleration."
    }
    
    results = evaluate_student_answers("answer_key.docx", dummy_answers)
    
    for result in results:
        print(f"\nQuestion: {result['question']}")
        print(f"Student Answer: {result['student_answer']}")
        print(f"Score: {result['score']}")
        print(f"Feedback: {result['feedback']}")
