"""Configuration constants for EduMind Jetson deployment"""
import os

# Model to use for all LLM calls (Jetson requirement: llama3.2:1b only)
LLM_MODEL = "llama3.2:1b"

# Ollama REST API Endpoint for Jetson board deployment
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://172.17.0.1:11434/api/generate")

# Jetson Orin memory-optimized options payload
OLLAMA_OPTIONS = {
    "num_ctx": 1024,   # Keep context small — saves ~500 MB RAM
    "num_gpu": 1,      # 1 GPU device on Jetson Orin
    "use_mmap": True   # Memory-mapped loading for Jetson
}

# Maximum character length for generated sentences / options
MAX_CHAR_LIMIT = 600

# Maximum number of questions per quiz (slider limit)
MAX_QUESTIONS = 10
