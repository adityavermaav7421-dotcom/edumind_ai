import os
import re
import json
from langchain_core.documents import Document
from quiz_generator import QuizGenerator

def run_debug():
    print("=" * 80)
    print("       CAPTURING LIVE CONSOLE LOGS ([STAGE 1] THROUGH [STAGE 6])")
    print("=" * 80)

    # Real-world networking document sample
    docs = [
        Document(
            page_content="""
            The Transport layer provides process-to-process delivery of data packets. 
            It uses port numbers to address target applications. TCP is a connection-oriented 
            protocol that ensures reliable data transmission with error detection and sequence numbers. 
            UDP is a connectionless transport protocol designed for low-latency transmission.
            Star topology connects all network nodes to a central hub or switch. 
            An advantage of star topology is simplified installation and reconnection. 
            However, if the central hub fails, the entire network goes down.
            """,
            metadata={"source": "networking_guide.pdf", "page": 1, "total_pages": 1}
        )
    ]

    # Initialize QuizGenerator
    quiz_gen = QuizGenerator(llm_model="llama3.2:1b")
    
    # Run Quiz Generation (Triggers STAGE 1, STAGE 2, STAGE 3, STAGE 4)
    quiz_data = quiz_gen.generate_quiz(
        documents=docs,
        num_questions=5,
        start_page=1,
        end_page=1
    )

    # Simulate Streamlit session_state & UI rendering (Triggers STAGE 5 and STAGE 6)
    if quiz_data and quiz_data.get("success"):
        questions = quiz_data.get("questions", [])

        # STAGE 5: IMMEDIATELY AFTER READING FROM SESSION_STATE
        print(f"\n[STAGE 5: IMMEDIATELY AFTER READING FROM SESSION_STATE]")
        for q in questions:
            print(f"  Q{q['id']} Question    : {q['question']}")
            print(f"  Q{q['id']} options     : {q.get('options')}")
            print(f"  Q{q['id']} correct_opt : {q.get('correct_option')} (Index: {q.get('correct_index')})")
            print(f"  Q{q['id']} answer      : {q.get('answer')}")

        # STAGE 6: IMMEDIATELY BEFORE RENDERING RADIO BUTTONS
        for idx, q in enumerate(questions):
            opts_raw = q.get("options", {})
            correct_ans_text = str(q.get("answer", "")).strip()
            opts_list = []
            if isinstance(opts_raw, dict):
                opts_list = [str(v).strip() for v in opts_raw.values()]
            elif isinstance(opts_raw, list):
                opts_list = [str(v).strip() for v in opts_raw]

            display_options = opts_list.copy()

            print(f"\n[STAGE 6: IMMEDIATELY BEFORE RENDERING RADIO BUTTONS]")
            print(f"  Q{q['id']} Question       : {q['question']}")
            print(f"  Q{q['id']} display_options : {display_options}")
            print(f"  Q{q['id']} correct_option  : {q.get('correct_option')} (Index: {q.get('correct_index')})")
            print(f"  Q{q['id']} answer         : '{correct_ans_text}'")

    print("\n" + "=" * 80)
    print("                   TRACE CAPTURE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_debug()
