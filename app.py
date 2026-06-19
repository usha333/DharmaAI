"""
app.py — Streamlit frontend for DharmaAI.
Design: Spiritual, minimal, full width, no sidebar.
"""

import streamlit as st
import requests

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DharmaAI — Wisdom-based Life Guidance",
    page_icon="🕉️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide sidebar and hamburger menu completely */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Page background — warm parchment spiritual feel */
    .stApp {
        background-color: #fdf6ec;
    }

    /* Remove default padding */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 2rem;
        max-width: 750px;
    }

    /* Banner image container */
    .banner {
        width: 100%;
        height: 220px;
        background: linear-gradient(180deg, #2c1810 0%, #5c3317 50%, #8b4513 100%);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }

    .banner::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='40' fill='none' stroke='%23f0c674' stroke-width='0.3' opacity='0.3'/%3E%3Ccircle cx='50' cy='50' r='30' fill='none' stroke='%23f0c674' stroke-width='0.3' opacity='0.3'/%3E%3Ccircle cx='50' cy='50' r='20' fill='none' stroke='%23f0c674' stroke-width='0.3' opacity='0.3'/%3E%3C/svg%3E");
        background-size: 120px;
        opacity: 0.4;
    }

    .banner-om {
        font-size: 4rem;
        color: #f0c674;
        z-index: 1;
        text-shadow: 0 0 30px rgba(240,198,116,0.5);
        margin-bottom: 0.3rem;
    }

    .banner-title {
        font-size: 2rem;
        font-weight: 300;
        color: #f0c674;
        letter-spacing: 8px;
        text-transform: uppercase;
        z-index: 1;
    }

    .banner-subtitle {
        font-size: 0.8rem;
        color: #d4a96a;
        letter-spacing: 3px;
        z-index: 1;
        margin-top: 0.3rem;
    }

    /* Divider line */
    .gold-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #c9a84c, transparent);
        margin: 1.5rem 0;
    }

    /* Section label */
    .section-label {
        font-size: 0.7rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #a0845c;
        margin-bottom: 0.5rem;
    }

    /* Example buttons row */
    .stButton > button {
        background: transparent;
        border: 1px solid #c9a84c;
        color: #7a5c3a;
        border-radius: 20px;
        font-size: 0.78rem;
        padding: 0.3rem 0.8rem;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        background: #c9a84c;
        color: #fff;
        border-color: #c9a84c;
    }

    /* Main submit button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #8b4513, #c9a84c);
        color: white;
        border: none;
        border-radius: 25px;
        font-size: 1rem;
        letter-spacing: 2px;
        padding: 0.6rem 2rem;
        font-weight: 400;
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #c9a84c, #8b4513);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(201,168,76,0.4);
    }

    /* Text area */
    .stTextArea textarea {
        background: #fff9f0;
        border: 1px solid #ddc8a0;
        border-radius: 8px;
        color: #3a2a1a;
        font-size: 0.95rem;
        line-height: 1.7;
    }

    .stTextArea textarea:focus {
        border-color: #c9a84c;
        box-shadow: 0 0 0 1px #c9a84c;
    }

    /* Category badge */
    .category-badge {
        display: inline-block;
        background: #f5ead8;
        border: 1px solid #c9a84c;
        color: #7a5c3a;
        padding: 0.25rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    /* Guidance response box */
    .guidance-box {
        background: #fff9f0;
        border-left: 3px solid #c9a84c;
        border-radius: 4px;
        padding: 1.8rem 2rem;
        color: #3a2a1a;
        line-height: 1.9;
        font-size: 0.95rem;
    }

    /* Source tags */
    .source-tag {
        display: inline-block;
        background: transparent;
        border: 1px solid #ddc8a0;
        color: #a0845c;
        padding: 0.15rem 0.7rem;
        border-radius: 10px;
        font-size: 0.72rem;
        margin: 0.2rem;
        letter-spacing: 1px;
    }

    /* Stats */
    .stats-bar {
        font-size: 0.72rem;
        color: #b0946e;
        margin-top: 1rem;
        letter-spacing: 1px;
    }

    /* History section */
    .history-item {
        background: #fff9f0;
        border: 1px solid #e8d5b0;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        color: #5a4030;
    }
</style>
""", unsafe_allow_html=True)

# ── FastAPI URL ───────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000"

# ── Helper Functions ──────────────────────────────────────────────────────────
def call_guidance_api(message: str, user_name: str) -> dict:
    try:
        response = requests.post(
            f"{API_URL}/guidance",
            json={"message": message, "user_name": user_name},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to DharmaAI backend. Make sure main.py is running.")
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json().get("detail", str(e))
        raise Exception(f"API error: {error_detail}")

def format_source_name(source: str) -> str:
    return {
        "gita":        "Bhagavad Gita",
        "mahabharata": "Mahabharata",
        "meditations": "Meditations · Marcus Aurelius"
    }.get(source, source)

def format_category(category: str) -> str:
    return {
        "career":       "Career & Purpose",
        "relationship": "Relationships",
        "family":       "Family",
        "stress":       "Stress & Anxiety",
        "growth":       "Personal Growth"
    }.get(category, category)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
    <div class="banner-om">ॐ</div>
    <div class="banner-title">DharmaAI</div>
    <div class="banner-subtitle">Wisdom · Guidance · Clarity</div>
</div>
""", unsafe_allow_html=True)

# ── Intro ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#7a5c3a; font-size:0.9rem; line-height:1.8; margin-bottom:1.5rem;">
    Ancient wisdom for modern struggles.<br>
    Rooted in the Bhagavad Gita, Mahabharata, and Stoic philosophy.
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

# ── Example Prompts ───────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Begin with a situation</div>', unsafe_allow_html=True)

example_messages = [
    "Someone came into my life unexpectedly but left without reason and I feel lost",
    "I feel stuck in my career and don't know my true purpose",
    "I feel anxious all the time and can't find inner peace"
]
example_labels = ["💛 Relationship", "💼 Career", "🌊 Stress"]

selected_example = None
cols = st.columns(3)
for i, col in enumerate(cols):
    with col:
        if st.button(example_labels[i], use_container_width=True):
            selected_example = example_messages[i]

# ── Text Input ────────────────────────────────────────────────────────────────
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

if selected_example:
    st.session_state.user_input = selected_example

st.markdown("<br>", unsafe_allow_html=True)

user_message = st.text_area(
    "your_situation",
    value=st.session_state.user_input,
    placeholder="Share what's weighing on your heart — a challenge, a loss, a crossroads...",
    height=110,
    label_visibility="collapsed"
)

# ── Submit ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1.5, 2, 1.5])
with col2:
    submit = st.button("✦ Seek Wisdom ✦", use_container_width=True, type="primary")

# ── Response ──────────────────────────────────────────────────────────────────
if submit:
    if not user_message or len(user_message.strip()) < 10:
        st.warning("Please share a little more about your situation.")
    else:
        with st.spinner("Searching ancient wisdom..."):
            try:
                result = call_guidance_api(user_message, "Friend")

                st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

                # Category + sources
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(
                        f'<div class="category-badge">{format_category(result["category"])}</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    tags = " ".join([
                        f'<span class="source-tag">{format_source_name(s)}</span>'
                        for s in result["sources"]
                    ])
                    st.markdown(f'<div style="padding-top:0.3rem">{tags}</div>', unsafe_allow_html=True)

                # Guidance
                st.markdown(
                    f'<div class="guidance-box">{result["guidance"]}</div>',
                    unsafe_allow_html=True
                )

                # Stats
                st.markdown(
                    f'<div class="stats-bar">⏱ {result["processing_time"]}s &nbsp;·&nbsp; '
                    f'{result["chunks_used"]} wisdom passages retrieved</div>',
                    unsafe_allow_html=True
                )

                # Save history
                if "history" not in st.session_state:
                    st.session_state.history = []
                st.session_state.history.append({
                    "message": user_message,
                    "category": result["category"],
                    "guidance": result["guidance"]
                })

            except Exception as e:
                st.error(f"❌ {str(e)}")
                if "Cannot connect" in str(e):
                    st.code("uvicorn main:app --reload", language="bash")

# ── History ───────────────────────────────────────────────────────────────────
if "history" in st.session_state and len(st.session_state.history) > 0:
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    with st.expander(f"Past Sessions ({len(st.session_state.history)})"):
        for i, item in enumerate(reversed(st.session_state.history)):
            st.markdown(
                f'<div class="history-item"><b>{format_category(item["category"])}</b> · {item["message"][:80]}...</div>',
                unsafe_allow_html=True
            )
