"""Ollama REST API Direct Client for Jetson Orin Deployment

Endpoint: http://172.17.0.1:11434/api/generate (with localhost fallback)
Model: llama3.2:1b
Options: num_ctx=1024, num_gpu=1, use_mmap=True
"""

import os
import requests
from config import LLM_MODEL, OLLAMA_API_URL, OLLAMA_OPTIONS


def call_ollama(prompt: str, model: str = LLM_MODEL, options: dict = None) -> str:
    """Call Ollama REST API directly via requests.post matching Jetson Orin deployment template."""
    api_url = os.getenv("OLLAMA_API_URL", OLLAMA_API_URL)
    opts = options or OLLAMA_OPTIONS

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": opts
    }

    try:
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get('response', '').strip()
        else:
            # Fallback to localhost if 172.17.0.1 is unreachable
            if "172.17.0.1" in api_url:
                local_url = "http://localhost:11434/api/generate"
                res_fallback = requests.post(local_url, json=payload, timeout=60)
                if res_fallback.status_code == 200:
                    return res_fallback.json().get('response', '').strip()
            print(f"Error {response.status_code}: {response.text}")
            return ""
    except requests.exceptions.RequestException as e:
        if "172.17.0.1" in api_url:
            try:
                local_url = "http://localhost:11434/api/generate"
                res_fallback = requests.post(local_url, json=payload, timeout=60)
                if res_fallback.status_code == 200:
                    return res_fallback.json().get('response', '').strip()
            except Exception:
                pass
        print(f"Connection Error: {e}")
        return ""
