import os
import json
import random
from rag_engine import RAGEngine
from quiz_generator import QuizGenerator, clean_question_text
from langchain_core.documents import Document

def trace_lifecycle():
    print("=" * 80)
    print("      LIFECYCLE TRACE OF OPTIONS OBJECT")
    print("=" * 80)

    sample_docs = [
        Document(
            page_content="Mesh topology connects every node directly to every other node using dedicated point-to-point links.",
            metadata={"source": "networking_lec1.pdf", "page": 1, "total_pages": 4}
        ),
        Document(
            page_content="Ring topology connects each node to two adjacent nodes forming a single continuous pathway for signals.",
            metadata={"source": "networking_lec1.pdf", "page": 2, "total_pages": 4}
        ),
        Document(
            page_content="Star topology connects all network nodes to a central hub or switch.",
            metadata={"source": "networking_lec1.pdf", "page": 3, "total_pages": 4}
        ),
        Document(
            page_content="Bus topology uses a single backbone cable to connect all network devices.",
            metadata={"source": "networking_lec1.pdf", "page": 4, "total_pages": 4}
        )
    ]

    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    
    print("\n--- [STAGE 1: GENERATION & PARSING] ---")
    res = quiz_gen.generate_quiz(
        documents=sample_docs,
        num_questions=4,
        start_page=1,
        end_page=4
    )

    print("\n--- [STAGE 2: QUIZ OBJECT RETURN CONTRACT] ---")
    questions = res.get("questions", [])
    for q in questions:
        print(f"\nQuestion ID {q.get('id')}: {q.get('question')}")
        print(f"  Type          : {q.get('type')}")
        print(f"  Stored Options: {q.get('options')}")
        print(f"  Correct Option: {q.get('correct_option')}")
        print(f"  Correct Index : {q.get('correct_index')}")
        print(f"  Answer Text   : {q.get('answer')}")

    print("\n--- [STAGE 3: SIMULATING STREAMLIT session_state STORAGE & UI RENDERING] ---")
    session_state_quiz = json.loads(json.dumps(res))  # Deep copy to simulate session state serialization
    
    for q in session_state_quiz.get("questions", []):
        opts_raw = q.get("options", {})
        if isinstance(opts_raw, dict):
            opts_list = [str(v).strip() for v in opts_raw.values()]
        else:
            opts_list = [str(v).strip() for v in opts_raw]

        display_options = opts_list.copy()

        print(f"\nUI Rendering for Question ID {q.get('id')}: {q.get('question')}")
        print(f"  display_options passed to st.radio: {display_options}")
        print(f"  Check Option A (index 0)           : '{display_options[0]}'")
        print(f"  Check Answer Text                  : '{q.get('answer')}'")
        print(f"  Does Option A match Answer Text?   : {display_options[0] == q.get('answer')}")
        
        # Verify 4 distinct options
        lower_opts = [o.lower() for o in display_options]
        is_unique = (len(lower_opts) == len(set(lower_opts)))
        print(f"  Are all 4 display options UNIQUE?  : {is_unique}")
        assert is_unique, f"BUG DETECTED! Option A was overwritten! {display_options}"

    print("\n" + "=" * 80)
    print("SUCCESS: Zero option replacement bug detected across the full lifecycle!")
    print("=" * 80)

if __name__ == "__main__":
    trace_lifecycle()
