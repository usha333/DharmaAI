"""
app.py — Streamlit chat interface for DharmaAI.
A real conversation with memory, not single question/answer.
"""

import streamlit as st
import requests

st.set_page_config(
    page_title="DharmaAI — Your Wisdom Guide",
    page_icon="🪷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #fdf6ec;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220' viewBox='0 0 220 220'%3E%3Cg fill='none' stroke='%23c9962f' stroke-width='1' opacity='0.18'%3E%3Ccircle cx='110' cy='110' r='100'/%3E%3Ccircle cx='110' cy='110' r='80'/%3E%3Ccircle cx='110' cy='110' r='60'/%3E%3Ccircle cx='110' cy='110' r='40'/%3E%3Ccircle cx='110' cy='110' r='20'/%3E%3Cpath d='M110 10 L110 210 M10 110 L210 110 M39.6 39.6 L180.4 180.4 M39.6 180.4 L180.4 39.6'/%3E%3Cpath d='M110 30 A80 80 0 0 1 178 70 A80 80 0 0 1 178 150 A80 80 0 0 1 110 190 A80 80 0 0 1 42 150 A80 80 0 0 1 42 70 A80 80 0 0 1 110 30 Z'/%3E%3C/g%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 220px 220px;
        background-attachment: fixed;
    }

    .block-container {
        padding-top: 0rem;
        padding-bottom: 6rem;
        max-width: 750px;
    }

    .banner {
        width: 100%;
        height: 220px;
        position: relative;
        overflow: hidden;
        margin-bottom: 1.5rem;
        border-radius: 0 0 16px 16px;
        background: linear-gradient(160deg, #8a5a1f 0%, #c9962f 45%, #e8c376 100%);
    }
    .banner-mandala {
        position: absolute;
        top: 50%; left: 50%;
        width: 480px; height: 480px;
        transform: translate(-50%, -50%);
        opacity: 0.5;
        animation: spin 120s linear infinite;
    }
    @keyframes spin {
        from { transform: translate(-50%, -50%) rotate(0deg); }
        to { transform: translate(-50%, -50%) rotate(360deg); }
    }
    .banner-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle at center, rgba(138,90,31,0.12) 0%, rgba(74,45,10,0.5) 100%);
    }
    .banner-om {
        font-size: 2.8rem;
        color: #f0c674;
        text-shadow: 0 0 30px rgba(240,198,116,0.8);
        line-height: 1;
    }
    .banner-title {
        font-size: 1.8rem;
        font-weight: 300;
        color: #fdf0d8;
        letter-spacing: 9px;
        text-transform: uppercase;
        margin-top: 0.4rem;
    }
    .banner-subtitle {
        font-size: 0.72rem;
        color: #f0d9a8;
        letter-spacing: 3px;
        margin-top: 0.3rem;
        text-transform: uppercase;
    }

    .chat-user {
        background: linear-gradient(135deg, #c9962f, #a8731f);
        color: #fffaf0;
        padding: 0.85rem 1.3rem;
        border-radius: 20px 20px 4px 20px;
        margin: 0.7rem 0 0.7rem auto;
        max-width: 75%;
        font-size: 0.92rem;
        line-height: 1.65;
        box-shadow: 0 2px 10px rgba(180,134,46,0.25);
    }
    .chat-user-wrap { display: flex; justify-content: flex-end; }

    .chat-dharmaai {
        background: rgba(255, 252, 245, 0.92);
        backdrop-filter: blur(2px);
        border: 1px solid #ecdcb0;
        color: #4a3a1f;
        padding: 1.1rem 1.4rem;
        border-radius: 20px 20px 20px 4px;
        margin: 0.7rem auto 0.7rem 0;
        max-width: 85%;
        font-size: 0.9rem;
        line-height: 1.8;
        box-shadow: 0 2px 12px rgba(201,150,47,0.12);
    }
    .chat-dharmaai-wrap { display: flex; justify-content: flex-start; }

    .chat-label {
        font-size: 0.68rem;
        color: #b8924f;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
        font-weight: 600;
    }

    .source-tag {
        display: inline-block;
        border: 1px solid #e3cf95;
        background: #faf0da;
        color: #9a7a3a;
        padding: 0.15rem 0.65rem;
        border-radius: 12px;
        font-size: 0.68rem;
        margin: 0.2rem 0.2rem 0 0;
    }

    .gold-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #c9962f, transparent);
        margin: 1.4rem 0;
    }

    .stButton > button {
        background: transparent;
        border: 1px solid #c9962f;
        color: #8a5a1f;
        border-radius: 20px;
        font-size: 0.78rem;
        padding: 0.4rem 0.9rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #c9962f, #a8731f);
        color: #fff;
        border-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"


# ── Helpers ────────────────────────────────────────────────────────────────────
def call_guidance_api(message: str, chat_history: list) -> dict:
    try:
        response = requests.post(
            f"{API_URL}/guidance",
            json={"message": message, "user_name": "Friend", "chat_history": chat_history},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to DharmaAI backend. Run: uvicorn main:app --reload")
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e))
        raise Exception(f"API error: {detail}")

def format_source_name(source):
    return {
        "gita": "Bhagavad Gita",
        "mahabharata": "Mahabharata",
        "meditations": "Meditations · Marcus Aurelius"
    }.get(source, source)

def format_category(category):
    return {
        "career": "Career & Purpose",
        "relationship": "Relationships",
        "family": "Family",
        "stress": "Stress & Anxiety",
        "growth": "Personal Growth",
        "casual": ""
    }.get(category, category)


# ── Banner ────────────────────────────────────────────────────────────────────
MANDALA_SVG = (
    '<svg class="banner-mandala" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">'
    '<g fill="none" stroke="#fdeec2" stroke-width="1.2" opacity="0.85">'
    '<circle cx="200" cy="200" r="180"/><circle cx="200" cy="200" r="150"/>'
    '<circle cx="200" cy="200" r="120"/><circle cx="200" cy="200" r="90"/>'
    '<circle cx="200" cy="200" r="60"/><circle cx="200" cy="200" r="30"/>'
    '</g>'
    '<g fill="none" stroke="#fff6dd" stroke-width="1" opacity="0.6">'
    '<g id="petals1"><path d="M200 50 Q230 100 200 140 Q170 100 200 50 Z"/></g>'
    '<use href="#petals1" transform="rotate(30 200 200)"/>'
    '<use href="#petals1" transform="rotate(60 200 200)"/>'
    '<use href="#petals1" transform="rotate(90 200 200)"/>'
    '<use href="#petals1" transform="rotate(120 200 200)"/>'
    '<use href="#petals1" transform="rotate(150 200 200)"/>'
    '<use href="#petals1" transform="rotate(180 200 200)"/>'
    '<use href="#petals1" transform="rotate(210 200 200)"/>'
    '<use href="#petals1" transform="rotate(240 200 200)"/>'
    '<use href="#petals1" transform="rotate(270 200 200)"/>'
    '<use href="#petals1" transform="rotate(300 200 200)"/>'
    '<use href="#petals1" transform="rotate(330 200 200)"/>'
    '</g>'
    '<g fill="none" stroke="#fdeec2" stroke-width="1" opacity="0.5">'
    '<g id="petals2"><path d="M200 80 Q220 120 200 160 Q180 120 200 80 Z"/></g>'
    '<use href="#petals2" transform="rotate(22.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(45 200 200)"/>'
    '<use href="#petals2" transform="rotate(67.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(90 200 200)"/>'
    '<use href="#petals2" transform="rotate(112.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(135 200 200)"/>'
    '<use href="#petals2" transform="rotate(157.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(180 200 200)"/>'
    '<use href="#petals2" transform="rotate(202.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(225 200 200)"/>'
    '<use href="#petals2" transform="rotate(247.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(270 200 200)"/>'
    '<use href="#petals2" transform="rotate(292.5 200 200)"/>'
    '<use href="#petals2" transform="rotate(315 200 200)"/>'
    '<use href="#petals2" transform="rotate(337.5 200 200)"/>'
    '</g>'
    '<circle cx="200" cy="200" r="8" fill="#fff6dd" opacity="0.9"/>'
    '</svg>'
)

banner_html = (
    f'<div class="banner">{MANDALA_SVG}'
    f'<div class="banner-overlay"><div class="banner-om">ॐ</div></div>'
    f'</div>'
)
st.markdown(banner_html, unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "dharmaai",
        "content": "Namaste 🙏 I'm here to listen. Share what's on your mind — a challenge, a feeling, or simply say hello.",
        "category": "casual",
        "sources": []
    }]

# ── Render Chat History ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user-wrap"><div class="chat-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        sources_html = ""
        if msg.get("sources"):
            tags = " ".join([f'<span class="source-tag">{format_source_name(s)}</span>' for s in msg["sources"]])
            sources_html = f'<div style="margin-top:0.7rem">{tags}</div>'

        label = ""
        cat_label = format_category(msg.get("category", ""))
        if cat_label:
            label = f'<div class="chat-label">{cat_label}</div>'

        st.markdown(
            f'<div class="chat-dharmaai-wrap"><div class="chat-dharmaai">{label}{msg["content"]}{sources_html}</div></div>',
            unsafe_allow_html=True
        )

# ── Quick-start suggestions (first message only) ──────────────────────────────
clicked = None
if len(st.session_state.messages) == 1:
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    suggestions = [
        ("💛 Relationship", "Someone came into my life unexpectedly but left without reason and I feel lost"),
        ("🌸 Career", "I feel stuck in my career and don't know my true purpose"),
        ("🌞 Stress", "I feel anxious all the time and can't find inner peace")
    ]
    for col, (label, text) in zip(cols, suggestions):
        with col:
            if st.button(label, use_container_width=True):
                clicked = text

# ── Chat Input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Share what's on your mind...")
final_input = user_input or clicked

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})

    history_payload = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.spinner("Reflecting..."):
        try:
            result = call_guidance_api(final_input, history_payload)
            st.session_state.messages.append({
                "role": "dharmaai",
                "content": result["guidance"],
                "category": result["category"],
                "sources": result["sources"]
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "dharmaai",
                "content": f"⚠️ {str(e)}",
                "category": "casual",
                "sources": []
            })

    st.rerun()

# ── Reset ─────────────────────────────────────────────────────────────────────
if len(st.session_state.messages) > 1:
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    if st.button("🔄 Start New Conversation"):
        st.session_state.messages = []
        st.rerun()
