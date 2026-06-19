"""
rag_core_langchain.py — LangChain version of the DharmaAI RAG pipeline.

Compare this with rag_core.py (plain Python version) to understand
exactly what LangChain abstracts away.

Same result, less code, less visibility into internals.
Both versions are kept in the repo intentionally:
- rag_core.py        = plain Python (shows understanding of internals)
- rag_core_langchain.py = LangChain (shows framework knowledge)
"""

import os
from dotenv import load_dotenv

# ── LangChain imports ─────────────────────────────────────────────────────────
from langchain.text_splitter import RecursiveCharacterTextSplitter
# RecursiveCharacterTextSplitter = our chunk_text() function
# It tries to split on paragraphs first, then sentences, then words
# "Recursive" means it tries multiple separators in order

from langchain_community.vectorstores import Chroma
# Chroma = wrapper around ChromaDB
# Handles embedding + storing + searching in one object

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# GoogleGenerativeAIEmbeddings = wrapper around Gemini embedding API
# ChatGoogleGenerativeAI = wrapper around Gemini generation API

from langchain.chains import RetrievalQA
# RetrievalQA = combines retriever + LLM into one callable chain
# Handles: embed query → search → build prompt → generate → return

from langchain.prompts import PromptTemplate
# PromptTemplate = structured way to define prompts with variables
# Like an f-string but with validation and reusability

from langchain_community.document_loaders import PyPDFLoader, TextLoader
# Document loaders = read files and return LangChain Document objects
# Each Document has .page_content (text) and .metadata (source info)

# ── Load API key ──────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# ── Initialize Gemini components via LangChain ────────────────────────────────
# In plain Python: client_ai = genai.Client(api_key=...)
# In LangChain: separate objects for embeddings vs generation

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_document"
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
    max_output_tokens=1000
)

# ── Load and chunk documents using LangChain ──────────────────────────────────
def load_documents():
    """
    LangChain version of reading + chunking files.

    Plain Python version (rag_core.py):
        raw = read_file(filepath)
        chunks = chunk_text(raw, chunk_size=400, overlap=50)

    LangChain version:
        loader = PyPDFLoader(filepath)  ← reads the file
        docs = loader.load()            ← returns list of Document objects
        chunks = splitter.split_documents(docs)  ← splits into chunks

    Key difference: LangChain Document objects carry metadata automatically
    (page number, source filename) without you manually tracking it.
    """

    # Text splitter — equivalent to our chunk_text() function
    # RecursiveCharacterTextSplitter tries these separators in order:
    # paragraphs (\n\n) → sentences (\n) → words ( ) → characters ("")
    # This produces more semantically meaningful chunks than fixed word count
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,       # characters (not words like our version)
        chunk_overlap=150,     # character overlap between chunks
        separators=["\n\n", "\n", " ", ""]
    )

    all_docs = []

    sources = [
        {"file": "data/bhagavad-gita-in-english-source-file.pdf", "source": "gita"},
        {"file": "data/the_mahabharata.pdf",                      "source": "mahabharata"},
        {"file": "data/meditations.txt",                          "source": "meditations"},
    ]

    for source in sources:
        if not os.path.exists(source["file"]):
            print(f"Skipping {source['file']} — not found")
            continue

        print(f"Loading: {source['file']}")

        # Choose loader based on file type
        if source["file"].endswith(".pdf"):
            loader = PyPDFLoader(source["file"])
        else:
            loader = TextLoader(source["file"], encoding="utf-8")

        # Load returns list of Document objects (one per page for PDF)
        documents = loader.load()

        # Add our custom source metadata to each document
        for doc in documents:
            doc.metadata["source"] = source["source"]

        # Split into chunks — returns list of smaller Document objects
        chunks = splitter.split_documents(documents)
        all_docs.extend(chunks)
        print(f"  → {len(chunks)} chunks created")

    print(f"\nTotal chunks: {len(all_docs)}")
    return all_docs


# ── Build or load ChromaDB vectorstore ───────────────────────────────────────
def get_vectorstore(rebuild=False):
    """
    Plain Python version (rag_core.py):
        collection = chroma_client.get_collection("dharmaai")
        # then manually embed query and call collection.query()

    LangChain version:
        vectorstore = Chroma(...)
        # vectorstore.as_retriever() handles embedding + querying automatically

    The LangChain Chroma wrapper:
    - Embeds documents automatically when you call .from_documents()
    - Embeds queries automatically when you call .similarity_search()
    - You never manually call the embedding API
    """

    chroma_dir = "./chroma_db_langchain"  # separate from plain Python version

    if os.path.exists(chroma_dir) and not rebuild:
        print("Loading existing LangChain ChromaDB...")
        # Load existing vectorstore — no re-embedding needed
        vectorstore = Chroma(
            persist_directory=chroma_dir,
            embedding_function=embeddings,
            collection_name="dharmaai_langchain"
        )
        print(f"Loaded {vectorstore._collection.count()} chunks")
        return vectorstore

    print("Building new LangChain ChromaDB...")
    docs = load_documents()

    # Chroma.from_documents():
    # 1. Takes each document's text
    # 2. Calls embeddings.embed_documents() on each (our get_embedding())
    # 3. Stores text + embedding + metadata in ChromaDB
    # All 3 steps in one line vs our manual loop
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=chroma_dir,
        collection_name="dharmaai_langchain"
    )

    print(f"Built vectorstore with {vectorstore._collection.count()} chunks")
    return vectorstore


# ── Intent Classification (same as plain Python version) ─────────────────────
def classify_intent(user_message):
    """
    LangChain has a PromptTemplate for structured prompts.
    This replaces our plain f-string prompt.

    Plain Python version:
        prompt = f"Classify this: {user_message}. Reply with one word."
        response = client_ai.models.generate_content(model=..., contents=prompt)
        return response.text.strip()

    LangChain version:
        template = PromptTemplate(input_variables=["message"], template="...")
        chain = template | llm  ← pipe operator chains template → llm
        response = chain.invoke({"message": user_message})
    """

    classification_template = PromptTemplate(
        input_variables=["message"],
        template="""
Classify the user's message into EXACTLY ONE category:
- career: work, job, purpose, ambition, direction
- relationship: romantic relationships, heartbreak, loneliness, attachment
- family: parents, siblings, family conflict, expectations
- stress: anxiety, overwhelm, mental health, burnout, fear
- growth: self-improvement, habits, meaning, spiritual seeking

Examples:
"I lost my job" → career
"Someone I loved left me" → relationship
"My parents don't understand me" → family
"I feel anxious all the time" → stress
"I want to become a better person" → growth

User message: "{message}"

Reply with ONLY the category word. Nothing else.
"""
    )

    # The pipe operator (|) chains: template → llm
    # This is LangChain's "chain" concept — composable steps
    chain = classification_template | llm
    response = chain.invoke({"message": user_message})

    # LangChain LLM returns AIMessage object, .content gets the text
    category = response.content.strip().lower().replace(".", "")

    valid = ["career", "relationship", "family", "stress", "growth"]
    return category if category in valid else "stress"


# ── Build RAG Chain ───────────────────────────────────────────────────────────
def build_rag_chain(vectorstore, category):
    """
    This is the biggest difference from plain Python.

    Plain Python version (rag_core.py):
        1. chunks = retrieve_wisdom(user_message, category)  ← manual search
        2. prompt = build_prompt(chunks, category, user_message)  ← manual
        3. response = generate_guidance(prompt)  ← manual API call

    LangChain version:
        chain = RetrievalQA.from_chain_type(llm, retriever, prompt)
        result = chain.invoke({"query": user_message})
        ← ALL 3 steps happen inside chain.invoke()

    The chain automatically:
    - Embeds the query
    - Searches ChromaDB
    - Inserts retrieved chunks into the prompt template
    - Calls the LLM
    - Returns the result
    """

    # Category-specific prompt angles — same logic as plain Python version
    category_angles = {
        "career":       "Focus on dharma (duty/purpose), karma yoga (action without attachment to results), svadharma (your own path).",
        "relationship": "Focus on karmic lessons in relationships, attachment vs love, impermanence. Reframe: this person was a karmic mirror, not a permanent fixture. Find the LESSON.",
        "family":       "Focus on dharmic obligations, complexity of love and duty, how even great families face impossible choices.",
        "stress":       "Focus on equanimity (samatvam), the observer mind (sakshi), what is and isn't in our control.",
        "growth":       "Focus on self-knowledge (atma jnana), the journey of the soul, how every challenge is a curriculum for growth."
    }

    # PromptTemplate with {context} and {question} as required variables
    # {context} = retrieved chunks (LangChain fills this automatically)
    # {question} = user's message (LangChain fills this automatically)
    dharma_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=f"""
You are DharmaAI — a wisdom-based life guidance system.

IMPORTANT:
- NEVER say "everything will be okay" or give empty comfort
- DO reframe situations through dharma, karma, and timeless wisdom
- Speak with warmth and depth — like a wise elder

GUIDANCE ANGLE FOR THIS SITUATION:
{category_angles.get(category, category_angles['stress'])}

RETRIEVED WISDOM FROM SACRED TEXTS:
{{context}}

USER'S SITUATION:
"{{question}}"

Respond in EXACTLY this structure:

**Situation:**
(One sentence — what they're really going through at a deeper level)

**Wisdom:**
(2-3 sentences from the retrieved texts above. Mention the source.)

**The Deeper Lesson:**
(The karmic/dharmic reframe specific to THEIR situation)

**Three Steps Forward:**
1. (Wisdom-rooted action)
2. (Wisdom-rooted action)
3. (Wisdom-rooted action)

**Reflect On This:**
(One powerful question for self-inquiry)
"""
    )

    # as_retriever() converts vectorstore into a retriever object
    # search_kwargs={"k": 6} = return top 6 most similar chunks
    retriever = vectorstore.as_retriever(
        search_type="similarity",  # cosine similarity search
        search_kwargs={"k": 6}
    )

    # RetrievalQA chain ties everything together:
    # query → retriever → prompt → llm → answer
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # "stuff" = put all chunks into one prompt
        retriever=retriever,
        chain_type_kwargs={"prompt": dharma_prompt},
        return_source_documents=True  # include which chunks were used
    )

    return chain


# ── Main Pipeline Function ────────────────────────────────────────────────────
def get_guidance_langchain(user_message):
    """
    Same interface as get_guidance() in rag_core.py.
    Drop-in replacement — FastAPI can call either version.
    """
    print(f"\nProcessing (LangChain): '{user_message[:50]}...'")

    # Step 1: Classify intent
    category = classify_intent(user_message)
    print(f"  Category: {category}")

    # Step 2: Load vectorstore
    vectorstore = get_vectorstore(rebuild=False)

    # Step 3: Build and run RAG chain
    chain = build_rag_chain(vectorstore, category)
    result = chain.invoke({"query": user_message})

    # Extract source documents used
    source_docs = result.get("source_documents", [])
    sources = list(set(
        doc.metadata.get("source", "unknown")
        for doc in source_docs
    ))

    print(f"  Sources used: {sources}")

    return {
        "category": category,
        "guidance": result["result"],
        "sources": sources,
        "chunks_used": len(source_docs)
    }


# ── Test directly ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*60)
    print("DharmaAI — LangChain Version")
    print("="*60)

    test_message = "Someone came into my life unexpectedly but left without reason and I feel lost"

    print(f"\nUSER: {test_message}")
    print("-"*60)

    result = get_guidance_langchain(test_message)

    print("\nDHARMAI RESPONSE (LangChain):")
    print(result["guidance"])
    print(f"\n[Category: {result['category']} | Sources: {result['sources']}]")
