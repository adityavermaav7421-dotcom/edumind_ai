import re
import sys
import io

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from quiz_generator import QuizGenerator, strip_option_prefix, normalize_for_dedup
from langchain_core.documents import Document

def test_fix():
    print("=" * 80)
    print("       VERIFYING FIX FOR OPTION PREFIX LEAK & DUPLICATION")
    print("=" * 80)

    # Java Document text matching user's screenshot (Scanner, BufferedReader, Ternary)
    java_docs = [
        Document(
            page_content="""
            The Scanner class in Java is used to read user input from the keyboard or input streams.
            The BufferedReader class in Java is used to read text from a character-input stream, buffering characters to handle large inputs efficiently.
            The ternary operator in Java is a shorthand conditional operator used to evaluate expressions and assign values.
            The bitwise operator performs operations on individual bits of integer types.
            """,
            metadata={"source": "Unit-1 oops.pdf", "page": 1}
        )
    ]

    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    quiz = quiz_gen.generate_quiz(documents=java_docs, num_questions=5, start_page=1, end_page=1)

    assert quiz["success"] is True, "Quiz generation failed"
    questions = quiz["questions"]

    print(f"\nGenerated {len(questions)} Questions successfully:\n")

    for idx, q in enumerate(questions):
        print(f"Q{q['id']} ({q['type']}): {q['question']}")
        opts = q["options"]
        if isinstance(opts, dict):
            opts_list = list(opts.values())
        else:
            opts_list = list(opts)

        print(f"  Options ({len(opts_list)}): {opts_list}")
        print(f"  Correct Option : {q.get('correct_option')}")
        print(f"  Answer Text    : '{q.get('answer')}'\n" + "-" * 60)

        # Verification 1: NO option string starts with A), B), C), D) or Option A
        for opt in opts_list:
            opt_str = str(opt).strip()
            assert not re.match(r"^[A-D][\):\.]\s*", opt_str, re.IGNORECASE), f"Option prefix leak detected in '{opt_str}'"
            assert not re.match(r"^Option\s*[A-D]", opt_str, re.IGNORECASE), f"Option prefix leak detected in '{opt_str}'"

        # Verification 2: All options are 100% unique after normalization
        norm_opts = [normalize_for_dedup(o) for o in opts_list]
        assert len(norm_opts) == len(set(norm_opts)), f"Duplicate option detected in {opts_list}"

    print("\n✅ VERIFICATION SUCCESSFUL: Zero option prefix leaks, zero duplicate options!")

if __name__ == "__main__":
    test_fix()
