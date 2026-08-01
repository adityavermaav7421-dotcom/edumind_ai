# 🚀 EDUMIND Deployment Guide — Jetson Orin Board

This document provides complete instructions for deploying **EDUMIND: Intelligent Document Brain** on the **NVIDIA Jetson Orin** edge board.

---

## 📌 1. Hardware & System Requirements

- **Device**: NVIDIA Jetson Orin Board (Orin Nano / Orin NX / AGX Orin)
- **Model**: `llama3.2:1b` (**Mandatory fixed SLM model — 100% Local**)
- **Ollama REST API Endpoint**: `http://172.17.0.1:11434/api/generate`
- **Memory Optimization Options**:
  - `num_ctx`: `1024` (reduces RAM usage by ~500 MB)
  - `num_gpu`: `1` (utilizes Jetson Orin GPU accelerator)
  - `use_mmap`: `true` (memory-mapped loading)

---

## ⚙️ 2. Ollama REST API Integration Specification

All LLM calls within EDUMIND use the lightweight Python `requests` library directly, matching the official Jetson Orin payload structure without heavy SDK wrappers.

### Python Integration Snippet (`ollama_client.py`):
```python
import requests

API_URL = "http://172.17.0.1:11434/api/generate"

prompt = "Explain how backpropagation works in one paragraph."

payload = {
    "model": "llama3.2:1b",          # Only approved model for Jetson deployment
    "prompt": prompt,
    "stream": False,
    "options": {
        "num_ctx": 1024,           # Keep context small — saves ~500 MB RAM
        "num_gpu": 1,              # 1 GPU device on Jetson Orin
        "use_mmap": True           # Memory-mapped loading for Jetson
    }
}

try:
    response = requests.post(API_URL, json=payload, timeout=60)
    if response.status_code == 200:
        print(response.json()['response'])
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Connection Error: {e}")
```

---

## 📦 3. Prerequisites & Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/edumind.git
cd edumind
```

### Step 2: Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## 🏃 4. Running the Application on Jetson Board

### Set Environment Variables (Optional override if running outside default bridge network):
```bash
export OLLAMA_API_URL="http://172.17.0.1:11434/api/generate"
```

### Launch Streamlit App:
```bash
streamlit run app.py --server.port 8505 --server.address 0.0.0.0
```

Once running, access the web interface from any browser on the network at:
`http://<JETSON_IP_ADDRESS>:8505`

---

## 🧪 5. Architecture Summary

| Component | Technology | Jetson Board Optimization |
|---|---|---|
| **SLM Model** | Ollama `llama3.2:1b` | 100% local, `num_ctx=1024`, `use_mmap=True` |
| **API Client** | Direct `requests` REST calls | 0 SDK dependencies, identical laptop/board payload |
| **RAG Vector Index** | FAISS + In-Memory Embeddings | High-speed 400-char chunking |
| **Notes Engine** | Page-Range Short Notes (Max 10 Pgs) | Strict page bounds + fallback support |
| **Quiz Generator** | Two-Stage `ThinkEngine` + `TemplateEngine` | 0 scenario noise, 100% document ground-truth |
