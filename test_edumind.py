import os
import sys
import re
import json

# Configure UTF-8 stdout encoding for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from rag_engine import RAGEngine
from notes_generator import NotesGenerator
from quiz_generator import QuizGenerator
from quiz_generator_v2 import QuizGeneratorV2
from langchain_core.documents import Document

def run_test():
    print("--- 🧠 EDUMIND Full Architecture Verification Suite ---")

    # Test 1: Enforce 20MB Size Limit
    print("\n1. Testing File Size Limits...")
    rag = RAGEngine(llm_model="llama3.2:1b")
    big_dummy_bytes = b"0" * (21 * 1024 * 1024) # 21 MB
    try:
        rag.process_uploaded_file(big_dummy_bytes, "too_large.pdf", max_size_mb=20.0)
        assert False, "Should have raised ValueError for file size > 20 MB!"
    except ValueError as e:
        print(f"  ✅ 20MB Limit enforced correctly: {e}")

    # Sample Documents (Pages 1 to 4)
    sample_docs = [
        Document(
            page_content="The Transport Layer provides process-to-process data delivery services. It uses port numbers to address target application processes.",
            metadata={"source": "networking_lec1.pdf", "page": 1, "total_pages": 4}
        ),
        Document(
            page_content="Star topology connects all network nodes to a central hub or switch. If the central switch fails, the entire network goes down.",
            metadata={"source": "networking_lec1.pdf", "page": 2, "total_pages": 4}
        ),
        Document(
            page_content="TCP provides connection-oriented, reliable byte stream delivery with error checking and sequence numbers.",
            metadata={"source": "networking_lec1.pdf", "page": 3, "total_pages": 4}
        ),
        Document(
            page_content="UDP is a connectionless, lightweight transport protocol suitable for real-time video streaming and gaming.",
            metadata={"source": "networking_lec1.pdf", "page": 4, "total_pages": 4}
        )
    ]

    # Test 2: RAG Indexing & Querying with Citations
    print("\n2. Testing RAG Engine Vector Store & Querying...")
    chunk_count = rag.build_vector_store(sample_docs)
    print(f"  Indexed {len(sample_docs)} docs into {chunk_count} vector chunks.")
    query_res = rag.query("What protocol provides reliable byte stream delivery?")
    print(f"  RAG Answer Output: {query_res['answer'][:120]}...")
    assert len(query_res["sources"]) > 0, "No sources cited in RAG response!"
    print(f"  ✅ Cited Source: {query_res['sources'][0]['source']} Page {query_res['sources'][0]['page']}")

    # Test 3: Short Notes Generation (1-10 Page Scope)
    print("\n3. Testing 1-10 Page Short Notes Generator...")
    notes_gen = NotesGenerator(llm_model="llama3.2:1b")
    notes_res = notes_gen.generate_notes(sample_docs, start_page=1, end_page=4, style="Bullet Points")
    assert notes_res["success"] is True, "Notes generation failed!"
    print(f"  Generated Notes Range: {notes_res['range']}")
    print(f"  Notes Output Preview:\n{notes_res['notes'][:200]}...")
    print("  ✅ Short notes generated successfully.")

    # Test 4: University Conceptual Practice Quiz Engine V2 (1-10 Page Scope)
    print("\n4. Testing University Conceptual Practice Quiz Engine V2...")
    quiz_gen = QuizGeneratorV2(llm_model="llama3.2:1b")
    quiz_res = quiz_gen.generate_quiz(sample_docs, num_questions=4, start_page=1, end_page=4)
    assert quiz_res["success"] is True, "Quiz generation failed!"
    questions = quiz_res["questions"]
    print(f"  Generated {len(questions)} university conceptual questions.")

    for idx, q in enumerate(questions):
        ans_text = str(q.get("answer", "")).strip()

        print(f"\n  --- Q{q['id']} ---")
        print(f"  Question: {q['question']}")

        opts = q.get("options")
        opts_list = list(opts.values()) if isinstance(opts, dict) else list(opts)
        print(f"  Options ({len(opts_list)}): {opts_list}")
        print(f"  Correct Answer: {ans_text}")
        print(f"  Explanation: {q.get('explanation')}")

        # Verification: Exactly 4 unique options
        assert len(opts_list) == 4, f"Invalid option count {len(opts_list)}"
        lower_opts = [o.lower() for o in opts_list]
        assert len(lower_opts) == len(set(lower_opts)), "Duplicate options detected!"

    print("\n✅ ALL UNIVERSITY CONCEPTUAL ACCEPTANCE TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_test()
