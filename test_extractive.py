"""Test of QuizGeneratorV2 extractive quiz generation with sample text."""
import sys
sys.path.insert(0, ".")
from langchain_core.documents import Document
from quiz_generator_v2 import QuizGeneratorV2

sample_text = """Object Oriented Programming is a programming paradigm that represents concepts as objects that have data fields and methods. 
Encapsulation is the bundling of data with the methods that operate on that data.
Polymorphism refers to the ability of different objects to respond to the same message in different ways.
Inheritance is a mechanism where a new class derives properties and behavior from an existing class.
A class is defined as a blueprint or template that describes the data and behavior of objects."""

doc = Document(page_content=sample_text, metadata={"page": 1, "source": "test.pdf"})
gen = QuizGeneratorV2()

print("=" * 70)
print("EXTRACTIVE QUIZ V2 TEST")
print("=" * 70)

quiz = gen.generate_quiz([doc], num_questions=3, start_page=1, end_page=1)
if quiz.get("success"):
    print(f"Generated {len(quiz['questions'])} questions for range {quiz['range']}:")
    for q in quiz["questions"]:
        print(f"\nQ{q['id']}. {q['question']}")
        for opt in q["options"]:
            print(f"  - {opt}")
        print(f"Answer: {q['answer']}")
else:
    print(f"Error: {quiz.get('error')}")

print("\n" + "=" * 70)
print("EXTRACTIVE QUIZ V2 TEST COMPLETE")
print("=" * 70)
