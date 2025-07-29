import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required functions
from admin import (
    exact_match,
    partial_match,
    cosine_similarity_score,
    sentiment_analysis,
    enhanced_sentence_match,
    multinomial_naive_bayes_score,
    semantic_similarity_score,
    coherence_score,
    relevance_score,
    weighted_average_score
)

def evaluate_answer(expected, response):
    """Custom evaluation function that doesn't rely on MySQL"""
    if expected == response:
        return 10
    elif not response:
        return 0

    # Calculate scores
    exact_match_score = exact_match(expected, response)
    partial_match_score = partial_match(expected, response)
    cosine_similarity_score_value = cosine_similarity_score(expected, response)
    sentiment_score = sentiment_analysis(response)
    enhanced_sentence_match_score = enhanced_sentence_match(expected, response)
    multinomial_naive_bayes_score_value = multinomial_naive_bayes_score(expected, response)
    semantic_similarity_value = semantic_similarity_score(expected, response)
    coherence_value = coherence_score(expected, response)
    relevance_value = relevance_score(expected, response)

    scores = [exact_match_score, partial_match_score, cosine_similarity_score_value, sentiment_score,
              enhanced_sentence_match_score, multinomial_naive_bayes_score_value, semantic_similarity_value,
              coherence_value, relevance_value]
    weights = [0.15, 0.1, 0.1, 0.05, 0.1, 0.1, 0.1, 0.1, 0.1]

    scaled_scores = [score * 10 for score in scores]
    final_score = weighted_average_score(scaled_scores, weights)
    rounded_score = round(final_score)

    print("\nDetailed Scores:")
    print("Exact Match Score:", exact_match_score)
    print("Partial Match Score:", partial_match_score)
    print("Cosine Similarity Score:", cosine_similarity_score_value)
    print("Sentiment Score:", sentiment_score)
    print("Enhanced Sentence Match Score:", enhanced_sentence_match_score)
    print("Multinomial Naive Bayes Score:", multinomial_naive_bayes_score_value)
    print("Semantic Similarity Score:", semantic_similarity_value)
    print("Coherence Score:", coherence_value)
    print("Relevance Score:", relevance_value)
    print("\nFinal Score:", rounded_score)

    return rounded_score

# Test cases
print("Running Answer Evaluation Tests...")

# Test case 1: Exact match
expected_answer = "Machine Learning is a branch of artificial intelligence that focuses on developing systems that can learn from and make decisions based on data."
student_answer1 = "Machine Learning is a branch of artificial intelligence that focuses on developing systems that can learn from and make decisions based on data."
print("\nTest Case 1: Exact Match")
print("Expected Answer:", expected_answer)
print("Student Answer:", student_answer1)
score1 = evaluate_answer(expected_answer, student_answer1)

# Test case 2: Similar but not exact
student_answer2 = "Machine Learning is a field of AI that enables computers to learn from data and make decisions. It's a crucial part of modern technology."
print("\nTest Case 2: Similar Answer")
print("Expected Answer:", expected_answer)
print("Student Answer:", student_answer2)
score2 = evaluate_answer(expected_answer, student_answer2)

# Test case 3: Different answer
student_answer3 = "Artificial Intelligence is about making computers think like humans."
print("\nTest Case 3: Different Answer")
print("Expected Answer:", expected_answer)
print("Student Answer:", student_answer3)
score3 = evaluate_answer(expected_answer, student_answer3)

print("\nSummary of Test Results:")
print("Test 1 (Exact Match) Score:", score1)
print("Test 2 (Similar Answer) Score:", score2)
print("Test 3 (Different Answer) Score:", score3) 