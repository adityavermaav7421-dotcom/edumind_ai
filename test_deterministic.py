"""Test the 100% deterministic extractive quiz generator."""
import sys
sys.path.insert(0, ".")
from quiz_generator import QuizGenerator
from langchain_core.documents import Document

# Build fake documents simulating pages from an OOPs PDF
pages = {
    1: "Object Oriented Programming is a programming paradigm that represents concepts as objects that have data fields and methods. OOP provides modularity for large applications. The key advantage of OOP is code reusability through inheritance.",
    2: "Encapsulation is the bundling of data with the methods that operate on that data, restricting direct access to some of an object's components. Encapsulation helps in data hiding and provides security to the internal state of objects.",
    3: "Polymorphism refers to the ability of different objects to respond to the same message in different ways. There are two types of polymorphism: compile-time polymorphism and runtime polymorphism. Method overloading is an example of compile-time polymorphism.",
    4: "Inheritance is a mechanism where a new class derives properties and behavior from an existing class. The class being inherited from is called the parent class or superclass. The class that inherits is called the child class or subclass.",
    5: "Java is a widely used object-oriented programming language. Java supports features like platform independence, automatic garbage collection, and strong type checking. The JDK provides tools for Java development including the compiler, debugger, and documentation generator.",
}

docs = []
for pg, text in pages.items():
    docs.append(Document(page_content=text, metadata={"page": pg, "source": "Unit-1 oops.pdf"}))

gen = QuizGenerator()
result = gen.generate_quiz(docs, num_questions=5, start_page=1, end_page=5)

print("=" * 70)
print("DETERMINISTIC QUIZ TEST — NO LLM CALLS")
print("=" * 70)

if result["success"]:
    for q in result["questions"]:
        print(f"\nQ{q['id']}. {q['question']}")
        for i, opt in enumerate(q["options"]):
            marker = "  <<<" if i == q["correct_index"] else ""
            print(f"  {chr(65+i)}) {opt}{marker}")
        print(f"  → Answer: {q['answer']}")
        print(f"  → Explanation: {q['explanation']}")
else:
    print(f"FAILED: {result['error']}")

print("\n" + "=" * 70)
print("DONE — Zero LLM calls made!")
print("=" * 70)
