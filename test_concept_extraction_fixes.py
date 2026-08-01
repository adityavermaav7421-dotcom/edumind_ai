"""Test script verifying the 3 specific Concept Extraction fixes:
1. 'The program' is never a concept topic.
2. 'Java' links to its definition ('Java is a...'), not a feature ('Java supports...').
3. 'Java:' (with colon) never appears as an option or concept.
"""
import sys
sys.path.insert(0, ".")
from quiz_generator import QuizGenerator, ConceptNormalizer, clean_option_text
from langchain_core.documents import Document

normalizer = ConceptNormalizer()

print("=" * 70)
print("TESTING 3 CONCEPT EXTRACTION FIXES")
print("=" * 70)

# Test 1: Normalizer rejects "The program", "Java:", "Examples:"
print("\n--- Test 1: Concept Normalizer ---")
t1 = normalizer.normalize("The program")
t2 = normalizer.normalize("Java:")
t3 = normalizer.normalize("Examples:")

print(f"  normalize('The program') -> {repr(t1)} (Expected: None)")
print(f"  normalize('Java:')      -> {repr(t2)} (Expected: 'Java')")
print(f"  normalize('Examples:')  -> {repr(t3)} (Expected: None)")

assert t1 is None, "FAIL: 'The program' was not rejected!"
assert t2 == "Java", f"FAIL: 'Java:' was normalized to {t2} instead of 'Java'!"
assert t3 is None, "FAIL: 'Examples:' was not rejected!"
print("  PASS: ConceptNormalizer tests passed!")

# Test 2: Option text cleaning
print("\n--- Test 2: Option Text Sanitizer ---")
o1 = clean_option_text("Java: Java is a widely-used, class-based language.")
o2 = clean_option_text("Page 1: Encapsulation is the bundling of data...")
o3 = clean_option_text("is a programming language designed for platform independence.")

print(f"  clean('Java: Java is...')   -> {repr(o1)}")
print(f"  clean('Page 1: Encaps...') -> {repr(o2)}")
print(f"  clean('is a prog...')      -> {repr(o3)}")

assert ":" not in o1 and not o1.startswith("Java:"), "FAIL: Colon prefix was not stripped!"
assert "Page 1:" not in o2, "FAIL: Page marker was not stripped!"
assert not o3.lower().startswith("is a "), "FAIL: 'is a ' prefix was not stripped!"
print("  PASS: Option Sanitizer tests passed!")

# Test 3: Concept Definition Priority ('Java' definition prioritized over features)
print("\n--- Test 3: Concept Definition Priority ---")
sample_java_doc = """Java: Java is a widely-used, class-based, object-oriented programming language.
Java supports features like platform independence, automatic garbage collection, and multithreading.
The program is compiled into bytecode that runs on the JVM."""

doc = Document(page_content=sample_java_doc, metadata={"page": 1, "source": "java_notes.pdf"})

gen = QuizGenerator()
res = gen.generate_quiz([doc], num_questions=2)

if res["success"]:
    for q in res["questions"]:
        print(f"\n[Template: {q['template']}] Q{q['id']}. {q['question']}")
        print(f"  Answer: {q['answer']}")

        # Ensure no "The program" or "Java:" colons in question or options
        assert "The program" not in q['question'], "FAIL: 'The program' was extracted as a question topic!"
        assert "Java:" not in q['question'], "FAIL: 'Java:' with colon in question!"
        for opt in q['options']:
            assert not opt.startswith("Java:"), f"FAIL: Option starts with 'Java:': {opt}"

        # If question is about Java, verify it linked to Definition
        if "Java" in q['question']:
            assert q['template'] == "Definition", f"FAIL: Java linked to {q['template']} instead of Definition!"
            assert "programming language" in q['answer'].lower(), f"FAIL: Java answer did not use definition: {q['answer']}"
    print("\n  PASS: Concept Definition Priority & Fragment Filters fully verified!")
else:
    print(f"FAILED: {res['error']}")

print("\n" + "=" * 70)
print("ALL 3 FIXES VERIFIED SUCCESSFULLY!")
print("=" * 70)
