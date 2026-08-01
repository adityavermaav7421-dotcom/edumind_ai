from typing import List, Dict, Any
from langchain_core.documents import Document
from config import LLM_MODEL
from ollama_client import call_ollama


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
        """Generates comprehensive, high-quality study notes across selected page ranges using direct REST API."""
        actual_end_page = min(end_page, start_page + 9)
        
        filtered_docs = [
            d for d in documents if start_page <= d.metadata.get("page", 1) <= actual_end_page
        ]

        if not filtered_docs:
            return {
                "success": False,
                "notes": f"No content available between Page {start_page} and Page {actual_end_page}.",
                "pages_included": 0
            }

        page_texts = []
        for doc in filtered_docs:
            page_num = doc.metadata.get("page", "?")
            txt = doc.page_content.strip()
            if txt and not txt.startswith("[Page"):
                page_texts.append(f"=== Page {page_num} ===\n{txt}")

        if not page_texts:
            return {
                "success": False,
                "notes": f"Selected page range ({start_page}-{actual_end_page}) contains no readable text.",
                "pages_included": 0
            }

        full_range_text = "\n\n".join(page_texts)

        if len(full_range_text) > 8000:
            full_range_text = full_range_text[:8000]

        topic_clause = f"Focus specifically on '{custom_topic}'." if custom_topic.strip() else "Cover all primary concepts, definitions, mechanisms, and key facts."

        prompt = f"""You are an Expert Academic Tutor creating high-yield revision study notes for students.
Read the educational document below (Pages {start_page} to {actual_end_page}) and generate detailed, well-structured study notes in {style} style.
{topic_clause}

REQUIRED NOTE STRUCTURE:
1. 📌 **Executive Overview**: A 2-3 sentence summary of the core theme.
2. 🔑 **Key Technical Concepts & Definitions**: Clear definitions of all important terms.
3. 📝 **Detailed Breakdown & Core Mechanisms**: Clear, structured {style.lower()} explaining how key components/processes work.
4. 💡 **Important Key Takeaways & Exam Tips**: Essential points to remember for exams.

Document Text (Pages {start_page} to {actual_end_page}):
{full_range_text}

Comprehensive Study Notes:"""

        try:
            notes = call_ollama(prompt, model=self.llm_model).strip()
        except Exception:
            notes = ""

        # Fallback to rich extractive notes if model response is empty or refused
        if not notes or len(notes) < 80 or "cannot fulfill" in notes.lower() or "can't fulfill" in notes.lower():
            notes = self._generate_extractive_notes(filtered_docs, style, start_page, actual_end_page)

        return {
            "success": True,
            "notes": notes,
            "pages_included": len(filtered_docs),
            "range": f"Pages {start_page} - {actual_end_page}",
            "style": style
        }

    def _generate_extractive_notes(self, docs: List[Document], style: str, start_p: int, end_p: int) -> str:
        """Rich extractive summary fallback preserving original section headings and concept names."""
        lines = [f"## 📋 Comprehensive Study Notes (Pages {start_p}-{end_p})\n"]
        lines.append("### 📌 Executive Overview")
        lines.append(f"These study notes cover core concepts, technical mechanisms, and definitions extracted from Pages {start_p} to {end_p}.\n")
        lines.append("### 🔑 Key Concepts & Page Breakdown")

        for d in docs:
            p_num = d.metadata.get("page", "?")
            lines.append(f"\n#### Page {p_num}")
            
            content = d.page_content.strip()
            raw_lines = [l.strip() for l in content.split("\n") if l.strip()]
            
            for line in raw_lines:
                if len(line) < 3:
                    continue
                
                # Format headings or key-value definitions cleanly
                if len(line) < 65 and not line.endswith(".") and (":" not in line or line.count(" ") < 6):
                    lines.append(f"\n**📌 {line}**")
                elif ":" in line:
                    parts = line.split(":", 1)
                    title = parts[0].strip()
                    body = parts[1].strip()
                    if len(title) < 50 and not title.lower().startswith("http"):
                        lines.append(f"- **{title}**: {body}")
                    else:
                        lines.append(f"- {line}")
                else:
                    lines.append(f"- {line}")

        lines.append("\n### 💡 Important Takeaways")
        lines.append("- Review all bolded technical terms, comparisons, and definitions above for exam preparation.")
        return "\n".join(lines)
