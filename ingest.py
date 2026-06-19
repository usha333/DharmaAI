import os, re, time, chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()
client_ai = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    chroma_client.delete_collection("dharmaai")
    print("Deleted existing collection")
except:
    pass

collection = chroma_client.create_collection(name="dharmaai", metadata={"hnsw:space": "cosine"})
print("Created collection: dharmaai")

def read_file(filepath):
    if filepath.endswith(".pdf"):
        reader = PdfReader(filepath)
        return "\n".join(p.extract_text() for p in reader.pages if p.extract_text())
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def clean_text(text):
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def chunk_text(text, chunk_size=400, overlap=50):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start:start+chunk_size]))
        start += chunk_size - overlap
    return chunks

def get_embedding(text, retries=3):
    """
    Get embedding with retry logic.
    If rate limited (429), wait 60 seconds and try again.
    retries=3 means we try up to 3 times before giving up.
    """
    for attempt in range(retries):
        try:
            result = client_ai.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return result.embeddings[0].values
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 60 * (attempt + 1)  # wait 60s, then 120s, then 180s
                print(f"  Rate limited. Waiting {wait}s before retry {attempt+1}/{retries}...")
                time.sleep(wait)
            else:
                raise e
    raise Exception("Max retries exceeded — check your API quota")

sources = [
    {"file": "data/bhagavad-gita-in-english-source-file.pdf", "source_name": "gita"},
    {"file": "data/mahabharata.txt",                      "source_name": "mahabharata"},
    {"file": "data/meditations.txt",                          "source_name": "meditations"},
]

total_chunks = 0
for source in sources:
    print(f"\nProcessing: {source['source_name']}")
    if not os.path.exists(source["file"]):
        print(f"  NOT FOUND: {source['file']} — skipping")
        continue

    raw = read_file(source["file"])
    cleaned = clean_text(raw)
    chunks = chunk_text(cleaned)
    print(f"  Words: {len(cleaned.split())} | Chunks: {len(chunks)}")

    batch_ids, batch_emb, batch_docs, batch_meta = [], [], [], []

    for i, chunk in enumerate(chunks):
        if len(chunk.split()) < 20:
            continue

        batch_ids.append(f"{source['source_name']}_{i}")
        batch_emb.append(get_embedding(chunk))
        batch_docs.append(chunk)
        batch_meta.append({"source": source["source_name"], "chunk_index": i})

        # Small delay between every API call to avoid rate limits
        time.sleep(1.5)

        if len(batch_ids) == 50:
            collection.add(ids=batch_ids, embeddings=batch_emb, documents=batch_docs, metadatas=batch_meta)
            total_chunks += 50
            print(f"  Stored {total_chunks} chunks...")
            batch_ids, batch_emb, batch_docs, batch_meta = [], [], [], []

    if batch_ids:
        collection.add(ids=batch_ids, embeddings=batch_emb, documents=batch_docs, metadatas=batch_meta)
        total_chunks += len(batch_ids)
    print(f"  Done: {source['source_name']}")

print(f"\nDone! Total chunks stored: {total_chunks}")

# Quick test
print("\nTesting retrieval...")
time.sleep(3)
test_emb = client_ai.models.embed_content(
    model="gemini-embedding-001",
    contents="how to deal with fear and duty",
    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
).embeddings[0].values

results = collection.query(query_embeddings=[test_emb], n_results=3)
for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
    print(f"\n--- Result {i+1} (source: {meta['source']}) ---")
    print(doc[:200] + "...")
