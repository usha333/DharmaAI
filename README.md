# DharmaAI 🕉️

The idea came from a simple frustration: when people go through hard times — a breakup, a career crisis, family conflict — they either get generic motivational quotes or expensive therapy. There's a massive middle ground of wisdom that's been sitting in ancient texts for thousands of years, completely accessible, just not in a form that maps to modern problems.

So I built DharmaAI. It takes your life situation, figures out what kind of problem it really is, pulls the most relevant teachings from the Bhagavad Gita, Mahabharata, and Marcus Aurelius, and gives you something actually useful — not "everything will be okay" but "here's what this situation is actually teaching you, and here's what to do about it."

---

## What it does differently

Most spiritual chatbots I found were basically glorified search engines. Type a keyword, get a verse. That's it.

This is different. When you describe your situation, DharmaAI:

1. **Figures out what kind of problem it is** — not by keyword matching, but by having the LLM classify your intent into one of five life domains (career, relationship, family, stress, growth)
2. **Searches for meaning, not keywords** — uses vector embeddings so "I feel stuck and empty" retrieves teachings about attachment and purpose, even if those exact words aren't in the text
3. **Gives structured, actionable output** — not a verse dump, but a situation summary, the relevant wisdom with its source, a karmic/dharmic reframe of what's really happening, three concrete steps, and one reflection question

Here's a real example of the difference:

**What you'd get from a keyword chatbot:**
> "Bhagavad Gita 2.47 — You have a right to perform your prescribed duties, but you are not entitled to the fruits of your actions."

**What DharmaAI gives:**
> **Situation:** You're not really lost — you're between identities, which is one of the most disorienting places a person can be.
>
> **Wisdom:** The Gita doesn't tell Arjuna to feel better. It tells him to act according to his nature without clinging to outcome. Marcus Aurelius writes that we suffer more in imagination than in reality — what you're feeling right now is real, but the story you're telling about what it means may not be.
>
> **The Deeper Lesson:** This isn't a failure of direction. It's an invitation to ask a harder question — not "what job should I take" but "what kind of person am I becoming through this work?"
>
> **Three Steps Forward:**
> 1. Write down the last time work felt meaningful — what was actually happening in that moment?
> 2. Separate the financial pressure from the identity question — they feel like the same problem but they need different solutions
> 3. Take one small action today that aligns with who you want to become, not who you think you should be
>
> **Reflect On This:** If nobody was watching and money wasn't a concern, what would you spend your days doing?

That difference matters to me. The first answer is correct. The second is useful.

---

## How it actually works

The technical name for what's happening under the hood is Retrieval-Augmented Generation (RAG). Here's the plain English version:

The Bhagavad Gita is about 24,000 words. Marcus Aurelius' Meditations is around 75,000 words. You can't paste all of that into a prompt every time someone asks a question — there's a limit to how much text an LLM can process at once.

So instead, I:
1. Split all three texts into small chunks (~400 words each, with 50-word overlap so ideas don't get cut in half at boundaries)
2. Convert each chunk into a list of numbers that represents its meaning — called an embedding
3. Store all those chunks and their number-lists in ChromaDB, a vector database that lives on disk
4. When someone asks a question, convert their question into the same kind of numbers and find which stored chunks have the most similar meaning
5. Pull the top 6 most relevant chunks, drop them into a carefully designed prompt, and let Gemini write the response

The intent classification piece sits before all of this — a separate LLM call that reads the user's message and outputs one word: career, relationship, family, stress, or growth. That single word changes the system prompt, the retrieval search terms, and the framing of the entire response.

```
your situation
     ↓
intent classifier  →  "relationship"
     ↓
dual retrieval (your words + category keywords)
     ↓
ChromaDB returns top 6 chunks
     ↓
category-specific prompt + retrieved wisdom
     ↓
Gemini generates structured response
     ↓
Situation · Wisdom · Lesson · Steps · Reflection
```

---

## What I learned building this

**Chunking strategy is not trivial.** I started with fixed 500-character chunks. The retrieval was terrible — ideas would get cut mid-sentence, and the most relevant text would sometimes split across two chunks that never got retrieved together. Moving to word-based chunking with overlap fixed most of this.

**Dual-query retrieval made a real difference.** The user says "he left me without reason." The Gita talks about "attachment and impermanence." Those don't share vocabulary, so a single search on the user's words missed a lot. Adding a second search on category-specific terms (attachment, loss, karmic bond) and merging the results improved relevance noticeably.

**SDK deprecation mid-project is a real thing.** Halfway through, Google deprecated the `google-generativeai` package I'd started with. Had to migrate to the new `google-genai` SDK — different import style, different client initialization, different embedding model names. Annoying, but a good lesson in not assuming APIs stay stable.

**Free tier rate limits shape architecture.** The ingestion script went through hundreds of embedding API calls. Without a 1.5-second delay between calls and retry logic with exponential backoff, it would fail halfway through every time. This is the kind of thing that doesn't come up in tutorials but matters immediately in practice.

**I also built a LangChain version** (`rag_core_langchain.py`) after building the plain Python version. Doing it manually first meant I actually understood what LangChain was abstracting — which made learning the framework much faster and gave me a real answer when an interviewer asks "so what does LangChain actually do?"

---

## Tech stack

| What | Why |
|------|-----|
| Python 3.11 | Stable, ChromaDB requires 3.10+ |
| ChromaDB | Persistent vector storage, runs locally, no external service needed |
| Gemini API (free tier) | `gemini-embedding-001` for embeddings, `gemini-1.5-flash` for generation |
| FastAPI | Clean REST API with automatic validation and docs at `/docs` |
| Streamlit | Fast UI that hot-reloads during development |
| PyPDF | Extract text from PDF source documents |
| LangChain | Second implementation for framework familiarity |

---

## Project structure

```
DharmaAI_Project/
├── ingest.py               # Run once — loads PDFs into ChromaDB
├── rag_core.py             # Plain Python RAG pipeline
├── rag_core_langchain.py   # Same pipeline using LangChain
├── main.py                 # FastAPI backend
├── app.py                  # Streamlit frontend
├── data/
│   ├── bhagavad-gita.pdf
│   ├── the_mahabharata.pdf
│   └── meditations.txt
├── chroma_db/              # Auto-created by ingest.py
├── requirements.txt
└── .env.example
```

---

## Running it yourself

You need Python 3.10+ and a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey). No credit card required.

```bash
git clone https://github.com/ush333/dharmaai.git
cd dharmaai

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Add your Gemini API key
cp .env.example .env
# edit .env and paste your key

# Ingest source documents into ChromaDB (run once, takes ~15 mins on free tier)
python ingest.py

# Terminal 1: start the API
uvicorn main:app --reload

# Terminal 2: start the UI
streamlit run app.py
```

Open `http://localhost:8501`

---

## API

FastAPI auto-generates interactive docs at `http://localhost:8000/docs` once the server is running.

```bash
# Quick test
curl -X POST "http://localhost:8000/guidance" \
  -H "Content-Type: application/json" \
  -d '{"message": "I feel stuck in my career and dont know what direction to take"}'
```

---

## What's next

Things I want to add but haven't yet:

- Docker so it runs the same way anywhere without the setup steps
- Azure deployment so it's actually live, not just on my laptop
- Evaluation — I want to run 20-30 test queries and measure whether the right chunks are actually being retrieved, not just whether the output sounds good
- More sources: Yoga Sutras of Patanjali, Arthashastra, maybe some Jung

---

## Sources

All texts used are public domain:
- Bhagavad Gita — Edwin Arnold translation (Project Gutenberg)
- Mahabharata — Kisari Mohan Ganguli translation (Project Gutenberg)  
- Meditations — George Long translation (Project Gutenberg)

---

*Built by Usha · 2026*
