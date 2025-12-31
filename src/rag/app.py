import os, argparse, json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

try:  # pragma: no cover
    from google import genai
except ModuleNotFoundError:  # pragma: no cover
    class _MissingGenAI:
        class Client:  # pylint: disable=too-few-public-methods
            def __init__(self, *_, **__):
                raise ImportError(
                    "google-genai is not installed. Run `pip install -r requirements.txt` inside the project first."
                )

    genai = _MissingGenAI()
try:  # pragma: no cover
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ModuleNotFoundError:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

from src.common.logger import log
from src.common.guards import input_guard, output_guard, enforce_json_schema

SYSTEM = "Return ONLY raw JSON. NO markdown, NO backticks, NO explanations. Output schema: {\"answer\": \"...\", \"citations\": [], \"safety\": \"safe\", \"rationale\": \"...\"}"
def load_docs(folder: Path):
    docs = []
    for p in sorted(folder.glob("*.txt")):
        docs.append((p.name, p.read_text(encoding='utf-8')))
    return docs

def retrieve(docs, query, k=3):
    ids = [d[0] for d in docs]
    corpus = [d[1] for d in docs]
    if TfidfVectorizer is None or cosine_similarity is None:
        query_terms = query.lower().split()
        scored = []
        for idx, doc in enumerate(corpus):
            doc_lower = doc.lower()
            score = sum(doc_lower.count(term) for term in query_terms)
            scored.append((score, idx))
        scored.sort(key=lambda item: item[0], reverse=True)
        order = [idx for _, idx in scored[:k]]
    else:
        vec = TfidfVectorizer().fit(corpus + [query])
        X = vec.transform(corpus)
        q = vec.transform([query])
        sims = cosine_similarity(q, X).ravel()
        order = sims.argsort()[::-1][:k]
    return [(ids[i], corpus[i]) for i in order]

def build_prompt(query, evid):
    chunks = "\n\n".join([f"[{idx}] {text}" for idx, (_, text) in enumerate(evid, 1)])
    ids = [doc_id for doc_id, _ in evid]
    return (
        f"Use ONLY these documents to answer. Cite ids: {ids}.\n"
        f"QUESTION: {query}\n"
        "DOCUMENTS:\n"
        f"{chunks}\n"
        "Return strictly JSON with keys: answer, citations (array of doc ids), safety ('safe'|'unsafe'), rationale."
    )

def call_llm(client, model, prompt):
    resp = client.models.generate_content(model=model, contents=prompt, config={"system_instruction": SYSTEM})
    text = resp.text or ""
    clean_text = text.replace("```json", "").replace("```", "").strip()
    return clean_text

def run(question: str, k: int = 3, client=None, model: Optional[str] = None):
    """Execute the RAG pipeline and return a JSON-serialisable dict."""
    if client is None:
        load_dotenv()
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    ok, reason = input_guard(question)
    if not ok:
        log({"track":"rag","phase":"input_block","reason":reason,"q":question})
        return {"answer":"","citations":[],"safety":"unsafe","rationale":reason}

    # Use path relative to this file, not current working directory
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"
    docs = load_docs(corpus_dir)
    evid = retrieve(docs, question, k=k)
    prompt = build_prompt(question, evid)

    raw = call_llm(client, model, prompt)
    ok, reason = output_guard(raw)
    if not ok:
        log({"track":"rag","phase":"output_block","reason":reason,"raw":raw[:200]})
        return {"answer":"","citations":[],"safety":"unsafe","rationale":reason}

    valid, err, obj = enforce_json_schema(raw)
    if not valid:
        log({"track":"rag","phase":"schema_error","err":err,"raw":raw[:200]})
        return {"answer":"","citations":[],"safety":"unsafe","rationale":"Invalid JSON from model"}

    log({"track":"rag","phase":"ok","q":question,"resp":obj})
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--k", type=int, default=3)
    args = ap.parse_args()

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    result = run(args.question, k=args.k, client=client, model=model)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
