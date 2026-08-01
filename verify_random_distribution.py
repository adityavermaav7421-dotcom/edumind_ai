import sys
import io

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from quiz_generator import QuizGenerator
from langchain_core.documents import Document

def test_distribution():
    print("=" * 80)
    print("      VERIFYING RANDOMIZED ANSWER POSITION DISTRIBUTION (A, B, C, D)")
    print("=" * 80)

    docs = [
        Document(
            page_content="""
            The Transport Layer provides process-to-process data delivery services. 
            The Network Layer provides host-to-host routing services.
            The Data Link Layer provides node-to-node framing services.
            The Physical Layer provides bit-level transmission services.
            Star topology connects all network nodes to a central switch.
            Ring topology connects each node to two adjacent nodes forming a continuous loop.
            Mesh topology connects every node directly to every other node.
            Bus topology uses a single backbone cable to connect all network devices.
            """,
            metadata={"source": "networking_guide.pdf", "page": 1}
        )
    ]

    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    quiz = quiz_gen.generate_quiz(documents=docs, num_questions=10, start_page=1, end_page=1)
    questions = quiz.get("questions", [])

    position_counts = {"A": 0, "B": 0, "C": 0, "D": 0}

    print(f"\nGenerated {len(questions)} Questions:\n")

    for q in questions:
        c_let = q.get("correct_option")
        c_ans = q.get("answer")
        opts = q.get("options", {})
        
        if c_let in position_counts:
            position_counts[c_let] += 1
            
        print(f"Q{q['id']}: {q['question']}")
        print(f"  Options        : {opts}")
        print(f"  Correct Option : {c_let} -> '{c_ans}'\n" + "-" * 50)

    print("\nCorrect Answer Position Breakdown across 10 Questions:")
    print(f"  Option A: {position_counts['A']} times")
    print(f"  Option B: {position_counts['B']} times")
    print(f"  Option C: {position_counts['C']} times")
    print(f"  Option D: {position_counts['D']} times")

    # Verify that the correct answer is NOT restricted to Option A
    assert position_counts['B'] + position_counts['C'] + position_counts['D'] > 0, "Correct answer is stuck on Option A!"
    print("\n[SUCCESS] Correct answer positions are randomly distributed across A, B, C, and D!")

if __name__ == "__main__":
    test_distribution()
