from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.2:1b", temperature=0.1)

prompt = """You are an expert academic examiner. Read the textbook excerpt below and generate exactly ONE high-quality, conceptual multiple-choice question.

Guidelines:
1. The question must test core concepts, technical principles, or critical mechanisms. Do NOT ask trivial, superficial, or filler questions.
2. Provide exactly 4 options. Make sure one option is 100% correct, and the other 3 options are incorrect but highly plausible distractors.
3. Both the question and the correct answer must be supported directly by the text excerpt. Do NOT hallucinate.
4. Output the result STRICTLY as a raw JSON object, with no other text, markdown blocks (like ```json), or explanations.

Target Excerpt (Pages 1 to 2):
Page 1: Unit-1 Introduction to Object oriented programming concepts. OOP vs Procedural Programming. OOP represents concepts as objects that contain data and code.

Required JSON schema:
{
  "question": "Clear, concise conceptual question...",
  "options": [
    "Option A text",
    "Option B text",
    "Option C text",
    "Option D text"
  ],
  "answer": "The exact correct option string",
  "explanation": "Brief explanation showing why this is correct and citing the text."
}

JSON:"""

try:
    res = llm.invoke(prompt)
    print("=== RAW RESPONSE ===")
    print(res)
except Exception as e:
    print("Error:", e)
