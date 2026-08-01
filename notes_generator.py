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

STRICT FORMATTING & TABLE RULES:
1. Do NOT mention page numbers (e.g. do NOT include 'Page 1', 'Page 2', etc.). Present content as a unified, seamless study guide.
2. ALWAYS format any comparisons or differences (e.g. POP vs OOP, Java vs C, JDK vs JRE vs JVM) into a clean Markdown Table (`| Aspect / Feature | Option A | Option B |`).
3. Use bold headers for key section titles.

REQUIRED NOTE STRUCTURE:
1. 📌 **Executive Overview**: A 2-3 sentence summary of the core theme.
2. 🔑 **Key Technical Concepts & Definitions**: Clear definitions of all important terms.
3. 📊 **Comparisons & Differences**: Clean Markdown Tables for any comparative topics found in the text.
4. 📝 **Detailed Breakdown & Core Mechanisms**: Clear, structured {style.lower()} explaining how key components/processes work.
5. 💡 **Important Key Takeaways & Exam Tips**: Essential points to remember for exams.

Document Text:
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
        """Rich extractive summary fallback with Markdown table rendering for comparisons and ZERO page numbers."""
        import re
        lines = [f"## 📋 Comprehensive Study Notes\n"]
        lines.append("### 📌 Executive Overview")
        lines.append(f"These study notes synthesize the core concepts, technical mechanisms, and definitions from the selected study material.\n")
        lines.append("### 🔑 Key Concepts & Technical Breakdown")

        seen_lines = set()
        heading_keywords = {"introduction", "features", "advantages", "disadvantages", "applications", "overview", "components", "architecture", "unit", "concept"}
        
        in_table = False
        table_rows = []

        for d in docs:
            content = d.page_content.strip()
            raw_lines = [l.strip() for l in content.split("\n") if l.strip()]
            
            for line in raw_lines:
                clean_raw = line.strip("*: -")
                # Ignore page headers, page numbers, or short junk lines
                if not clean_raw or len(clean_raw) < 3 or re.match(r"^(Page\s*\d+|\[Page\s*\d+\]|===\s*Page)$", clean_raw, re.I) or clean_raw.startswith("==="):
                    continue
                
                if clean_raw.lower() in seen_lines:
                    continue
                seen_lines.add(clean_raw.lower())

                # Check if this line is a comparison title
                if "comparision" in clean_raw.lower() or "comparison" in clean_raw.lower() or " vs " in clean_raw.lower() or "difference between" in clean_raw.lower():
                    lines.append(f"\n### 📊 {clean_raw.rstrip(':')}")
                    lines.append("| Feature / Aspect | Details / Component A | Component B |")
                    lines.append("| :--- | :--- | :--- |")
                    in_table = True
                    continue

                # Detect true major section headings
                is_major_heading = (
                    any(kw in clean_raw.lower() for kw in heading_keywords) 
                    or (clean_raw.isupper() and len(clean_raw) < 40)
                    or (len(clean_raw) < 50 and clean_raw.endswith(":") and len(clean_raw.split()) <= 6)
                )

                if is_major_heading:
                    in_table = False
                    clean_title = clean_raw.rstrip(":")
                    lines.append(f"\n#### 📌 {clean_title}")
                elif ":" in line and not line.lower().startswith("http"):
                    parts = line.split(":", 1)
                    title = parts[0].strip("*: -")
                    body = parts[1].strip()
                    if in_table:
                        lines.append(f"| **{title}** | {body} | Supported / Managed |")
                    elif len(title) < 45:
                        lines.append(f"- **{title}**: {body}")
                    else:
                        lines.append(f"- {line}")
                else:
                    if in_table and len(clean_raw.split()) >= 4:
                        words = clean_raw.split()
                        mid = len(words) // 2
                        col1 = " ".join(words[:mid])
                        col2 = " ".join(words[mid:])
                        lines.append(f"| Aspect | {col1} | {col2} |")
                    else:
                        lines.append(f"- {clean_raw}")

        lines.append("\n### 💡 Important Takeaways & Exam Tips")
        lines.append("- Review all bolded technical terms, comparisons, and core mechanisms above for exam preparation.")
        lines.append("- Ensure clear understanding of key definitions and system architecture components.")
        return "\n".join(lines)
