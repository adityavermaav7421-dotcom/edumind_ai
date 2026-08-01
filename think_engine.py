'''Think Engine – performs a lightweight "think" step before actual MCQ generation.'''

from config import LLM_MODEL
from ollama_client import call_ollama

class ThinkEngine:
    """Generate a concise reasoning snippet for a concept using direct REST API."""

    def __init__(self, llm_model: str = LLM_MODEL):
        self.llm_model = llm_model

    def think(self, concept: str, page_text: str) -> str:
        """Return a "thought" string describing why *concept* is a valid MCQ term.

        Args:
            concept: The extracted concept name.
            page_text: Full text of the source page.
        Returns:
            A short reasoning string (≤ MAX_CHAR_LIMIT).
        """
        prompt = (
            f"You are a quiz‑author assistant. Given the following page excerpt,\n"
            f"identify why the term **{concept}** is an important concept that can\n"
            f"form the basis of a multiple‑choice question. Summarize the reasoning\n"
            f"in up to 600 characters, preserving only factual information from the\n"
            f"text. Do NOT include any answer options or mention the word 'answer'.\n"
            f"\n"
            f"--- Page excerpt (trimmed to 500 chars) ---\n"
            f"{page_text[:500]}...\n"
        )
        response = call_ollama(prompt, model=self.llm_model)
        return response.strip()[:600]
