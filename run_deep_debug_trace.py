import sys
import io

# Force UTF-8 stdout wrapper
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from quiz_generator import QuizGenerator
from langchain_core.documents import Document

def run_trace():
    print("=" * 80)
    print("       RUNNING DEEP DEBUG TRACE HARNESS")
    print("=" * 80)

    docs = [
        Document(
            page_content="""
            The Scanner class in Java is used to read user input from the keyboard.
            The BufferedReader class in Java is used to read text from a character-input stream, buffering characters to handle large inputs efficiently.
            The ternary operator in Java is a shorthand conditional operator used to evaluate expressions and assign values.
            Object-Oriented Programming (OOP) in Java organizes code around objects rather than functions.
            """,
            metadata={"source": "Unit-1 oops.pdf", "page": 1}
        )
    ]

    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    quiz = quiz_gen.generate_quiz(documents=docs, num_questions=4, start_page=1, end_page=1)

    print("\nFINAL QUIZ RESULT GENERATED:")
    for idx, q in enumerate(quiz.get("questions", [])):
        print(f"\nQ{q['id']} ({q['type']}): {q['question']}")
        print(f"  Options Dictionary : {q.get('options')}")
        print(f"  Correct Option     : {q.get('correct_option')}")
        print(f"  Answer             : '{q.get('answer')}'")

if __name__ == "__main__":
    run_trace()
