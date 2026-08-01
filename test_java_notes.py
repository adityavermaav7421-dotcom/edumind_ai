"""Verification script for Java Notes page 10-20 concepts (This, Using, Identifier, Literals, Types)."""
import sys
sys.path.insert(0, ".")
from quiz_generator import QuizGenerator
from langchain_core.documents import Document

java_notes = """An Identifier in Java is a name given by the programmer to uniquely identify classes, variables, methods, interfaces, and other user-defined items.
Literals are constant values assigned to variables or used in expressions in Java programs.
Types of Comments in Java: Java provides three types of comments including single-line, multi-line, and documentation comments. Comments are beneficial for programmers to understand code.
That is, if you want to declare many classes within one element, then you can declare it within a package. This is useful for organization.
Using BufferedReader and InputStreamReader or Using Scanner class: The Scanner class is part of java.util package used for reading input."""

doc = Document(page_content=java_notes, metadata={"page": 12, "source": "java_chapter2.pdf"})

gen = QuizGenerator()
res = gen.generate_quiz([doc], num_questions=5, start_page=12, end_page=20)

print("=" * 75)
print("JAVA NOTES EXTRACTION VERIFICATION TEST")
print("=" * 75)

if res["success"]:
    for q in res["questions"]:
        print(f"\n[Template: {q['template']}] Q{q['id']}. {q['question']}")
        print(f"  A) {q['options'][0]}")
        print(f"  B) {q['options'][1]}")
        print(f"  C) {q['options'][2]}")
        print(f"  D) {q['options'][3]}")
        print(f"  → Correct Answer: {q['answer']}")

        # Ensure "This", "Using", "Types" are NEVER extracted as standalone concept topics!
        q_words = q['question'].split()
        assert "This?" not in q['question'], f"FAIL: 'This' was extracted as concept in: {q['question']}"
        assert "Using?" not in q['question'], f"FAIL: 'Using' was extracted as concept in: {q['question']}"
        assert "Types?" not in q['question'], f"FAIL: 'Types' was extracted as concept in: {q['question']}"
        assert "```" not in q['answer'], f"FAIL: Raw backticks in answer: {q['answer']}"
        assert "\n" not in q['answer'], f"FAIL: Raw newlines in answer: {q['answer']}"

    print("\n" + "=" * 75)
    print("ALL JAVA NOTES TESTS PASSED PERFECTLY — Zero Vague Concepts!")
    print("=" * 75)
else:
    print(f"FAILED: {res['error']}")
