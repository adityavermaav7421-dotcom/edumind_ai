"""Test the QuizGenerator MCQ validation and concept normalization."""
import sys
sys.path.insert(0, ".")
from quiz_generator import MCQValidator, ConceptNormalizer, MCQ

validator = MCQValidator()

print("=== TEST 1: Valid MCQ ===")
mcq1 = MCQ(
    id=1,
    question="What is Encapsulation?",
    options=["Data bundling", "Code inheritance", "Type casting", "Memory allocation"],
    correct_answer="Data bundling",
    correct_index=0,
    explanation="Encapsulation bundles data.",
    template_name="Definition",
    page_num=1
)
if validator.validate(mcq1):
    print("  PASS - Valid MCQ passed validation")
else:
    print("  FAIL - Valid MCQ failed validation")

print("\n=== TEST 2: Duplicate Options ===")
mcq2 = MCQ(
    id=2,
    question="What is Encapsulation?",
    options=["Data bundling", "Data bundling", "Type casting", "Memory allocation"],
    correct_answer="Data bundling",
    correct_index=0,
    explanation="Duplicate options.",
    template_name="Definition",
    page_num=1
)
if not validator.validate(mcq2):
    print("  PASS - Duplicate options correctly rejected")
else:
    print("  FAIL - Duplicate options passed validation")

print("\n=== TEST 3: Blocked word concept normalization ===")
blocked = ConceptNormalizer.is_blocked_word("definition")
if blocked:
    print("  PASS - 'definition' correctly identified as blocked word")
else:
    print("  FAIL - 'definition' not blocked")

print("\n=== ALL TESTS COMPLETE ===")
