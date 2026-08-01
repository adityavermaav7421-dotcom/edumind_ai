import os
os.environ["TZ"] = "UTC"
import re
import streamlit as st

# Set page config FIRST before any other streamlit calls
st.set_page_config(
    page_title="EDUMIND: Intelligent Document Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

from rag_engine import RAGEngine
from notes_generator import NotesGenerator
from quiz_generator_v2 import QuizGeneratorV2
from config import MAX_QUESTIONS

# Load Custom CSS
def load_css(css_file_path: str):
    if os.path.exists(css_file_path):
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(os.path.join(os.path.dirname(__file__), "style.css"))

# Initialize Session State
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine(llm_model="llama3.2:1b", embed_model="nomic-embed-text")

if "notes_gen" not in st.session_state:
    st.session_state.notes_gen = NotesGenerator(llm_model="llama3.2:1b")

if "quiz_gen" not in st.session_state:
    st.session_state.quiz_gen = QuizGeneratorV2()

if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []  # List of raw Document objects

if "doc_metas" not in st.session_state:
    st.session_state.doc_metas = []  # Metadata dicts per uploaded file

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "generated_notes" not in st.session_state:
    st.session_state.generated_notes = None

if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

if "quiz_user_answers" not in st.session_state:
    st.session_state.quiz_user_answers = {}

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("## 🧠 EDUMIND")
    st.markdown("<span class='badge-tag green'>100% Local (Ollama llama3.2:1b)</span> <span class='badge-tag purple'>Zero API Calls</span> <span class='badge-tag blue'>Max 20MB File</span>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📁 Upload Documents")
    st.caption("🔒 Document Processing Limits:\n- File size: **Max 20 MB**\n- Supported formats: **PDF, DOC/DOCX, TXT**\n- Pages per file: **All Pages Indexed (100% Local)**")
    
    uploaded_files = st.file_uploader(
        "Upload PDF, Word, or TXT (< 20MB)",
        type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:
        new_files_detected = False
        existing_names = [m["filename"] for m in st.session_state.doc_metas]
        
        for file in uploaded_files:
            if file.name not in existing_names:
                # Check File Size Limit (20 MB)
                file_bytes = file.read()
                file_size_mb = len(file_bytes) / (1024 * 1024)
                
                if file_size_mb > 20.0:
                    st.error(f"❌ '{file.name}' ({file_size_mb:.1f} MB) exceeds the 20 MB size limit for high-accuracy local processing.")
                    continue

                with st.spinner(f"Parsing & indexing '{file.name}'..."):
                    try:
                        # Ensure RAGEngine instance is up to date
                        st.session_state.rag_engine = RAGEngine(llm_model="llama3.2:1b", embed_model="nomic-embed-text")
                        docs, meta = st.session_state.rag_engine.process_uploaded_file(file_bytes, file.name, max_size_mb=20.0)
                        st.session_state.processed_docs.extend(docs)
                        st.session_state.doc_metas.append(meta)
                        new_files_detected = True
                    except Exception as e:
                        st.error(f"Error processing '{file.name}': {str(e)}")

        if new_files_detected:
            with st.spinner("Building FAISS Vector Index..."):
                chunk_count = st.session_state.rag_engine.build_vector_store(st.session_state.processed_docs)
                st.success(f"Indexed {len(st.session_state.doc_metas)} documents into {chunk_count} precise vector chunks!")

    st.markdown("---")
    st.subheader("📊 Document Statistics")
    
    if st.session_state.doc_metas:
        total_pages = sum(m.get("indexed_pages", m.get("total_pages", 0)) for m in st.session_state.doc_metas)
        total_words = sum(m.get("total_words", 0) for m in st.session_state.doc_metas)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='stat-card'><div class='stat-value'>{total_pages}</div><div class='stat-label'>Indexed Pages</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='stat-card'><div class='stat-value'>{total_words}</div><div class='stat-label'>Total Words</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Loaded Files:**")
        for m in st.session_state.doc_metas:
            pgs = m.get('indexed_pages', m.get('total_pages', 1))
            size = m.get('size_mb', 0.1)
            st.markdown(f"- 📄 `{m.get('filename', 'document')}` ({pgs} pgs / {size}MB)")
    else:
        st.info("No documents uploaded yet. Upload a file above to get started.")

    st.markdown("---")
    st.markdown("⚙️ **Engine Accuracy Config**")
    st.markdown("- **LLM**: Ollama `llama3.2:1b` (100% Local)\n- **Chunk Size**: 400 chars\n- **Page Range Window**: 1-10 pages max")
    
    if st.button("🗑️ Clear All Documents & Reset"):
        st.session_state.processed_docs = []
        st.session_state.doc_metas = []
        st.session_state.chat_history = []
        st.session_state.generated_notes = None
        st.session_state.current_quiz = None
        st.session_state.rag_engine.vector_store = None
        st.rerun()


# ---------------- MAIN APP HEADER ----------------
st.markdown("""
<div class='edumind-header'>
    <h1 class='edumind-title'>EDUMIND : Intelligent Document Brain</h1>
    <p class='edumind-subtitle'>High-Accuracy RAG Chatbot, Page-Range Short Notes & Practice Quizzes — Powered 100% locally by Ollama llama3.2:1b.</p>
</div>
""", unsafe_allow_html=True)


# ---------------- TABS NAVIGATION ----------------
tab_chat, tab_notes, tab_quiz = st.tabs([
    "💬 RAG Chatbot & Citations",
    "📝 Short Notes (Max 10-Page Window)",
    "🧪 Practice Quiz (Max 10-Page Window)"
])


# ==============================================================================
# TAB 1: RAG CHATBOT
# ==============================================================================
with tab_chat:
    st.subheader("💬 Ask Questions About Your Documents")
    st.caption("Answers include exact page number citations and source snippets from your uploaded files.")

    if not st.session_state.processed_docs:
        st.warning("⚠️ Please upload at least one document in the sidebar to activate the Chatbot.")
    else:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    if "sources" in msg and msg["sources"]:
                        with st.expander("📚 View Document Citations & Context Snippets"):
                            for s in msg["sources"]:
                                st.markdown(f"**[Source {s['id']}]** `{s['source']}` — Page {s['page']}")
                                st.caption(s["snippet"])
                                st.markdown("---")

        user_input = st.chat_input("Ask anything about your uploaded documents...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking & searching document context..."):
                    res = st.session_state.rag_engine.query(user_input, top_k=3)
                    answer_text = res["answer"]
                    sources = res["sources"]

                    st.markdown(answer_text)
                    if sources:
                        with st.expander("📚 View Document Citations & Context Snippets"):
                            for s in sources:
                                st.markdown(f"**[Source {s['id']}]** `{s['source']}` — Page {s['page']}")
                                st.caption(s["snippet"])
                                st.markdown("---")

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer_text,
                "sources": sources
            })


# ==============================================================================
# TAB 2: SHORT NOTES GENERATOR WITH PAGE RANGE (MAX 10 PAGES)
# ==============================================================================
with tab_notes:
    st.subheader("📝 Generate Concise Short Notes & Summaries")
    st.caption("💡 Page ranges are capped at 10 pages per batch to guarantee high accuracy with Ollama 3.2:1b.")

    if not st.session_state.processed_docs:
        st.warning("⚠️ Please upload at least one document in the sidebar to generate notes.")
    else:
        doc_options = ["All Uploaded Documents"] + [m.get("filename", f"Doc {i+1}") for i, m in enumerate(st.session_state.doc_metas)]
        selected_notes_doc = st.selectbox("🎯 Target Document for Notes", doc_options, key="notes_doc_select")

        if selected_notes_doc == "All Uploaded Documents":
            active_docs = st.session_state.processed_docs
        else:
            active_docs = [d for d in st.session_state.processed_docs if d.metadata.get("source") == selected_notes_doc]

        total_p = max(1, max((d.metadata.get("page", 1) for d in active_docs), default=1))
        max_page = total_p

        col_p1, col_p2, col_style = st.columns([1, 1, 1])

        with col_p1:
            start_p = st.number_input("Start Page", min_value=1, max_value=max_page, value=1, step=1, key="notes_start_p")

        with col_p2:
            max_allowed_end = min(start_p + 9, max_page)
            end_p = st.number_input("End Page (Max 10 pgs)", min_value=start_p, max_value=max_allowed_end, value=max_allowed_end, step=1, key="notes_end_p")

        with col_style:
            note_style = st.selectbox(
                "Format Style",
                ["Bullet Points", "Core Concepts", "Mind-Map Breakdown", "Executive Summary"]
            )
            custom_topic = st.text_input("Topic Focus (Optional)", placeholder="e.g. Chapter 2, Neural Networks")

        st.info(f"Target Scope: **{selected_notes_doc} — Pages {start_p} to {end_p}** ({end_p - start_p + 1} pages selected)")

        if st.button("✨ Generate Short Notes", type="primary"):
            with st.spinner(f"Generating '{note_style}' notes for Pages {start_p} to {end_p}..."):
                res = st.session_state.notes_gen.generate_notes(
                    documents=active_docs,
                    start_page=start_p,
                    end_page=end_p,
                    style=note_style,
                    custom_topic=custom_topic
                )
                st.session_state.generated_notes = res

        if st.session_state.generated_notes:
            res = st.session_state.generated_notes
            if res.get("success"):
                st.markdown("---")
                st.markdown(f"### 📋 Generated Notes ({res['style']} — {res['range']})")
                st.markdown(res["notes"])
                
                st.download_button(
                    label="📥 Download Notes (.md)",
                    data=res["notes"],
                    file_name=f"EDUMIND_Notes_Pages_{start_p}_to_{end_p}.md",
                    mime="text/markdown"
                )
            else:
                st.error(res.get("notes"))


# ==============================================================================
# TAB 3: INTERACTIVE QUIZ GENERATOR (MAX 10 PAGES)
# ==============================================================================
with tab_quiz:
    st.subheader("🧪 Interactive Practice Quiz Generator")

    if not st.session_state.processed_docs:
        st.warning("⚠️ Please upload at least one document in the sidebar to generate practice quizzes.")
    else:
        doc_filenames = [m.get("filename", f"Doc {i+1}") for i, m in enumerate(st.session_state.doc_metas)]
        doc_options_quiz = doc_filenames + ["All Uploaded Documents"]
        selected_quiz_doc = st.selectbox("🎯 Target Document for Quiz", doc_options_quiz, key="quiz_doc_select")

        if selected_quiz_doc == "All Uploaded Documents":
            active_quiz_docs = st.session_state.processed_docs
        else:
            active_quiz_docs = [d for d in st.session_state.processed_docs if d.metadata.get("source") == selected_quiz_doc]

        total_p_quiz = max(1, max((d.metadata.get("page", 1) for d in active_quiz_docs), default=1))
        max_page_quiz = total_p_quiz

        col_q1, col_q2 = st.columns([1, 1])

        with col_q1:
            num_q = st.slider("Number of Questions", min_value=1, max_value=10, value=5)

        with col_q2:
            quiz_topic = st.text_input("Quiz Topic / Focus (Optional)", placeholder="Full Document or specific topic/chapter")

        col_qp1, col_qp2 = st.columns([1, 1])
        with col_qp1:
            q_start = st.number_input("Quiz Start Page", min_value=1, max_value=max_page_quiz, value=1, step=1, key="q_start_input")
        with col_qp2:
            q_max_end = min(q_start + 9, max_page_quiz)
            q_end = st.number_input("Quiz End Page (Max 10 pgs)", min_value=q_start, max_value=q_max_end, value=q_max_end, step=1, key="q_end_input")

        st.info(f"Quiz Target Scope: **{selected_quiz_doc} — Pages {q_start} to {q_end}** ({q_end - q_start + 1} pages selected)")

        if st.button("🚀 Generate Quiz", type="primary"):
            with st.spinner(f"Generating {num_q} university conceptual questions for Pages {q_start} to {q_end}..."):
                # Use the pre-initialized QuizGeneratorV2 instance
                quiz_data = st.session_state.quiz_gen.generate_quiz(
                    documents=active_quiz_docs,
                    num_questions=num_q,
                    topic=quiz_topic,
                    start_page=q_start,
                    end_page=q_end
                )
                import time
                st.session_state.current_quiz = quiz_data
                st.session_state.quiz_id = f"quiz_form_{int(time.time())}"
                st.session_state.quiz_submitted = False
                st.session_state.quiz_user_answers = {}

        if st.session_state.current_quiz:
            quiz = st.session_state.current_quiz

            if not quiz.get("success"):
                st.error(f"⚠️ {quiz.get('error', 'Quiz generation failed.')}")
            else:
                questions = quiz.get("questions", [])
                if not questions:
                    st.warning("⚠️ No valid conceptual questions could be generated. Try a wider page range or different topic.")
                else:
                    quiz_form_key = st.session_state.get("quiz_id", "quiz_form_default")
                    st.markdown("---")
                    st.markdown(f"### ✏️ Practice Quiz: Test Your Notes Understanding ({quiz.get('range', '')} — {len(questions)} Questions)")

                    with st.form(key=quiz_form_key):
                        for idx, q in enumerate(questions):
                            q_text = str(q.get('question', '')).strip()

                            st.markdown(
                                f"""<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px; padding: 16px 20px; margin-bottom: 24px;">
                                    <div style="background: #64748b; color: #ffffff; font-size: 1.15rem; font-weight: 700; padding: 18px 24px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);">
                                        Q{idx+1}. {q_text}
                                    </div>""",
                                unsafe_allow_html=True
                            )

                            opts = q.get("options", [])
                            if isinstance(opts, dict):
                                opts = list(opts.values())
                            display_options = [str(o).strip() for o in opts if str(o).strip()]

                            ans_key = f"q_{q['id']}"
                            selected_choice = st.radio(
                                f"Select choice for Q{idx+1}:",
                                options=display_options,
                                key=ans_key,
                                index=None
                            )
                            st.session_state.quiz_user_answers[q['id']] = selected_choice

                            st.markdown("</div>", unsafe_allow_html=True)

                        submit_btn = st.form_submit_button("🏆 Submit Answers & Get Score", type="primary")

                    if submit_btn:
                        st.session_state.quiz_submitted = True

                    if st.session_state.quiz_submitted:
                        st.markdown("---")
                        st.markdown("### 📊 Quiz Results & Feedback")

                        correct_count = 0
                        for q in questions:
                            user_choice = st.session_state.quiz_user_answers.get(q['id'])
                            correct_ans = str(q.get("answer", "")).strip()
                            q_text = str(q.get('question', '')).strip()

                            is_correct = False
                            if user_choice and correct_ans:
                                # Normalize for comparison
                                u = re.sub(r'[^\w\s]', '', user_choice).strip().lower()
                                c = re.sub(r'[^\w\s]', '', correct_ans).strip().lower()
                                is_correct = (u == c)

                            if is_correct:
                                correct_count += 1
                                st.markdown(f"**Q{q['id']}: {q_text}**")
                                st.markdown(f"- **Your Answer:** `{user_choice}`")
                                st.markdown(f"- **Correct Answer:** `{correct_ans}`")
                                st.markdown(f"<div class='quiz-result-correct'>Correct! {q.get('explanation', '')}</div>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**Q{q['id']}: {q_text}**")
                                st.markdown(f"- **Your Answer:** `{user_choice if user_choice else 'Not answered'}`")
                                st.markdown(f"- **Correct Answer:** `{correct_ans}`")
                                st.markdown(f"<div class='quiz-result-incorrect'>Incorrect. {q.get('explanation', '')}</div>", unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True)

                        score_pct = int(round((correct_count / len(questions)) * 100)) if questions else 0
                        st.metric("Final Score", f"{correct_count} / {len(questions)} ({score_pct}%)")

                        if score_pct >= 80:
                            st.balloons()
                            st.success("Excellent work! You mastered this topic!")
                        elif score_pct >= 50:
                            st.info("Good effort! Review the notes and try again to improve.")
                        else:
                            st.warning("Keep practicing! Try generating short notes for this range first.")


