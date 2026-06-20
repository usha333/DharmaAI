"""
rag_core.py — Plain Python RAG pipeline for DharmaAI.

Pipeline:
0. Check if message is casual chat or a real situation
1. Classify intent (career/relationship/family/stress/growth)
2. Retrieve relevant wisdom chunks from ChromaDB (dual-query)
3. Build prompt with retrieved wisdom + conversation history
4. Generate structured guidance with Gemini

Model: gemini-2.5-flash-lite — chosen for its generous free-tier daily
quota (~1000/day) compared to gemini-2.5-flash (~20/day). Since each
user message can require 2-3 API calls (casual check, classify, generate),
quota efficiency matters a lot during development and testing.
"""

import os
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ── Load API key ─────────────────────────────────────────────────────────────
load_dotenv()
client_ai = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── Connect to ChromaDB (already populated by ingest.py) ─────────────────────
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection("dharmaai")
print(f"Connected to ChromaDB — {collection.count()} chunks available")

# Model used for all text generation in this file
GEN_MODEL = "gemini-2.5-flash-lite"
EMBED_MODEL = "gemini-embedding-001"


# ── STEP 0: CASUAL MESSAGE DETECTION ─────────────────────────────────────────
def is_casual_message(user_message):
    """
    Detect if this is small talk (greeting, thanks, introducing themselves)
    rather than a genuine life situation needing wisdom-based guidance.

    Without this check, "hi" would trigger the full RAG pipeline and come
    back as a formal 5-section structured response — which feels robotic.
    A real guru responds to "hello" warmly, not with a sermon.
    """
    check_prompt = f"""
Is this message casual small talk (greeting, thanks, goodbye, "how are you",
introducing themselves) OR a genuine life situation/problem seeking guidance?

Message: "{user_message}"

Reply with ONLY one word: "casual" or "situation"
"""
    response = client_ai.models.generate_content(
        model=GEN_MODEL,
        contents=check_prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=10,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    )
    return "casual" in response.text.strip().lower()


def generate_casual_reply(user_message, chat_history):
    """
    Generate a warm, brief, guru-like reply for small talk.
    Uses chat_history so it doesn't repeat itself (e.g. asking your name twice).
    """
    history_text = ""
    if chat_history:
        for turn in chat_history[-6:]:
            history_text += f"{turn['role']}: {turn['content']}\n"

    prompt = f"""
You are DharmaAI — a warm, wise guide rooted in dharmic philosophy.
Someone is making casual conversation, not asking for deep guidance yet.

Respond briefly and warmly, like a wise teacher greeting a student —
no headers, no bullet points, no formal structure. 1-3 sentences max.
You may gently invite them to share what's on their mind, but don't force it.
If they already told you their name earlier, use it naturally.

Conversation so far:
{history_text if history_text else "(this is the first message)"}

Their message: "{user_message}"

Your reply:
"""
    response = client_ai.models.generate_content(
        model=GEN_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=150,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    )
    return response.text.strip()


# ── STEP 1: INTENT CLASSIFICATION ────────────────────────────────────────────
def classify_intent(user_message):
    """Classify the user's message into one of 5 life categories."""

    classification_prompt = f"""
You are a life situation classifier for DharmaAI, a wisdom-based guidance system.

Classify the user's message into EXACTLY ONE of these categories:
- career: work, job, purpose, ambition, success, failure, direction
- relationship: romantic relationships, heartbreak, loneliness, attachment, love
- family: parents, siblings, children, family conflict, expectations
- stress: anxiety, overwhelm, mental health, burnout, fear, worry
- growth: self-improvement, habits, meaning, identity, spiritual seeking

Examples:
"I lost my job and don't know what to do" → career
"Someone I loved left me without explanation" → relationship
"My parents don't understand my choices" → family
"I feel anxious all the time and can't sleep" → stress
"I want to become a better person but don't know how" → growth

User message: "{user_message}"

Reply with ONLY the category word. Nothing else.
"""
    response = client_ai.models.generate_content(
        model=GEN_MODEL,
        contents=classification_prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=10,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    )

    category = response.text.strip().lower().replace(".", "").replace("\n", "")
    valid_categories = ["career", "relationship", "family", "stress", "growth"]
    return category if category in valid_categories else "stress"


# ── STEP 2: RETRIEVAL ─────────────────────────────────────────────────────────
def retrieve_wisdom(user_message, category, n_results=5):
    """
    Search ChromaDB for relevant wisdom chunks using dual-query retrieval.

    We search twice — once with the user's exact words, once with
    category-specific keywords — because the user's vocabulary often
    differs from the source text's vocabulary. E.g. user says "he left me",
    Gita talks about "attachment and impermanence". Merging both searches
    catches relevant chunks that a single search would miss.
    """
    category_context = {
        "career":       "duty work purpose action karma yoga dharma profession",
        "relationship": "attachment love loss letting go impermanence karmic bond",
        "family":       "duty family dharma obligation respect relationships bonds",
        "stress":       "fear anxiety mind peace equanimity suffering acceptance",
        "growth":       "self knowledge wisdom spiritual growth transformation soul"
    }

    user_embedding = client_ai.models.embed_content(
        model=EMBED_MODEL,
        contents=user_message,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    ).embeddings[0].values

    context_embedding = client_ai.models.embed_content(
        model=EMBED_MODEL,
        contents=category_context[category],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    ).embeddings[0].values

    results_user = collection.query(
        query_embeddings=[user_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    results_context = collection.query(
        query_embeddings=[context_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    combined = {}
    for doc, meta, dist in zip(results_user["documents"][0], results_user["metadatas"][0], results_user["distances"][0]):
        combined[doc[:50]] = {"text": doc, "source": meta["source"], "distance": dist}
    for doc, meta, dist in zip(results_context["documents"][0], results_context["metadatas"][0], results_context["distances"][0]):
        key = doc[:50]
        if key not in combined:
            combined[key] = {"text": doc, "source": meta["source"], "distance": dist}

    sorted_chunks = sorted(combined.values(), key=lambda x: x["distance"])
    return sorted_chunks[:6]


# ── STEP 3 & 4: PROMPT BUILDING + GENERATION ─────────────────────────────────
def generate_guidance(user_message, category, retrieved_chunks, chat_history=None):
    """
    Build a category-specific prompt (with retrieved wisdom + conversation
    history) and generate structured guidance.
    """
    wisdom_context = ""
    for i, chunk in enumerate(retrieved_chunks):
        source_label = {
            "gita":        "Bhagavad Gita",
            "mahabharata": "Mahabharata",
            "meditations": "Meditations (Marcus Aurelius)"
        }.get(chunk["source"], chunk["source"])
        wisdom_context += f"\n[Source {i+1}: {source_label}]\n{chunk['text'][:400]}\n"

    history_text = ""
    if chat_history:
        for turn in chat_history[-6:]:
            speaker = "User" if turn["role"] == "user" else "DharmaAI"
            history_text += f"{speaker}: {turn['content'][:200]}\n"

    category_angles = {
        "career": "Focus on dharma (duty/purpose), karma yoga (action without attachment to results), svadharma (your own path vs someone else's).",
        "relationship": "Focus on the karmic nature of relationships (people enter our lives as teachers), attachment vs love, impermanence. Reframe: this person was a karmic mirror, not a permanent fixture. Find the LESSON.",
        "family": "Focus on dharmic obligations, the complexity of love and duty, how even great families face impossible choices.",
        "stress": "Focus on equanimity (samatvam), the observer mind (sakshi), what is and isn't in our control.",
        "growth": "Focus on self-knowledge (atma jnana), the journey of the soul, how every challenge is a curriculum for growth."
    }

    prompt = f"""
You are DharmaAI — a wise, warm guide rooted in dharmic philosophy and timeless
psychological insight. You are having an ONGOING CONVERSATION with this person,
like a guru with a student — not answering an isolated question.

IMPORTANT RULES:
- NEVER say "everything will be okay" or give empty comfort
- DO reframe their situation through dharma, karma, and wisdom
- If conversation history exists below, reference it naturally — remember
  names, earlier situations, what you already told them. Don't repeat yourself.
- Speak like a wise elder who remembers this person

CONVERSATION SO FAR:
{history_text if history_text else "(this is the start of the conversation)"}

CATEGORY: {category.upper()} SITUATION
{category_angles[category]}

RETRIEVED WISDOM FROM SACRED TEXTS:
{wisdom_context}

USER'S CURRENT MESSAGE:
"{user_message}"

Respond in EXACTLY this structure. BE CONCISE — keep ENTIRE response under 150 words:

**Situation:**
(ONE short sentence)

**Wisdom:**
(1-2 short sentences, mention source briefly)

**The Deeper Lesson:**
(ONE short sentence)

**Three Steps Forward:**
1. (Short action, under 12 words)
2. (Short action, under 12 words)
3. (Short action, under 12 words)

**Reflect On This:**
(ONE short question, under 15 words)
"""
    response = client_ai.models.generate_content(
        model=GEN_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=500,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    )
    return response.text


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def get_guidance(user_message, chat_history=None):
    """
    Single entry point. FastAPI calls only this function.

    chat_history: optional list of {"role": "user"/"dharmaai", "content": str}
    representing the conversation so far — gives DharmaAI memory across turns.
    """
    print(f"\nProcessing: '{user_message[:50]}...'")

    if is_casual_message(user_message):
        print("  Detected: casual message")
        reply = generate_casual_reply(user_message, chat_history)
        return {"category": "casual", "guidance": reply, "sources": [], "chunks_used": 0}

    category = classify_intent(user_message)
    print(f"  Detected category: {category}")

    chunks = retrieve_wisdom(user_message, category)
    print(f"  Retrieved {len(chunks)} chunks from: {list(set(c['source'] for c in chunks))}")

    guidance = generate_guidance(user_message, category, chunks, chat_history)
    print(f"  Generated response ({len(guidance)} chars)")

    return {
        "category": category,
        "guidance": guidance,
        "sources": list(set(c["source"] for c in chunks)),
        "chunks_used": len(chunks)
    }


# ── TEST ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*60)
    print("Testing DharmaAI conversation flow")
    print("="*60)

    history = []
    test_flow = [
        "hello, this is Usha",
        "I feel stuck in my career and don't know what direction to take",
        "thank you, that helps"
    ]

    for msg in test_flow:
        print(f"\nUSER: {msg}")
        result = get_guidance(msg, chat_history=history)
        print(f"DHARMAI: {result['guidance']}")
        print(f"[category: {result['category']}]")
        history.append({"role": "user", "content": msg})
        history.append({"role": "dharmaai", "content": result["guidance"]})
