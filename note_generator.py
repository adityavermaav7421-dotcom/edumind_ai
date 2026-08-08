import re
from typing import List, Dict, Any
from langchain_core.documents import Document
from config import LLM_MODEL
from ollama_client import call_ollama


def clean_page_text(text: str) -> str:
    """Fixes broken font encodings (e.g., 'c ntr l' -> 'control') and strips bullet artifacts."""
    if not text:
        return ""
    # Repair missing single-letter space gaps (e.g., "c ntr l" -> "control", "o ject" -> "object")
    cleaned = re.sub(r'(?<=\b[a-zA-Z])\s+(?=[a-zA-Z]\b)', '', text)
    # Normalize multiple whitespace characters
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    # Strip bullet artifacts like weird Unicode symbols or raw bullet boxes
    cleaned = re.sub(r'^[•▪\-*\s]+', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()


class NotesGenerator:
    def __init__(self, llm_model: str = LLM_MODEL):
        self.llm_model = llm_model

    def generate_notes(
        self,
        documents: List[Document],
        start_page: int,
        end_page: int,
        style: str = "Bullet Points",
        custom_topic: str = ""
    ) -> Dict[str, Any]:
        """Generates high-yield, user-friendly academic study notes covering all headings across Pages 1-10."""
        actual_end_page = min(end_page, start_page + 9)
        
        filtered_docs = [
            d for d in documents if start_page <= d.metadata.get("page", 1) <= actual_end_page
        ]

        if not filtered_docs:
            return {
                "success": False,
                "notes": f"No content available between Page {start_page} and Page {actual_end_page}.",
                "pages_included": 0,
                "style": style
            }

        # Build clean pagewise text blocks
        page_blocks = []
        valid_pages = []
        for doc in filtered_docs:
            page_num = doc.metadata.get("page", "?")
            raw_text = doc.page_content.strip()
            if not raw_text or raw_text.startswith("[Page"):
                continue
            cleaned = clean_page_text(raw_text)
            if cleaned:
                page_blocks.append(f"=== [Page {page_num}] ===\n{cleaned}")
                valid_pages.append((page_num, cleaned))

        if not page_blocks:
            return {
                "success": False,
                "notes": f"Selected page range ({start_page}-{actual_end_page}) contains no readable text.",
                "pages_included": 0,
                "style": style
            }

        full_text = "\n\n".join(page_blocks)
        if len(full_text) > 10000:
            full_text = full_text[:10000]

        topic_clause = f"\nFocus specifically on '{custom_topic}'." if custom_topic.strip() else ""

        # Single-pass elegant academic prompt with increased word limit budget
        prompt = f"""You are a Master Academic Tutor creating a comprehensive study guide for Pages {start_page} to {actual_end_page}.{topic_clause}

CRITICAL USER-FRIENDLY INSTRUCTIONS:
1. FULL PAGE COVERAGE: Extract and explain the important headings, key concepts, and technical definitions from EVERY single page in the range (Pages {start_page} to {actual_end_page}).
2. INCREASED WORD BUDGET: Provide a rich, detailed study guide of approximately 1000 to 1200 words in {style} style.
3. SEAMLESS FORMATTING: Present notes as a unified, professional study guide with clear section titles (`### 📌 Section Title`). Do NOT use raw dividers like "Notes for Page X".
4. MANDATORY COMPARISON TABLES: Format any comparative topics as clean Markdown Tables (`| Feature / Aspect | Option A | Option B |`).
5. NO OUTSIDE HALLUCINATIONS: Use ONLY the provided document text.

Document Text (Pages {start_page} to {actual_end_page}):
{full_text}

Comprehensive Study Guide:"""

        try:
            notes = call_ollama(prompt, model=self.llm_model).strip()
        except Exception:
            notes = ""

        # Rich extractive fallback if LLM returns empty or refusal
        if not notes or len(notes) < 120 or "can't fulfill" in notes.lower() or "cannot fulfill" in notes.lower():
            notes = self._generate_extractive_fallback(valid_pages, start_page, actual_end_page)

        return {
            "success": True,
            "range": f"Pages {start_page} - {actual_end_page}",
            "notes": notes,
            "pages_included": len(filtered_docs),
            "style": style
        }

    def _generate_extractive_fallback(self, valid_pages: List[tuple], start_p: int, end_p: int) -> str:
        """User-friendly extractive fallback extracting headings & bullet points across all pages."""
        lines = [f"## 📋 Comprehensive Study Guide (Pages {start_p}-{end_p})\n"]
        lines.append("### 📌 Executive Overview")
        lines.append("Synthesized high-yield study material extracted from all pages in the selected range.\n")
        lines.append("### 🔑 Key Concepts & Technical Breakdown")

        for p_num, text in valid_pages:
            sents = [s.strip() for s in text.split(".") if len(s.strip().split()) >= 5]
            if sents:
                lines.append(f"\n#### 📌 Key Topics (Page {p_num})")
                for s in sents[:3]:
                    lines.append(f"- **Concept**: {s}.")

        lines.append("\n### 💡 Exam Takeaways")
        lines.append("- Review all technical terms, definitions, and mechanisms above for revision.")
        return "\n".join(lines)
