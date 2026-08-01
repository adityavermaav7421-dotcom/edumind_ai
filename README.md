# 🧠 EDUMIND: Intelligent Document Brain & Study Companion

> **100% Privacy-First, Offline RAG Chatbot, Page-Window Short Notes Generator, & Practice Quiz Engine — Powered locally by Ollama (`llama3.2:1b`).**

---

## 🌟 Key Features

- **💬 High-Accuracy RAG Chatbot**: Upload PDFs, Word docs, TXT, or images and ask questions with exact page-number citations and source context snippets.
- **📝 Short Notes Generator**: Select any 10-page window from your documents to generate structured chapter summaries, bullet points, and key concepts.
- **🧪 Interactive Practice Quiz Generator**: Automatically builds 4-option MCQs and True/False practice quizzes from selected page ranges.
- **⚡ Zero Position Bias & Guaranteed Unique Options**: Advanced option deduplication and random answer placement across A, B, C, and D.
- **🛡️ 100% Local & Free Execution**: Runs entirely on your local machine using Ollama. No external API keys or cloud services required.
- **🟢 Edge Compatible**: Optimized for NVIDIA Jetson (Orin Nano / Xavier NX / AGX Orin), PCs, and Macs.

---

## 🏗️ Architecture Stack

- **Frontend & UI**: Streamlit with custom CSS styling
- **LLM Engine**: Ollama (`llama3.2:1b`)
- **Embeddings**: In-Memory HuggingFace Embeddings (`all-MiniLM-L6-v2`)
- **Vector Search**: FAISS (Facebook AI Similarity Search)
- **Document Extractors**: PyPDF, pdfplumber, python-docx, PyTesseract (OCR fallback)

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Install [Ollama](https://ollama.com/download) and pull the lightweight 1B model:
```bash
ollama pull llama3.2:1b
```

### 2. Clone Repository & Install Dependencies
```bash
git clone https://github.com/YOUR_USERNAME/EDUMIND.git
cd EDUMIND

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Launch Application
```bash
python -m streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501`** in your browser.

---

## 🟢 Deployment Options

- **Local Network Sharing (Wi-Fi / LAN)**:
  ```bash
  python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
  ```
- **NVIDIA Jetson Setup**: Maximize Jetson clocks (`sudo nvpmodel -m 0 && sudo jetson_clocks`), install Ollama ARM64, and launch.

---

## 📜 License
MIT License. Free for personal, academic, and open-source use.
