#!/usr/bin/env python3
"""Create a quiz from a PDF page range using a local Ollama model.

No cloud service or API key is used: the program invokes ``ollama run`` on
the machine.  Install the model beforehand, for example:
    ollama pull llama3.2:3b
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_pages(spec: str, page_count: int) -> list[int]:
    """Return zero-based PDF page indexes from a spec such as ``1-3,7``."""
    chosen: set[int] = set()
    for item in spec.replace(" ", "").split(","):
        if not item:
            continue
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", item)
        if not match:
            raise ValueError(f"Invalid page range item: {item!r}")
        first, last = (int(n) for n in match.groups(default=match.group(1)))
        if first > last:
            raise ValueError(f"Range starts after it ends: {item!r}")
        if first < 1 or last > page_count:
            raise ValueError(f"Page range {item!r} is outside 1-{page_count}")
        chosen.update(range(first - 1, last))
    if not chosen:
        raise ValueError("Specify at least one page")
    return sorted(chosen)


def extract_text(pdf_path: Path, pages: list[int]) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Missing dependency: install it with `python -m pip install pypdf`.") from exc

    reader = PdfReader(str(pdf_path))
    text = "\n\n".join(
        f"[PDF page {page + 1}]\n{reader.pages[page].extract_text() or ''}" for page in pages
    ).strip()
    if not text:
        raise RuntimeError("No extractable text was found. OCR the PDF first, then try again.")
    return text


def build_prompt(source: str, count: int, difficulty: str) -> str:
    return f"""You are an exacting educator. Based only on the source below, create {count}
{difficulty} quiz questions. Include a mix of multiple-choice and short-answer
questions when the source permits. Do not invent facts. Return ONLY valid JSON:

{{
  "questions": [
    {{"type": "multiple_choice", "question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "explanation": "..."}},
    {{"type": "short_answer", "question": "...", "answer": "...", "explanation": "..."}}
  ]
}}

SOURCE:
{source}
"""


def local_ollama(model: str, prompt: str) -> dict:
    executable = shutil.which("ollama")
    if not executable:
        raise RuntimeError("Ollama was not found on PATH. Install/start Ollama, then pull the selected model.")
    result = subprocess.run(
        [executable, "run", model], input=prompt, text=True, capture_output=True, encoding="utf-8"
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Ollama failed: {detail}")
    raw = result.stdout.strip()
    # Models occasionally wrap otherwise valid output in a Markdown code fence.
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    try:
        quiz = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama did not return valid JSON: {exc}\nRaw output:\n{raw}") from exc
    if not isinstance(quiz.get("questions"), list) or not quiz["questions"]:
        raise RuntimeError("Ollama returned JSON but no questions.")
    return quiz


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local Ollama quiz from PDF pages.")
    parser.add_argument("pdf", type=Path, help="Source PDF")
    parser.add_argument("pages", help="Page range, e.g. 1-5 or 1-3,7")
    parser.add_argument("-n", "--questions", type=int, default=10, help="Number of questions (default: 10)")
    parser.add_argument("--model", default="llama3.2:1b", help="Installed local Ollama model")
    parser.add_argument("--difficulty", default="mixed-difficulty", choices=["easy", "medium", "hard", "mixed-difficulty"])
    parser.add_argument("-o", "--output", type=Path, default=Path("quiz.json"), help="Quiz JSON output")
    args = parser.parse_args()
    if args.questions < 1:
        parser.error("--questions must be at least 1")
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")

    try:
        from pypdf import PdfReader
        all_pages = len(PdfReader(str(args.pdf)).pages)
        page_indexes = parse_pages(args.pages, all_pages)
        source = extract_text(args.pdf, page_indexes)
        quiz = local_ollama(args.model, build_prompt(source, args.questions, args.difficulty))
        quiz["source_pdf"] = str(args.pdf.resolve())
        quiz["pages"] = [number + 1 for number in page_indexes]
        quiz["model"] = args.model
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(quiz, indent=2, ensure_ascii=False), encoding="utf-8")
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output} with {len(quiz['questions'])} questions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
