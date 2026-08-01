"""
quiz_generator_backup.py — EduMind Modular Architectural Quiz Engine Backup
Senior AI Systems Engineering Architecture for Local 1B SLM + Deterministic Pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional, Set, Type

from langchain_core.documents import Document
from langchain_ollama import OllamaLLM

logger = logging.getLogger(__name__)


# ── Data Models ─────────────────────────────────────────────────────────────

class FactType:
    DEFINITION = "definition"
    FEATURE = "feature"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    TYPE_IDENTIFICATION = "type_identification"
    ABBREVIATION = "abbreviation"
    PROCESS_STEP = "process_step"
    GENERAL_FACT = "general_fact"


@dataclass
class Fact:
    raw_text: str
    fact_type: str
    concept: str
    details: str
    page_num: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    confidence_score: float = 1.0


# ── 1. DocumentCleaner & ConceptNormalizer ─────────────────────────────────

class DocumentCleaner:
    """Preprocesses raw document text to remove OCR artifacts, bullets, and page headers."""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        s = text

        s = re.sub(r'\[?Page\s+\d+(?:\s+(?:of|/)\s+\d+)?\]?:?', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^\s*Unit\s+\d+\s*[-:]?\s*', '', s, flags=re.IGNORECASE | re.MULTILINE)
        s = re.sub(r'^\s*Chapter\s+\d+\s*[-:]?\s*', '', s, flags=re.IGNORECASE | re.MULTILINE)
        s = re.sub(r'^\s*[O0o]\s+', '', s, flags=re.MULTILINE)
        s = re.sub(r'(?<=\n)\s*[O0o]\s+', '', s)
        s = re.sub(r'[•●▪✓\u2022\u25cf\u25aa\uf0b7]', ' ', s)
        s = re.sub(r'^\s*(?:#+|\-{3,}|\={3,})\s*', '', s, flags=re.MULTILINE)
        s = s.replace("\r", " ").replace("`", "")
        s = re.sub(r'\n+', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s


class ConceptNormalizer:
    """Cleans, normalizes, and filters concept terms, ignoring layout/section headings."""

    TRANSITION_PHRASES: Set[str] = {
        "for this reason", "for this reason there", "in addition", "therefore",
        "however", "thus", "for example", "as a result", "on the other hand",
        "furthermore", "in other words", "in conclusion", "consequently",
        "nevertheless", "on the contrary", "in contrast", "for instance",
        "due to this", "as mentioned", "as discussed", "the term", "this term",
        "note that", "it is important", "according to", "in general", "unlike",
        "unlike the", "examples", "example", "examples:", "that is", "this is"
    }

    SECTION_HEADINGS: Set[str] = {
        "executive overview", "detailed breakdown", "core mechanisms",
        "key technical concepts & definitions", "structure of a java program",
        "java tokens", "examples", "variables", "scope of variables",
        "comprehensive study notes", "performance overhead", "gui limitations",
        "initialization", "compilation", "execution", "summary", "overview",
        "introduction", "background", "conclusion", "table of contents",
        "key technical concepts", "detailed breakdown & core mechanisms",
        "unit 1 introduction", "unit 1"
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
        "limitations", "overview", "breakdown", "platform", "unit"
    }

    VERB_INITIAL_WORDS: Set[str] = {
        "helps", "follows", "difficult", "allows", "provides", "supports",
        "includes", "contains", "requires", "executes", "creates", "defines",
        "implements", "reduces", "improves", "manages", "handles", "converts",
        "unit", "chapter", "section", "module", "part", "table", "figure",
        "page", "header", "footer", "topic", "platform", "helps in self"
    }

    def normalize(self, term: str) -> Optional[str]:
        if not term:
            return None

        cleaned = re.sub(r'^\s*(?:\d+[\.\)]|[-•●*])\s*', '', term).strip()
        cleaned = re.sub(r'[:\-;]\s*$', '', cleaned).strip()
        cleaned = re.sub(r'^[A-Z0-9\s]{2,}\s+(?=[A-Z][a-z])', '', cleaned).strip()
        if not cleaned:
            cleaned = term.strip()

        cleaned = re.sub(
            r'^(?:The\s+term\s+|This\s+term\s+|The\s+|A\s+|An\s+|This\s+|That\s+|These\s+|Those\s+)',
            '',
            cleaned,
            flags=re.IGNORECASE
        ).strip()

        cleaned = re.sub(r'[:\-;]\s*$', '', cleaned).strip()
        norm = cleaned.lower()

        first_word = norm.split()[0] if norm.split() else ""
        if first_word in self.VERB_INITIAL_WORDS:
            return None

        if norm in self.SECTION_HEADINGS or norm in self.TRANSITION_PHRASES or norm in self.GENERIC_CONCEPTS:
            return None
        if norm.startswith(("the ", "this ", "that ", "it ", "these ", "those ", "using ")):
            return None
        if len(cleaned) < 4 or len(cleaned.split()) > 4:
            return None

        if not cleaned[0].isalnum():
            return None

        return cleaned[0].upper() + cleaned[1:]


def clean_option_text(text: str) -> str:
    if not text:
        return ""
    s = text.replace("`", "").replace("\r", " ").replace("\n", " ")
    s = re.sub(r'^(?:Executive Overview|Detailed Breakdown|Core Mechanisms|GUI Limitations|Performance Overhead|Java Tokens|Examples|Scope of Variables)\s*', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'^\s*(?:[•●*-]|\b[a-z0-9][\.\)]\b)\s*', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'^(?:[A-Za-z0-9_-]{2,20}\s*:\s*|\[?Page\s+\d+\]?:?\s*)', '', s).strip()
    s = re.sub(r'[:\-;]\s*$', '', s).strip()
    s = re.sub(r'^(?:is\s+a\s+|is\s+an\s+|is\s+the\s+|refers\s+to\s+)', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'\s+', ' ', s).strip()

    if s:
        return s[0].upper() + s[1:]
    return s


class KnowledgeBuilder:
    def __init__(self, normalizer: ConceptNormalizer):
        self.normalizer = normalizer

    def build_sentences(self, text: str) -> List[str]:
        cleaned = DocumentCleaner.clean_text(text)
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|;\s+(?=[A-Z])|\s*(?:\b[iI1-9][\)\.]\b)\s*', cleaned)
        sentences = []
        for p in parts:
            p_clean = clean_option_text(p)
            if 25 <= len(p_clean) <= 350 and not p_clean.startswith(("Figure", "Table", "Page")):
                sentences.append(p_clean)
        return sentences


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
            if len(sentence) < 30 or len(sentence) > 300:
                continue

            if re.match(r'^(?:Unlike|For this reason|As a result|In addition|For example|However|Therefore)\b', sentence, re.IGNORECASE):
                continue

            abbr_match = re.search(r'\b([A-Z]{2,10})\s*\(([^)]+)\)', sentence)
            if abbr_match:
                short_form = abbr_match.group(1)
                full_form = abbr_match.group(2)
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

            is_action_verb = bool(re.search(r'\b(?:provides|allows|enables|supports|includes|contains|uses|executes|improves|reduces)\b', sentence, re.IGNORECASE))

            if not is_action_verb:
                def_patterns = [
                    r'^\s*([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s*:\s*([^.]{15,200})\.?',
                    r'^\s*([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s*[-–—]\s*([^.]{15,200})\.?',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)\s+is\s+((?:the|a|an)\s+[^.]{15,120})\.',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)\s+refers\s+to\s+([^.]{15,120})\.',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)\s+is\s+defined\s+as\s+([^.]{15,120})\.',
                    r'([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)\s+is\s+a\s+([^.]{15,120})\.',
                ]
                found_def = False
                for pat in def_patterns:
                    m = re.search(pat, sentence)
                    if m:
                        raw_concept = m.group(1)
                        details = m.group(2).strip()
                        clean_concept = self.normalizer.normalize(raw_concept)
                        if clean_concept and len(details) >= 15:
                            salience = 4.0 + concept_counts.get(clean_concept.lower(), 1)
                            facts.append(Fact(
                                raw_text=sentence,
                                fact_type=FactType.DEFINITION,
                                concept=clean_concept,
                                details=details,
                                page_num=page_num,
                                metadata={"salience_score": salience}
                            ))
                            found_def = True
                            break
                if found_def:
                    continue

            if re.search(r'\b(?:advantage|benefit|plus|upside)\b', sentence, re.IGNORECASE):
                subj = self._extract_subject(sentence)
                if subj:
                    salience = 3.0 + concept_counts.get(subj.lower(), 1)
                    facts.append(Fact(raw_text=sentence, fact_type=FactType.ADVANTAGE, concept=subj, details=sentence, page_num=page_num, metadata={"salience_score": salience}))
                continue
            elif re.search(r'\b(?:disadvantage|drawback|limitation|downside|issue)\b', sentence, re.IGNORECASE):
                subj = self._extract_subject(sentence)
                if subj:
                    salience = 3.0 + concept_counts.get(subj.lower(), 1)
                    facts.append(Fact(raw_text=sentence, fact_type=FactType.DISADVANTAGE, concept=subj, details=sentence, page_num=page_num, metadata={"salience_score": salience}))
                continue
            elif is_action_verb or re.search(r'\b(?:feature|characteristic|property|attribute)\b', sentence, re.IGNORECASE):
                subj = self._extract_subject(sentence)
                if subj:
                    salience = 3.0 + concept_counts.get(subj.lower(), 1)
                    facts.append(Fact(raw_text=sentence, fact_type=FactType.FEATURE, concept=subj, details=sentence, page_num=page_num, metadata={"salience_score": salience}))
                continue

            subj_match = re.match(
                r'(?:The\s+|A\s+|An\s+)?([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,3}?)'
                r'\s+(?:is|are|was|were|has|have|provides|allows|supports|uses|includes|contains|represents|requires|defines|creates)\b',
                sentence
            )
            if subj_match:
                clean_subj = self.normalizer.normalize(subj_match.group(1))
                if clean_subj:
                    salience = 2.0 + concept_counts.get(clean_subj.lower(), 1)
                    facts.append(Fact(
                        raw_text=sentence,
                        fact_type=FactType.GENERAL_FACT,
                        concept=clean_subj,
                        details=sentence,
                        page_num=page_num,
                        metadata={"salience_score": salience}
                    ))

        return facts

    def _extract_subject(self, sentence: str) -> Optional[str]:
        m = re.match(r'^(?:The\s+|A\s+|An\s+|This\s+|That\s+)?([A-Z][a-zA-Z0-9_-]+(?:\s+[A-Za-z0-9_-]+){0,2}?)', sentence)
        if m:
            clean = self.normalizer.normalize(m.group(1))
            if clean and clean.lower() not in ("the", "a", "an", "this", "system", "program", "code", "it", "they"):
                return clean
        return None


class DistractorEngine:
    GENERIC_DEFINITIONS: List[str] = [
        "a method for managing memory allocation in computer programs",
        "a technique for converting data between different encoding formats",
        "a process of breaking down programs into independent executable modules",
        "a mechanism for handling runtime errors and exception propagation",
        "a standard protocol for network communication between distributed systems",
        "a way to optimize compiler output for target hardware architectures",
    ]

    GENERIC_FACTS: List[str] = [
        "It is primarily used for managing hardware interrupt requests",
        "It defines the rules for data transmission over network protocols",
        "It converts high-level programming code into assembly language instructions",
        "It manages the scheduling of concurrent processes in the operating system",
        "It handles binary serialization of complex data structures",
        "It provides automatic load balancing across distributed servers",
    ]

    def get_distractors(
        self,
        target_fact: Fact,
        all_facts: List[Fact],
        count: int = 3
    ) -> List[str]:
        distractors: List[str] = []
        target_concept_lower = target_fact.concept.lower()

        for f in all_facts:
            if f.concept.lower() != target_concept_lower and f.fact_type == target_fact.fact_type:
                candidate = self._truncate(f.details)
                if candidate.lower() != target_fact.details.lower() and candidate not in distractors:
                    distractors.append(candidate)
            if len(distractors) >= count:
                break

        if len(distractors) < count:
            for f in all_facts:
                if f.concept.lower() != target_concept_lower:
                    candidate = self._truncate(f.details)
                    if candidate.lower() != target_fact.details.lower() and candidate not in distractors:
                        distractors.append(candidate)
                if len(distractors) >= count:
                    break

        pool = self.GENERIC_DEFINITIONS if target_fact.fact_type == FactType.DEFINITION else self.GENERIC_FACTS
        shuffled_pool = list(pool)
        random.shuffle(shuffled_pool)

        while len(distractors) < count and shuffled_pool:
            item = shuffled_pool.pop(0)
            if item.lower() != target_fact.details.lower() and item not in distractors:
                distractors.append(item)

        random.shuffle(distractors)
        return distractors[:count]

    def _truncate(self, text: str, max_len: int = 350) -> str:
        cleaned = clean_option_text(text)
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[:max_len].rsplit(" ", 1)[0] + "..."


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
    template_name = "Definition"
    supported_fact_types = [FactType.DEFINITION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        correct = distractor_engine._truncate(fact.details)
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        options = [correct] + distractors
        random.shuffle(options)
        correct_idx = options.index(correct)

        return MCQ(
            id=0,
            question=f"What does '{fact.concept}' refer to?",
            options=options,
            correct_answer=correct,
            correct_index=correct_idx,
            explanation=f"According to the text on page {fact.page_num}, {fact.concept} refers to {fact.details}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class FeatureTemplate(BaseMCQTemplate):
    template_name = "Feature"
    supported_fact_types = [FactType.FEATURE, FactType.ADVANTAGE]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if len(fact.concept) < 4 or fact.concept.lower() in ("this", "that", "these", "those", "using", "types", "type"):
            return None

        correct = distractor_engine._truncate(fact.details)
        distractors = distractor_engine.get_distractors(fact, all_facts, count=3)

        options = [correct] + distractors
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"Which of the following is a feature or characteristic of {fact.concept}?",
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"Stated directly in the text on page {fact.page_num}.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class AbbreviationTemplate(BaseMCQTemplate):
    template_name = "Abbreviation Expansion"
    supported_fact_types = [FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        correct = fact.details
        words = correct.split()
        d1 = " ".join([w.capitalize() + " System" if i == len(words)-1 else w for i, w in enumerate(words)])
        d2 = " ".join(["Dynamic" if i == 0 else w for i, w in enumerate(words)])
        d3 = " ".join([w if i != 1 else "Central" for i, w in enumerate(words)])

        distractors = [d for d in [d1, d2, d3] if d.lower() != correct.lower()]
        while len(distractors) < 3:
            distractors.append("Standard Protocol Extension")

        options = [correct] + distractors[:3]
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"What does the abbreviation '{fact.concept}' stand for?",
            options=options,
            correct_answer=correct,
            correct_index=options.index(correct),
            explanation=f"'{fact.concept}' stands for {correct} (Page {fact.page_num}).",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class GeneralFactTemplate(BaseMCQTemplate):
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


class FillInTheBlankTemplate(BaseMCQTemplate):
    template_name = "Fill in the Blank"
    supported_fact_types = [FactType.DEFINITION, FactType.FEATURE, FactType.GENERAL_FACT, FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3 or fact.concept.lower() in ("this", "that", "these", "those"):
            return None

        raw = fact.raw_text
        concept_pattern = re.compile(re.escape(fact.concept), re.IGNORECASE)
        if not concept_pattern.search(raw):
            return None

        blanked_sentence = concept_pattern.sub("_________", raw, count=1)
        blanked_sentence = clean_option_text(blanked_sentence)

        correct_term = fact.concept

        distractors = []
        for f in all_facts:
            if f.concept.lower() != correct_term.lower() and f.concept not in distractors and len(f.concept) >= 3:
                distractors.append(f.concept)
            if len(distractors) >= 3:
                break

        fallback_terms = ["Identifier", "Literal", "Variable", "Operator", "Class", "Object", "Package", "Method"]
        random.shuffle(fallback_terms)
        while len(distractors) < 3 and fallback_terms:
            t = fallback_terms.pop(0)
            if t.lower() != correct_term.lower() and t not in distractors:
                distractors.append(t)

        options = [correct_term] + distractors[:3]
        random.shuffle(options)

        return MCQ(
            id=0,
            question=f"Fill in the blank: \"{blanked_sentence}\"",
            options=options,
            correct_answer=correct_term,
            correct_index=options.index(correct_term),
            explanation=f"According to page {fact.page_num}, the correct term is '{correct_term}'.",
            template_name=self.template_name,
            page_num=fact.page_num
        )


class TrueFalseTemplate(BaseMCQTemplate):
    template_name = "True / False"
    supported_fact_types = [FactType.DEFINITION, FactType.GENERAL_FACT, FactType.ABBREVIATION]

    def generate(self, fact: Fact, distractor_engine: DistractorEngine, all_facts: List[Fact]) -> Optional[MCQ]:
        if not fact.concept or len(fact.concept) < 3:
            return None

        is_true = random.choice([True, False])

        if is_true:
            statement = f"'{fact.concept}' is defined as: {clean_option_text(fact.details)}"
            correct = "True"
        else:
            wrong_facts = [f for f in all_facts if f.concept.lower() != fact.concept.lower()]
            if not wrong_facts:
                return None
            wrong_fact = random.choice(wrong_facts)
            statement = f"'{fact.concept}' is defined as: {clean_option_text(wrong_fact.details)}"
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


class TemplateEngine:
    def __init__(self):
        self._registry: Dict[str, List[BaseMCQTemplate]] = {}
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
        templates = self._registry.get(fact.fact_type, [])
        if not templates:
            templates = self._registry.get(FactType.GENERAL_FACT, [])

        if not templates:
            return None

        selected_template = random.choice(templates)
        return selected_template.generate(fact, distractor_engine, all_facts)


class MCQValidator:
    GARBAGE_PATTERNS = {
        "option1", "option2", "option3", "option4",
        "a answer", "b answer", "your question here", "why correct"
    }

    def validate(self, mcq: Optional[MCQ]) -> bool:
        if mcq is None:
            return False

        if not mcq.question or len(mcq.question.strip()) < 12:
            return False

        if not isinstance(mcq.options, list) or len(mcq.options) not in (2, 4):
            return False

        for opt in mcq.options:
            s = str(opt).strip().lower()
            if len(s) < 2 or s in self.GARBAGE_PATTERNS or s in ("a", "b", "c", "d"):
                return False

        norms = [str(o).strip().lower() for o in mcq.options]
        if len(set(norms)) != len(mcq.options):
            return False

        if mcq.correct_answer not in mcq.options:
            return False

        if mcq.options[mcq.correct_index] != mcq.correct_answer:
            return False

        return True


class QuizGenerator:
    def __init__(self, llm_model: str = "llama3.2:1b"):
        self.llm_model = llm_model
        self.normalizer = ConceptNormalizer()
        self.knowledge_builder = KnowledgeBuilder(self.normalizer)
        self.fact_classifier = FactClassifier(self.normalizer)
        self.distractor_engine = DistractorEngine()
        self.template_engine = TemplateEngine()
        self.validator = MCQValidator()
        self.slm = OllamaLLM(model=llm_model, temperature=0.2)

    def generate_quiz(
        self,
        documents: List[Document],
        num_questions: int = 5,
        topic: str = "",
        start_page: int = 1,
        end_page: int = 9999
    ) -> Dict[str, Any]:
        actual_end = min(end_page, start_page + 9)
        filtered_docs = [
            d for d in documents
            if start_page <= d.metadata.get("page", 1) <= actual_end
        ]

        if not filtered_docs:
            return {"success": False, "error": f"No content between pages {start_page} and {actual_end}."}

        source = filtered_docs[0].metadata.get("source", "Document")

        all_facts: List[Fact] = []
        for d in filtered_docs:
            pg = d.metadata.get("page", 1)
            txt = (d.page_content or "").strip()
            if txt:
                facts = self.fact_classifier.classify_text(txt, page_num=pg)
                all_facts.extend(facts)

        if not all_facts:
            return {"success": False, "error": f"Pages {start_page}-{actual_end} contain no extractable concepts."}

        num_questions = max(1, min(5, num_questions))

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

        unique_facts = list(concept_best_fact.values())
        unique_facts.sort(key=lambda f: (f.fact_type == FactType.DEFINITION, f.metadata.get("salience_score", 1.0)), reverse=True)

        selected_facts = unique_facts[:num_questions]

        generated_mcqs: List[Dict[str, Any]] = []
        q_id = 1

        for fact in selected_facts[:num_questions]:
            mcq = self.template_engine.generate_mcq(fact, self.distractor_engine, all_facts)

            if not self.validator.validate(mcq):
                mcq = GeneralFactTemplate().generate(fact, self.distractor_engine, all_facts)

            if mcq and self.validator.validate(mcq):
                generated_mcqs.append({
                    "id": q_id,
                    "question": mcq.question,
                    "options": mcq.options,
                    "answer": mcq.correct_answer,
                    "correct_index": mcq.correct_index,
                    "explanation": mcq.explanation,
                    "page": mcq.page_num,
                    "template": mcq.template_name
                })
                q_id += 1

        return {
            "success": True,
            "quiz_type": f"Practice Quiz ({source})",
            "range": f"Pages {start_page} - {actual_end}",
            "questions": generated_mcqs
        }
