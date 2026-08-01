import re
import sys
import io

# Force UTF-8 encoding for stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from quiz_generator import QuizGenerator
from langchain_core.documents import Document

def test_cloze():
    print("=" * 80)
    print("       TESTING REWRITTEN FALLBACK CLOZE GENERATOR")
    print("=" * 80)

    docs = [
        Document(
            page_content="Keyboards and traditional monitors are examples of simplex devices.",
            metadata={"source": "lec1.pdf", "page": 3}
        ),
        Document(
            page_content="In a bus topology, this redundancy is eliminated.",
            metadata={"source": "lec1.pdf", "page": 9}
        ),
        Document(
            page_content="The Transport layer uses port numbers to address target application processes.",
            metadata={"source": "lec1.pdf", "page": 12}
        ),
        Document(
            page_content="Star topology connects all network nodes to a central switch.",
            metadata={"source": "lec1.pdf", "page": 15}
        )
    ]

    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    cloze_qs = quiz_gen._stage7_deterministic_cloze_generator(docs, count=4, vocab_pool=[])

    print(f"\nGenerated {len(cloze_qs)} High-Quality Fallback Cloze Questions:\n")

    for q in cloze_qs:
        print(f"Question Prompt: {q['question']}")
        print(f"Options Dict   : {q['options']}")
        print(f"Correct Option : {q['correct_option']}")
        print(f"Answer Text    : {q['answer']}")
        print(f"Explanation    : {q['explanation']}\n" + "-" * 60)

        # Assertions
        opts_list = list(q['options'].values())
        for opt in opts_list:
            assert opt not in ["redund", "ancy", "tion", "there", "most", "optimally"], f"Invalid word fragment or stop word detected: {opt}"

        assert "_____" in q['question'], "Missing blank in question prompt"
        assert not re.search(r"_____[a-zA-Z]", q['question']), f"Word fragment blank detected: {q['question']}"
        assert not re.search(r"[a-zA-Z]_____", q['question']), f"Word fragment blank detected: {q['question']}"

    print("\n✅ All Cloze Generator Acceptance Criteria PASSED successfully!")

if __name__ == "__main__":
    test_cloze()
