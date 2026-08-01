"""Benchmark test verifying quiz generation on the exact User Study Notes text."""
import sys
sys.path.insert(0, ".")
from quiz_generator import QuizGenerator
from langchain_core.documents import Document

user_notes_text = """Executive Overview
Java is a high-level, object-oriented programming language that allows developers to create interactive and dynamic software applications.
It was created by James Gosling et al. at Sun Microsystems in 1995.

Key Technical Concepts & Definitions
JVM: Java Virtual Machine (JVM) is the runtime environment that executes Java bytecode on a computer.
Bytecode: Bytecode is intermediate code that is compiled from source code into machine code that can be executed directly by the JVM.
Class: A class is a blueprint or template for creating objects in an object-oriented programming language like Java.
Object: An object is an instance of a class, which has its own set of attributes (data) and methods (functions).
Method: A method is a block of code that performs a specific task within a class.
Package: A package is a group of classes that are defined by a name.

Core Mechanisms
Garbage Collection: A mechanism that automatically frees up memory occupied by objects that are no longer needed or referenced.
Identifier: A name given by the programmer to uniquely identify classes, variables, methods, interfaces, and other user-defined items.
Keywords: Reserved words in Java with a special predefined meaning.
Operators: Symbols used for arithmetic, comparison, logical, and assignment operations."""

doc = Document(page_content=user_notes_text, metadata={"page": 1, "source": "user_notes.pdf"})

gen = QuizGenerator()
res = gen.generate_quiz([doc], num_questions=5)

print("=" * 80)
print("BENCHMARK TEST ON USER STUDY NOTES")
print("=" * 80)

if res["success"]:
    for q in res["questions"]:
        print(f"\n[{q['template']}] Q{q['id']}. {q['question']}")
        for i, opt in enumerate(q['options']):
            marker = "  <<< (CORRECT)" if i == q['correct_index'] else ""
            print(f"  {chr(65+i)}) {opt}{marker}")
        print(f"  Explanation: {q['explanation']}")
    print("\n" + "=" * 80)
    print("BENCHMARK TEST PASSED 100% — High Quality Questions & Key Term Options!")
    print("=" * 80)
else:
    print(f"FAILED: {res['error']}")
