import os
import re
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from langchain_core.documents import Document
from config import LLM_MODEL
from ollama_client import call_ollama


# ── 1. Data Schemas & Fact Types ──────────────────────────────────────────

class FactType(str, Enum):
    DEFINITION = "DEFINITION"
    FEATURE = "FEATURE"
    ADVANTAGE = "ADVANTAGE"
    DISADVANTAGE = "DISADVANTAGE"
    ABBREVIATION = "ABBREVIATION"
    GENERAL_FACT = "GENERAL_FACT"
    TYPE_IDENTIFICATION = "TYPE_IDENTIFICATION"


@dataclass
class Fact:
    raw_text: str
    fact_type: FactType
    concept: str
    details: str
    page_num: int
    metadata: Dict[str, Any]


@dataclass
class MCQ:
    id: int
    question: str
    options: List[str]
    correct_answer: str
    correct_index: int
    explanation: str
    template_name: str
    page_num: int


# ── 2. Text Preprocessing & Concept Normalization ────────────────────────────

class DocumentCleaner:
    """Strips OCR artifacts, bullet points, headers/footers, and page noise."""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        t = re.sub(r'^\s*(?:\d+[\.\)]|[-•●▪*])\s*', '', t, flags=re.MULTILINE)
        t = re.sub(r'\[Page\s+\d+\]', '', t, flags=re.IGNORECASE)
        t = re.sub(r'Page\s+\d+\s+of\s+\d+', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\n{3,}', '\n\n', t)
        t = re.sub(r'[ \t]+', ' ', t)
        return t.strip()


class ConceptNormalizer:
    """Filters generic terms, layout headings, question words, and prepositions."""

    TRANSITION_PHRASES: Set[str] = {
        "for this reason", "in addition", "therefore", "however", "thus",
        "for example", "as a result", "on the other hand", "furthermore",
        "in other words", "in conclusion", "consequently", "nevertheless",
        "for instance", "as mentioned", "as discussed", "note that", "it is important"
    }

    SECTION_HEADINGS: Set[str] = {
        "executive overview", "detailed breakdown", "core mechanisms",
        "key technical concepts & definitions", "structure of a java program",
        "variables", "scope of variables", "comprehensive study notes",
        "performance overhead", "gui limitations", "initialization",
        "compilation", "execution", "summary", "overview", "introduction",
        "background", "conclusion", "table of contents", "key technical concepts",
        "unit 1 introduction", "unit 1", "chapter 1", "chapter 2", "unit 2",
        "definition", "definitions", "description", "meaning", "explanation", "structure", "elements"
    }

    GENERIC_CONCEPTS: Set[str] = {
        "this", "that", "these", "those", "using", "types", "type", "part", "parts",
        "way", "ways", "use", "uses", "value", "values", "item", "items", "section",
        "sections", "comment", "comments", "program", "the program", "system",
        "the system", "code", "the code", "file", "the file", "method", "the method",
        "data", "the data", "object", "an object", "class", "a class", "page",
        "figure", "table", "example", "examples", "well", "unlike", "note",
        "introduction", "java:", "features", "advantages", "disadvantages",
        "concept", "concepts", "topic", "syntax", "example:", "notes", "input",
        "supports", "includes", "provides", "allows", "enables", "contains",
        "requires", "copy", "automatic", "manual", "static", "dynamic", "general",
        "limitations", "overview", "breakdown", "platform", "unit", "what", "why",
        "how", "when", "where", "who", "which", "goals", "operating system goals",
        "many", "the", "primary", "of", "some", "all", "any", "each", "other",
        "a", "an", "in", "on", "at", "by", "for", "with", "from", "as", "to", "or", "and",
        "definition", "definitions", "description", "meaning", "explanation"
    }

    VERB_INITIAL_WORDS: Set[str] = {
        "helps", "follows", "difficult", "allows", "provides", "supports",
        "includes", "contains", "requires", "executes", "creates", "defines",
        "implements", "reduces", "improves", "manages", "handles", "converts",
        "unit", "chapter", "section", "module", "part", "table", "figure",
        "page", "header", "footer", "topic", "platform", "helps in self",
        "what", "why", "how", "when", "where", "who", "which", "many", "the",
        "primary", "of", "some", "all", "any", "each", "other"
    }

    @classmethod
    def is_blocked_word(cls, term: str) -> bool:
        if not term:
            return True
        norm = term.strip().lower()
        words = norm.split()
        if not words:
            return True
        if words[0] in cls.VERB_INITIAL_WORDS or words[0] in cls.GENERIC_CONCEPTS:
            return True
        if words[-1] in {"of", "the", "a", "an", "in", "on", "at", "by", "for", "with", "from", "as", "to", "or", "and"}:
            return True
        if norm in cls.SECTION_HEADINGS or norm in cls.TRANSITION_PHRASES or norm in cls.GENERIC_CONCEPTS:
            return True
        return False

    def normalize(self, term: str) -> Optional[str]:
        if not term or self.is_blocked_word(term):
            return None

        cleaned = re.sub(r'^\s*(?:\d+[\.\)]|[-•●*])\s*', '', term).strip()
        cleaned = re.sub(r'[:\-;]\s*$', '', cleaned).strip()

        cleaned = re.sub(
            r'^(?:The\s+term\s+|This\s+term\s+|The\s+|A\s+|An\s+|This\s+|That\s+|These\s+|Those\s+)',
            '',
            cleaned,
            flags=re.IGNORECASE
        ).strip()

        if len(cleaned) < 3 or len(cleaned.split()) > 4:
            return None

        return cleaned[0].upper() + cleaned[1:]


def clean_option_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'^\s*(?:that|which|is|are|refers to|defined as)\s+', '', t, flags=re.IGNORECASE)
    return t.strip()


# ── 3. Knowledge Extraction & Fact Classifier ────────────────────────────────

class KnowledgeBuilder:
    def __init__(self, normalizer: ConceptNormalizer):
        self.normalizer = normalizer

    def build_sentences(self, text: str) -> List[str]:
        clean = DocumentCleaner.clean_text(text)
        raw_sentences = re.split(r'(?<=[.!?])\s+', clean)
        results = []
        for s in raw_sentences:
            s_clean = s.strip()
            if 25 <= len(s_clean) <= 600:
                results.append(s_clean)
        return results


class FactClassifier:
    def __init__(self, normalizer: ConceptNormalizer):
        self.normalizer = normalizer

    def classify_text(self, text: str, page_num: int = 1) -> List[Fact]:
        facts: List[Fact] = []
        builder = KnowledgeBuilder(self.normalizer)
        sentences = builder.build_sentences(text)

        concept_counts: Dict[str, int] = {}
        for s in sentences:
            words = re.findall(r'\b[A-Z][a-zA-Z0-9_-]{2,}\b', s)
            for w in words:
                concept_counts[w.lower()] = concept_counts.get(w.lower(), 0) + 1

        for sentence in sentences:
            if len(sentence) < 25 or len(sentence) > 600:
                continue

            if re.match(r'^(?:Unlike|For this reason|As a result|In addition|For example|However|Therefore)\b', sentence, re.IGNORECASE):
                continue

            # A. Abbreviation Extraction
            abbr_match = re.search(r'\b([A-Z]{2,10})\s*\(([^)]+)\)', sentence)
            if abbr_match:
                short_form = abbr_match.group(1)
                full_form = abbr_match.group(2)
                if not ConceptNormalizer.is_blocked_word(short_form):
                    salience = 5.0 + concept_counts.get(short_form.lower(), 1)
                    facts.append(Fact(
                        raw_text=sentence,
                        fact_type=FactType.ABBREVIATION,
                        concept=short_form,
                        details=full_form,
                        page_num=page_num,
                        metadata={"salience_score": salience}
                    ))
                    continue

            # B. Definition Extraction
            is_action_verb = bool(re.search(r'\b(?:provides|allows|enables|supports|includes|contains|uses|executes|improves|reduces)\b', sentence, re.IGNORECASE))
            if not is_action_verb:
                def_patterns = [
                    r'^\s*([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s*:\s*([^.]{15,500})\.?',
                    r'^\s*([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s*[-–—]\s*([^.]{15,500})\.?',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s+is\s+((?:the|a|an)\s+[^.]{15,400})\.',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)\s+refers\s+to\s+([^.]{15,400})\.',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)\s+is\s+defined\s+as\s+([^.]{15,400})\.'
                ]
                found_def = False
                for pattern in def_patterns:
                    match = re.search(pattern, sentence)
                    if match:
                        raw_concept = match.group(1).strip()
                        raw_details = match.group(2).strip()
                        norm_concept = self.normalizer.normalize(raw_concept)
                        if norm_concept and not ConceptNormalizer.is_blocked_word(norm_concept):
                            salience = 4.0 + concept_counts.get(norm_concept.lower(), 1)
                            facts.append(Fact(
                                raw_text=sentence,
                                fact_type=FactType.DEFINITION,
                                concept=norm_concept,
                                details=raw_details,
                                page_num=page_num,
                                metadata={"salience_score": salience}
                            ))
                            found_def = True
                            break
                if found_def:
                    continue

            # C. Advantage / Feature Extraction
            concept_match = re.search(r'\b([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2})\b', sentence)
            if concept_match:
                concept_name = self.normalizer.normalize(concept_match.group(1))
                if concept_name and not ConceptNormalizer.is_blocked_word(concept_name):
                    ftype = FactType.FEATURE
                    if any(w in sentence.lower() for w in ["advantage", "benefit", "reduces", "improves", "faster", "efficient"]):
                        ftype = FactType.ADVANTAGE
                    elif any(w in sentence.lower() for w in ["limitation", "disadvantage", "drawback", "slower", "overhead"]):
                        ftype = FactType.DISADVANTAGE

                    salience = 2.0 + concept_counts.get(concept_name.lower(), 1)
                    facts.append(Fact(
                        raw_text=sentence,
                        fact_type=ftype,
                        concept=concept_name,
                        details=sentence,
                        page_num=page_num,
                        metadata={"salience_score": salience}
                    ))

        return facts


# ── 4. DistractorEngine ────────────────────────────────────────────────────

class DistractorEngine:
    """Generates plausible distractors using document concepts strictly without hardcoded domain terms."""

    def get_distractors(
        self,
        target_fact: Fact,
        all_facts: List[Fact],
        count: int = 3
    ) -> List[str]:
        distractors: List[str] = []
        target_concept_lower = target_fact.concept.lower()

        # Strategy A: Use facts of the SAME type from OTHER concepts in the document
        for f in all_facts:
            if f.concept.lower() != target_concept_lower and f.fact_type == target_fact.fact_type:
                candidate = self._truncate(f.details)
                if candidate.lower() != target_fact.details.lower() and candidate not in distractors:
                    distractors.append(candidate)
            if len(distractors) >= count:
                break

        # Strategy B: Use facts of ANY type from other concepts
        if len(distractors) < count:
            for f in all_facts:
                if f.concept.lower() != target_concept_lower:
                    candidate = self._truncate(f.details)
                    if candidate.lower() != target_fact.details.lower() and candidate not in distractors:
                        distractors.append(candidate)
                if len(distractors) >= count:
                    break

        # Strategy C: Dynamic generic technical fallback phrases (Never hardcoded Java/Bytecode!)
        generic_pool = [
            "a mechanism for managing memory allocation in computer systems",
            "a technique for converting data between different encoding formats",
            "a process of breaking down execution into independent units",
            "a standard protocol for resource communication across interfaces",
            "an optimization procedure for hardware execution units"
        ]
        shuffled_pool = list(generic_pool)
        random.shuffle(shuffled_pool)

        while len(distractors) < count and shuffled_pool:
            item = shuffled_pool.pop(0)
            if item.lower() != target_fact.details.lower() and item not in distractors:
                distractors.append(item)

        random.shuffle(distractors)
        return distractors[:count]

    def _truncate(self, text: str, max_len: int = 600) -> str:
        cleaned = clean_option_text(text)
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[:max_len].rsplit(" ", 1)[0] + "..."


# ── 5. Reusable Template Engine & Question Strategies ─────────────────────

class BaseMCQTemplate(ABC):
    @property
    @abstractmethod
    def template_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_fact_types(self) -> List[str]:
        pass

    @abstractmethod
    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        pass


class DefinitionTemplate(BaseMCQTemplate):
    """Generates clean 'What is the primary function of X?' MCQs."""
    template_name = "Definition"
    supported_fact_types = [FactType.DEFINITION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        clean_det = clean_option_text(fact.details)
        clean_det = re.sub(r'^(?:' + re.escape(fact.concept) + r'|The\s+' + re.escape(fact.concept) + r')\s+(?:is|are|refers to|is defined as)\s+', '', clean_det, flags=re.IGNORECASE).strip()
        if clean_det:
            clean_det = clean_det[0].upper() + clean_det[1:]
        else:
            clean_det = clean_option_text(fact.details)

        correct = distractor_engine._truncate(clean_det)
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        clean_distractors = []
        for d in distractors:
            cd = re.sub(r'^[A-Z][a-zA-Z0-9_-]+\s+(?:is|are|refers to|is defined as)\s+', '', d, flags=re.IGNORECASE).strip()
            clean_distractors.append(cd[0].upper() + cd[1:] if cd else d)

        options = [correct] + clean_distractors[:3]
        random.shuffle(options)

        if any(w in fact.details.lower() for w in ["function", "purpose", "role", "mechanism", "executes", "manages", "allocates"]):
            stem = f"What is the primary function of {fact.concept}?"
        else:
            stem = f"What is '{fact.concept}'?"

        return MCQ(
            id=0,
            question=stem,
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"According to page {fact.page_num}, {fact.concept} is {fact.details}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class FeatureTemplate(BaseMCQTemplate):
    """Generates clean 'What is the primary advantage of X?' MCQs."""
    template_name = "Feature"
    supported_fact_types = [FactType.FEATURE, FactType.ADVANTAGE]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if len(fact.concept) < 3 or ConceptNormalizer.is_blocked_word(fact.concept):
            return None

        correct = distractor_engine._truncate(fact.details)
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        options = [correct] + distractors
        random.shuffle(options)

        if fact.fact_type == FactType.ADVANTAGE or any(w in fact.details.lower() for w in ["advantage", "benefit", "plus"]):
            stem = f"What is the primary advantage of {fact.concept}?"
        else:
            stem = f"Which of the following is a primary function or characteristic of {fact.concept}?"

        return MCQ(
            id=0,
            question=stem,
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"Stated directly in the text on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class FillInTheBlankTemplate(BaseMCQTemplate):
    """Generates natural Fill-in-the-Blank MCQs targeting key terms."""
    template_name = "Fill in the Blank"
    supported_fact_types = [FactType.DEFINITION, FactType.FEATURE, FactType.GENERAL_FACT, FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3 or ConceptNormalizer.is_blocked_word(fact.concept):
            return None

        raw = fact.raw_text
        concept_pattern = re.compile(r'\b' + re.escape(fact.concept) + r'\b', re.IGNORECASE)
        if concept_pattern.search(raw):
            blanked_sentence = concept_pattern.sub("_________", raw, count=1)
        else:
            blanked_sentence = f"_________ is defined as: {clean_option_text(fact.details)}"

        blanked_sentence = clean_option_text(blanked_sentence)
        correct_term = fact.concept

        distractors = []
        for f in all_facts:
            if f.concept.lower() != correct_term.lower() and f.concept not in distractors and len(f.concept) >= 3 and not ConceptNormalizer.is_blocked_word(f.concept):
                distractors.append(f.concept)
            if len(distractors) >= 3:
                break

        doc_words = list({f.concept for f in all_facts if len(f.concept) >= 3 and f.concept.lower() != correct_term.lower() and not ConceptNormalizer.is_blocked_word(f.concept)})
        random.shuffle(doc_words)
        while len(distractors) < 3 and doc_words:
            w = doc_words.pop(0)
            if w not in distractors:
                distractors.append(w)

        options = [correct_term] + distractors[:3]
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"Complete the statement:\n\"{blanked_sentence}\"",
            options=options,
            correct_answer=correct_term,
            correct_index=options.index(correct_term),
            explanation=f"According to page {fact.page_num}, the correct key term is '{correct_term}'.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class TrueFalseTemplate(BaseMCQTemplate):
    """Generates natural True/False MCQs."""
    template_name = "True / False"
    supported_fact_types = [FactType.DEFINITION, FactType.GENERAL_FACT, FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3 or ConceptNormalizer.is_blocked_word(fact.concept):
            return None

        is_true = random.choice([True, False])
        clean_det = clean_option_text(fact.details)

        if is_true:
            if clean_det.lower().startswith(fact.concept.lower()):
                statement = clean_det
            else:
                statement = f"{fact.concept} is {clean_det[0].lower() + clean_det[1:] if clean_det else clean_det}"
            correct = "True"
        else:
            wrong_facts = [f for f in all_facts if f.concept.lower() != fact.concept.lower() and not ConceptNormalizer.is_blocked_word(f.concept)]
            if not wrong_facts:
                return None
            wrong_fact = random.choice(wrong_facts)
            clean_wrong = clean_option_text(wrong_fact.details)
            clean_wrong = re.sub(r'^[A-Z][a-zA-Z0-9_-]+\s+(?:is|are|refers to)\s+', '', clean_wrong, flags=re.IGNORECASE).strip()
            statement = f"{fact.concept} is {clean_wrong[0].lower() + clean_wrong[1:] if clean_wrong else clean_wrong}"
            correct = "False"

        options = ["True", "False"]

        return MCQ(
            id=0,
            question=f"True or False: {statement}",
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"Based on the notes on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class SituationalTemplate(BaseMCQTemplate):
    """Generates domain-neutral scenario MCQs without concept leakage."""
    template_name = "Situational Application"
    supported_fact_types = [FactType.DEFINITION, FactType.FEATURE, FactType.GENERAL_FACT]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3 or ConceptNormalizer.is_blocked_word(fact.concept):
            return None

        scenario = clean_option_text(fact.details)
        scenario = re.sub(r'^(?:' + re.escape(fact.concept) + r'|The\s+' + re.escape(fact.concept) + r')\s+(?:is|are|refers to|is defined as)\s+', '', scenario, flags=re.IGNORECASE).strip()
        correct_term = fact.concept

        distractors = []
        for f in all_facts:
            if f.concept.lower() != correct_term.lower() and f.concept not in distractors and len(f.concept) >= 3 and not ConceptNormalizer.is_blocked_word(f.concept):
                distractors.append(f.concept)
            if len(distractors) >= 3:
                break

        doc_words = list({f.concept for f in all_facts if len(f.concept) >= 3 and f.concept.lower() != correct_term.lower() and not ConceptNormalizer.is_blocked_word(f.concept)})
        random.shuffle(doc_words)
        while len(distractors) < 3 and doc_words:
            w = doc_words.pop(0)
            if w not in distractors:
                distractors.append(w)

        options = [correct_term] + distractors[:3]
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"Scenario: In computer systems, a component is required that \"{scenario}\". Which key term or component applies?",
            options=options,
            correct_answer=correct_term,
            correct_index=options.index(correct_term),
            explanation=f"According to page {fact.page_num}, '{correct_term}' is the exact component responsible.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class TerminologyDefinitionTemplate(BaseMCQTemplate):
    """Generates 'Which component is defined as: ...' questions where the answer term is NEVER in the stem."""
    template_name = "Terminology Definition"
    supported_fact_types = [FactType.DEFINITION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3 or ConceptNormalizer.is_blocked_word(fact.concept):
            return None

        clean_det = clean_option_text(fact.details)
        # Scrub all occurrences of fact.concept from definition excerpt
        concept_pattern = re.compile(r'\b' + re.escape(fact.concept) + r's?\b', re.IGNORECASE)
        clean_det = concept_pattern.sub("_________", clean_det)
        clean_det = re.sub(r'^\s*(?:is|are|refers to|is defined as)\s+', '', clean_det, flags=re.IGNORECASE).strip()
        if not clean_det or len(clean_det) < 5:
            return None

        stem = f"Which component or concept is defined as: \"{clean_det[0].lower() + clean_det[1:]}\"?"

        correct_term = fact.concept
        distractors = []
        for f in all_facts:
            if f.concept.lower() != correct_term.lower() and f.concept not in distractors and len(f.concept) >= 3 and not ConceptNormalizer.is_blocked_word(f.concept):
                distractors.append(f.concept)
            if len(distractors) >= 3:
                break

        doc_words = list({f.concept for f in all_facts if len(f.concept) >= 3 and f.concept.lower() != correct_term.lower() and not ConceptNormalizer.is_blocked_word(f.concept)})
        random.shuffle(doc_words)
        while len(distractors) < 3 and doc_words:
            w = doc_words.pop(0)
            if w not in distractors:
                distractors.append(w)

        options = [correct_term] + distractors[:3]
        random.shuffle(options)

        return MCQ(
            id=0,
            question=stem,
            options=options,
            correct_answer=correct_term,
            correct_index=options.index(correct_term),
            explanation=f"According to page {fact.page_num}, '{correct_term}' is defined as: {fact.details}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class SectionHeadingInclusionTemplate(BaseMCQTemplate):
    """Generates 'Which of the following is included under X?' MCQs with 'All of the above' options."""
    template_name = "Heading Components"
    supported_fact_types = [FactType.DEFINITION, FactType.FEATURE, FactType.GENERAL_FACT]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        normalizer = ConceptNormalizer()
        valid_concepts = []
        for f in all_facts:
            norm_c = normalizer.normalize(f.concept)
            if norm_c and norm_c.title() not in valid_concepts and len(norm_c) >= 3:
                valid_concepts.append(norm_c.title())

        if len(valid_concepts) < 3:
            return None

        opts = random.sample(valid_concepts, 3)
        correct_ans = "All of the above"
        options = opts + [correct_ans]
        random.shuffle(options)

        heading_name = "Operating System Components & Structures" if any(w in fact.raw_text.lower() for w in ["system", "operating", "os", "structure"]) else f"{fact.concept} Elements"

        return MCQ(
            id=0,
            question=f"Which of the following is included under {heading_name}?",
            options=options,
            correct_answer=correct_ans,
            correct_index=options.index(correct_ans),
            explanation=f"All listed choices ({opts[0]}, {opts[1]}, {opts[2]}) are valid components mentioned on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class SectionHeadingNotStructureTemplate(BaseMCQTemplate):
    """Generates 'Which of the following is NOT an element of X?' exception questions."""
    template_name = "NOT Structure Exception"
    supported_fact_types = [FactType.DEFINITION, FactType.FEATURE, FactType.GENERAL_FACT]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        all_concepts = list({f.concept for f in all_facts if len(f.concept) >= 3 and not ConceptNormalizer.is_blocked_word(f.concept)})
        if len(all_concepts) < 2:
            return None

        valid_opts = random.sample(all_concepts, min(3, len(all_concepts)))
        fake_option = random.choice(["System Machine", "Virtual Monitor", "Process Colour", "Memory Shifter"])
        
        options = valid_opts + [fake_option]
        random.shuffle(options)

        heading_name = "Operating System Structure" if any(w in fact.raw_text.lower() for w in ["system", "operating", "os", "structure"]) else f"{fact.concept} Structure"

        return MCQ(
            id=0,
            question=f"Which of the following is NOT an element of {heading_name}?",
            options=options,
            correct_answer=fake_option,
            correct_index=options.index(fake_option),
            explanation=f"'{fake_option}' is not a valid structure or component mentioned in the text on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class AbbreviationTemplate(BaseMCQTemplate):
    """Generates 'What does X stand for?' MCQs."""
    template_name = "Abbreviation"
    supported_fact_types = [FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        correct = fact.details.strip()
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        options = [correct] + distractors
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"What does the abbreviation '{fact.concept}' stand for?",
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"According to page {fact.page_num}, '{fact.concept}' stands for '{correct}'.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class GeneralFactTemplate(BaseMCQTemplate):
    """Generates general conceptual MCQs."""
    template_name = "General Fact"
    supported_fact_types = [FactType.GENERAL_FACT, FactType.DISADVANTAGE]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        correct = distractor_engine._truncate(fact.details)
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        options = [correct] + distractors
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"Which of the following statements about {fact.concept} is correct?",
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"Stated in the text on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


# ── 6. Template Engine Registry ───────────────────────────────────────────

class TemplateEngine:
    """Registry-based Template Engine for resolving and applying MCQ strategies."""

    def __init__(self):
        self._registry: Dict[str, List[BaseMCQTemplate]] = {}
        # Register all paper-setter testing strategies (No scenario, artificial headings, or 'None of the above' templates)
        self.register_template(TerminologyDefinitionTemplate())
        self.register_template(FillInTheBlankTemplate())
        self.register_template(DefinitionTemplate())
        self.register_template(TrueFalseTemplate())
        self.register_template(FeatureTemplate())
        self.register_template(AbbreviationTemplate())
        self.register_template(GeneralFactTemplate())

    def register_template(self, template: BaseMCQTemplate) -> None:
        for ftype in template.supported_fact_types:
            if ftype not in self._registry:
                self._registry[ftype] = []
            self._registry[ftype].append(template)

    def generate_mcq(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        templates = list(self._registry.get(fact.fact_type, []))
        general_templates = list(self._registry.get(FactType.GENERAL_FACT, []))
        for g_temp in general_templates:
            if g_temp not in templates:
                templates.append(g_temp)

        if not templates:
            return None

        random.shuffle(templates)
        for t in templates:
            mcq = t.generate(fact, distractor_engine, all_facts)
            if mcq:
                return mcq
        return None


# ── 7. MCQ Validator ──────────────────────────────────────────────────────

class MCQValidator:
    """Validates generated MCQs to guarantee non-empty options and single correct index."""

    def validate(self, mcq: MCQ) -> bool:
        if not mcq or not mcq.question or len(mcq.options) != 4:
            return False

        unique_options = set(mcq.options)
        if len(unique_options) != 4:
            return False

        if mcq.correct_index < 0 or mcq.correct_index >= 4:
            return False

        if mcq.options[mcq.correct_index] != mcq.correct_answer:
            return False

        # Anti-Leakage Audit: Ensure answer/concept term does NOT leak inside fill-in-the-blank or definition stems
        ans_clean = mcq.correct_answer.strip().lower()
        q_clean = mcq.question.strip().lower()

        # Reject artificial heading inclusion questions
        if "included under" in q_clean or "operating system components" in q_clean:
            return False

        if ("defined as:" in q_clean or "which component or concept" in q_clean or "complete the statement" in q_clean):
            if len(ans_clean) >= 3 and re.search(r'\b' + re.escape(ans_clean) + r's?\b', q_clean):
                return False

        return True


# ── 8. Main QuizGenerator Pipeline ──────────────────────────────────────────

class QuizGenerator:
    """EduMind Main Quiz Generator orchestrator adhering to Llama 3.2 1B SLM-Routing + Fixed Deterministic Rules."""

    def __init__(self, llm_model: str = "llama3.2:1b"):
        self.llm_model = llm_model
        self.normalizer = ConceptNormalizer()
        self.knowledge_builder = KnowledgeBuilder(self.normalizer)
        self.fact_classifier = FactClassifier(self.normalizer)
        self.distractor_engine = DistractorEngine()
        self.template_engine = TemplateEngine()
        self.validator = MCQValidator()

    def generate_quiz(
        self,
        documents: List[Document],
        num_questions: int = 5,
        topic: str = "",
        start_page: int = 1,
        end_page: int = 10
    ) -> Dict[str, Any]:
        """Generates up to 10 high-yield conceptual MCQs from selected document pages."""
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
            facts = self.fact_classifier.classify_text(doc.page_content, page_num=p_num)
            all_facts.extend(facts)

        if not all_facts:
            return {"success": False, "error": f"Pages {start_page}-{actual_end} contain no extractable concepts."}

        num_questions = max(1, min(10, num_questions))

        # Group facts by concept (prioritize DEFINITION)
        concept_best_fact: Dict[str, Fact] = {}
        for f in all_facts:
            norm_c = f.concept.lower()
            if norm_c not in concept_best_fact:
                concept_best_fact[norm_c] = f
            else:
                existing = concept_best_fact[norm_c]
                if f.fact_type == FactType.DEFINITION and existing.fact_type != FactType.DEFINITION:
                    concept_best_fact[norm_c] = f
                elif f.fact_type == existing.fact_type:
                    if f.metadata.get("salience_score", 1.0) > existing.metadata.get("salience_score", 1.0):
                        concept_best_fact[norm_c] = f

        target_facts = list(concept_best_fact.values())
        target_facts.sort(
            key=lambda x: (x.fact_type == FactType.DEFINITION, x.metadata.get("salience_score", 1.0)),
            reverse=True
        )

        mcqs: List[MCQ] = []
        seen_questions = set()
        seen_concepts = set()

        for fact in target_facts:
            if len(mcqs) >= num_questions:
                break

            if fact.concept.lower() in seen_concepts:
                continue

            mcq = self.template_engine.generate_mcq(fact, self.distractor_engine, all_facts)
            if mcq and self.validator.validate(mcq):
                if mcq.question.lower() not in seen_questions:
                    mcq.id = len(mcqs) + 1
                    mcqs.append(mcq)
                    seen_questions.add(mcq.question.lower())
                    seen_concepts.add(fact.concept.lower())

        # Fallback to remaining facts if target count not met
        if len(mcqs) < num_questions:
            for fact in all_facts:
                if len(mcqs) >= num_questions:
                    break
                if fact.concept.lower() in seen_concepts:
                    continue
                mcq = self.template_engine.generate_mcq(fact, self.distractor_engine, all_facts)
                if mcq and self.validator.validate(mcq):
                    if mcq.question.lower() not in seen_questions:
                        mcq.id = len(mcqs) + 1
                        mcqs.append(mcq)
                        seen_questions.add(mcq.question.lower())
                        seen_concepts.add(fact.concept.lower())

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
