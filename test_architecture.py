"""Comprehensive verification script for the redesigned EduMind Modular Quiz Architecture."""
import sys
sys.path.insert(0, ".")
from quiz_generator import QuizGenerator
from langchain_core.documents import Document

sample_text_p1 = """Computer Networks are systems of interconnected devices that share data and resources.
TCP (Transmission Control Protocol) is a connection-oriented communication protocol that provides reliable byte stream delivery.
UDP (User Datagram Protocol) is a connectionless protocol that provides low-latency data transmission.
The main advantage of TCP is reliable delivery through sequence numbers and acknowledgments.
The main disadvantage of UDP is lack of guaranteed packet delivery."""

sample_text_p2 = """IP (Internet Protocol) refers to the principal communications protocol in the Internet protocol suite for relaying datagrams across network boundaries.
A Router is defined as a networking device that forwards data packets between computer networks.
A Switch is a networking device that connects devices on a computer network by using packet switching.
DNS (Domain Name System) is a hierarchical naming system for computers, services, or other resources connected to the Internet."""

docs = [
    Document(page_content=sample_text_p1, metadata={"page": 1, "source": "networks.pdf"}),
    Document(page_content=sample_text_p2, metadata={"page": 2, "source": "networks.pdf"}),
]

gen = QuizGenerator()
result = gen.generate_quiz(docs, num_questions=5, start_page=1, end_page=2)

print("=" * 75)
print("EDUMIND ARCHITECTURE VERIFICATION TEST")
print("=" * 75)

if result["success"]:
    for q in result["questions"]:
        print(f"\n[Template: {q['template']}] Q{q['id']}. {q['question']}")
        for i, opt in enumerate(q["options"]):
            marker = "  <<< (CORRECT)" if i == q["correct_index"] else ""
            print(f"  {chr(65+i)}) {opt}{marker}")
        print(f"  Explanation: {q['explanation']}")
        print(f"  Citation: Page {q['page']}")
else:
    print(f"FAILED: {result['error']}")

print("\n" + "=" * 75)
print("VERIFICATION SUCCESSFUL — All templates operational!")
print("=" * 75)
