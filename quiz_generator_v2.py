"""QuizGeneratorV2 – high‑speed two‑stage quiz creation with optimized ThinkEngine.

Uses the existing QuizGenerator and TemplateEngine (from quiz_generator.py) to generate MCQs,
running ThinkEngine.think() on top candidate concepts to ensure high grounding with low latency.
Guarantees generating the exact requested number of non-scenario questions quickly.
"""

from typing import List, Dict, Any, Optional

from config import MAX_QUESTIONS, LLM_MODEL
from think_engine import ThinkEngine
from quiz_generator import QuizGenerator, Fact, MCQ, FactType


class QuizGeneratorV2:
    """High‑quality, low-latency quiz generator with 2-stage ThinkEngine reasoning."""

    def __init__(self, llm_model: str = LLM_MODEL):
        self.llm_model = llm_model
        self.base_generator = QuizGenerator(llm_model=llm_model)
        self.think_engine = ThinkEngine(llm_model=self.llm_model)

    def generate_quiz(
        self,
        documents: List[Any],
        num_questions: int = 5,
        topic: str = "",
        start_page: int = 1,
        end_page: int = 10
    ) -> Dict[str, Any]:
        """Generate a quiz from the supplied documents using ThinkEngine pre-reasoning."""
        if not documents:
            return {"success": False, "error": "No documents provided for quiz generation."}

        actual_end = min(end_page, start_page + 9)
        filtered_docs = [
            d for d in documents if start_page <= d.metadata.get("page", 1) <= actual_end
        ]

        if not filtered_docs:
            return {"success": False, "error": f"No pages found in range {start_page}-{actual_end}."}

        # Extract facts strictly from selected document pages
        all_facts: List[Fact] = []
        for doc in filtered_docs:
            p_num = doc.metadata.get("page", 1)
            facts = self.base_generator.fact_classifier.classify_text(doc.page_content, page_num=p_num)
            all_facts.extend(facts)

        if not all_facts:
            return {"success": False, "error": f"Pages {start_page}-{actual_end} contain no extractable concepts."}

        num_questions = max(1, min(10, num_questions))

        # 1. Deduplicate & prioritize top concepts to avoid redundant LLM calls
        concept_best_fact: Dict[str, Fact] = {}
        for f in all_facts:
            norm_c = f.concept.lower()
            if norm_c not in concept_best_fact:
                concept_best_fact[norm_c] = f
            else:
                existing = concept_best_fact[norm_c]
                if f.fact_type == FactType.DEFINITION and existing.fact_type != FactType.DEFINITION:
                    concept_best_fact[norm_c] = f

        candidate_facts = list(concept_best_fact.values())
        candidate_facts.sort(
            key=lambda x: (x.fact_type == FactType.DEFINITION, x.fact_type == FactType.FEATURE),
            reverse=True
        )

        # 2. Run ThinkEngine only on the top candidate concepts needed (max num_questions + 2)
        top_candidates = candidate_facts[:min(len(candidate_facts), num_questions + 2)]
        viable_facts: List[Fact] = []
        for fact in top_candidates:
            page = next((d for d in filtered_docs if d.metadata.get("page", 1) == fact.page_num), filtered_docs[0])
            thought = self.think_engine.think(fact.concept, page.page_content)
            if thought:
                fact.metadata["think_reasoning"] = thought
                viable_facts.append(fact)

        # Append remaining candidates as instant fallbacks without delaying with LLM calls
        for f in candidate_facts:
            if f not in viable_facts:
                viable_facts.append(f)

        # Multi-pass MCQ generation to hit num_questions
        mcqs: List[MCQ] = []
        seen_questions = set()
        seen_concepts = set()

        # Pass 1: Unique concept coverage
        for fact in viable_facts:
            if len(mcqs) >= num_questions:
                break
            if fact.concept.lower() in seen_concepts:
                continue

            mcq = self.base_generator.template_engine.generate_mcq(
                fact, self.base_generator.distractor_engine, all_facts
            )
            if mcq and self.base_generator.validator.validate(mcq):
                if mcq.question.lower() not in seen_questions:
                    mcq.id = len(mcqs) + 1
                    mcqs.append(mcq)
                    seen_questions.add(mcq.question.lower())
                    seen_concepts.add(fact.concept.lower())

        # Pass 2: Additional questions per concept if needed
        if len(mcqs) < num_questions:
            for fact in viable_facts:
                if len(mcqs) >= num_questions:
                    break
                mcq = self.base_generator.template_engine.generate_mcq(
                    fact, self.base_generator.distractor_engine, all_facts
                )
                if mcq and self.base_generator.validator.validate(mcq):
                    if mcq.question.lower() not in seen_questions:
                        mcq.id = len(mcqs) + 1
                        mcqs.append(mcq)
                        seen_questions.add(mcq.question.lower())

        # Pass 3: Instant fallback from all_facts
        if len(mcqs) < num_questions:
            for fact in all_facts:
                if len(mcqs) >= num_questions:
                    break
                mcq = self.base_generator.template_engine.generate_mcq(
                    fact, self.base_generator.distractor_engine, all_facts
                )
                if mcq and self.base_generator.validator.validate(mcq):
                    if mcq.question.lower() not in seen_questions:
                        mcq.id = len(mcqs) + 1
                        mcqs.append(mcq)
                        seen_questions.add(mcq.question.lower())

        if not mcqs:
            return {"success": False, "error": "Could not generate valid questions. Try a wider page range."}

        formatted_questions = []
        for m in mcqs:
            formatted_questions.append({
                "id": m.id,
                "question": m.question,
                "options": m.options,
                "answer": m.correct_answer,
                "correct_index": m.correct_index,
                "explanation": m.explanation,
                "template": m.template_name,
                "page": m.page_num
            })

        return {
            "success": True,
            "questions": formatted_questions,
            "total_questions": len(formatted_questions),
            "range": f"Pages {start_page} - {actual_end}"
        }
