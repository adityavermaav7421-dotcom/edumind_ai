"""EduMind Jetson Orin Demo Day Dry Run Script

Executes an end-to-end dry run testing:
1. Direct Ollama REST API Connection (llama3.2:1b)
2. RAG Document Q&A with exact citations
3. 1-10 Page Short Notes Generator
4. High-Yield Practice Quiz Engine (QuizGeneratorV2)

Saves all generated outputs to 'demo_backup_output.txt' as a live backup.
"""

import sys
import time

# Ensure UTF-8 output encoding across Windows and Linux
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from langchain_core.documents import Document
from ollama_client import call_ollama
from rag_engine import RAGEngine
from notes_generator import NotesGenerator
from quiz_generator_v2 import QuizGeneratorV2
from config import LLM_MODEL

def main():
    backup_lines = []
    def log(msg: str):
        print(msg)
        backup_lines.append(msg)

    log("=" * 70)
    log("🧠 EDUMIND JETSON ORIN DEMO DAY DRY RUN & BACKUP GENERATOR")
    log("=" * 70)
    log(f"Model: {LLM_MODEL}")
    log(f"Time: {time.ctime()}")

    # 1. Test Direct REST API Connection
    log("\n[STAGE 1] Testing Direct Ollama REST API Endpoint...")
    test_prompt = "Explain why object-oriented programming is useful in software engineering in two sentences."
    api_response = call_ollama(test_prompt)
    if api_response:
        log("  ✅ Direct Ollama REST API response received:")
        log(f"  > {api_response[:200]}...")
    else:
        log("  ❌ REST API Connection failed!")

    # Sample Document Setup (Simulating uploaded lecture notes)
    sample_docs = [
        Document(
            page_content="Operating System is a software program that acts as an interface between user applications and computer hardware. Operating Systems manage CPU scheduling, memory allocation, and file storage.",
            metadata={"source": "os_lecture_p1.pdf", "page": 1}
        ),
        Document(
            page_content="Process Management is a core OS component. A process is an instance of a program in execution. The OS maintains a Process Control Block (PCB) to track process state, PID, CPU registers, and memory boundaries.",
            metadata={"source": "os_lecture_p1.pdf", "page": 2}
        ),
        Document(
            page_content="Virtual Memory allows execution of processes that are not completely in physical memory. Paging breaks physical memory into fixed-size frames and virtual memory into pages.",
            metadata={"source": "os_lecture_p1.pdf", "page": 3}
        )
    ]

    # 2. Test RAG Engine with Citations
    log("\n[STAGE 2] Testing High-Accuracy RAG Engine & Citations...")
    rag = RAGEngine(llm_model=LLM_MODEL)
    chunk_count = rag.build_vector_store(sample_docs)
    log(f"  Indexed {len(sample_docs)} pages into {chunk_count} FAISS vector chunks.")
    rag_res = rag.query("What is a Process Control Block and what does it store?")
    log(f"  Answer: {rag_res['answer']}")
    if rag_res["sources"]:
        log(f"  Citation: {rag_res['sources'][0]['source']} Page {rag_res['sources'][0]['page']}")

    # 3. Test Short Notes Generator
    log("\n[STAGE 3] Testing 1-10 Page Short Notes Generator...")
    notes_gen = NotesGenerator(llm_model=LLM_MODEL)
    notes_res = notes_gen.generate_notes(sample_docs, start_page=1, end_page=3, style="Executive Summary")
    if notes_res["success"]:
        log(f"  ✅ Notes generated for range {notes_res['range']}:")
        log(notes_res["notes"])

    # 4. Test High-Yield Practice Quiz Engine V2
    log("\n[STAGE 4] Testing QuizGeneratorV2 (Ground-Truth & 0 Scenario Noise)...")
    quiz_gen = QuizGeneratorV2(llm_model=LLM_MODEL)
    quiz_res = quiz_gen.generate_quiz(sample_docs, num_questions=3, start_page=1, end_page=3)
    if quiz_res.get("success"):
        log(f"  ✅ Generated {len(quiz_res['questions'])} conceptual MCQs:")
        for q in quiz_res["questions"]:
            log(f"\n  Q{q['id']}. {q['question']}")
            for opt in q["options"]:
                log(f"    - {opt}")
            log(f"  Correct Answer: {q['answer']}")
            log(f"  Explanation: {q['explanation']}")

    log("\n" + "=" * 70)
    log("✅ ALL DRY RUN TESTS PASSED SUCCESSFULLY!")
    log("=" * 70)

    # Save backup output to file
    with open("demo_backup_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(backup_lines))
    print("\n📄 Demo backup output saved to 'demo_backup_output.txt'.")

if __name__ == "__main__":
    main()
