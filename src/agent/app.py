import os
import argparse
import json
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
                    "google-genai is not installed. Install project requirements to run the agent track."
                )

    genai = _MissingGenAI()

from src.common.logger import log
from src.common.guards import input_guard, output_guard, enforce_json_schema

SYSTEM = (
    "You are a safe agent. You MUST return ONLY raw JSON. NO markdown. NO backticks. "
    "To use a tool, return JSON with a 'tool' object. Allowed tools: search_corpus{query}, calc{expr}. "
    "Max 3 steps. Final output must be JSON {answer, citations, safety, rationale}."
)


def search_corpus(query: str, k: int = 3):
    folder = Path("data/corpus")
    hits = []
    for p in sorted(folder.glob("*.txt")):
        txt = p.read_text(encoding="utf-8")
        score = sum(1 for w in query.lower().split() if w in txt.lower())
        hits.append((score, p.name, txt))
    hits.sort(reverse=True)
    return [{"doc": name, "snippet": txt[:200]} for score, name, txt in hits[:k] if score > 0]


def calc(expr: str) -> str:
    try:
        assert all(c in "0123456789+-*/(). " for c in expr)
        return str(eval(expr, {"__builtins__": {}}))
    except Exception as e:  # pragma: no cover - defensive
        return f"error: {e}"


def ask(client, model, content: str) -> str:
    resp = client.models.generate_content(
        model=model,
        contents=content,
        config={"system_instruction": SYSTEM},
    )
    text = resp.text or ""
    return text.replace("```json", "").replace("```", "").strip()


def run(
    question: str,
    *,
    client=None,
    model: Optional[str] = None,
    max_steps: int = 3,
):
    if client is None:
        load_dotenv()
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    ok, reason = input_guard(question)
    if not ok:
        return {"answer": "", "citations": [], "safety": "unsafe", "rationale": reason}

    transcript = []
    content = (
        f"User question: {question}\n"
        "If you need a tool, return JSON {\"tool\":{\"name\":\"search_corpus\"|\"calc\", \"args\":{...}}}."
        " Otherwise return final JSON."
    )

    for step in range(max_steps):
        raw = ask(client, model, content)
        
        # 1. Extraction propre du JSON par Regex (Cherche le bloc entre { })
        import re
        match = re.search(r'(\{.*\})', raw, re.DOTALL)
        clean_raw = match.group(1) if match else raw

        # 2. On vérifie si c'est un appel d'outil
        if '"tool"' in clean_raw:
            try:
                # On utilise directement clean_raw qui est déjà extrait
                tool_req = json.loads(clean_raw).get("tool", {})
            except Exception:
                break
            
            name = tool_req.get("name")
            args_ = tool_req.get("args", {})
            if name == "search_corpus":
                res = search_corpus(args_.get("query", ""))
            elif name == "calc":
                res = calc(args_.get("expr", ""))
            else:
                res = "error: tool not allowed"
            
            transcript.append({"tool": name, "args": args_, "result": res})
            content = (
                "Tool result: "
                + json.dumps(res)[:1200]
                + "\nNow return final JSON with answer, citations, safety, rationale."
            )
            continue

        # 3. Si ce n'est pas un outil, on valide la réponse finale
        ok2, reason2 = output_guard(clean_raw) # Utilise clean_raw ici aussi
        if not ok2:
            return {"answer": "", "citations": [], "safety": "unsafe", "rationale": reason2}
        
        valid, err, obj = enforce_json_schema(clean_raw) # Et ici
        if not valid:
            return {"answer": "", "citations": [], "safety": "unsafe", "rationale": "Invalid JSON from model"}
        
        obj["steps"] = transcript
        log({"track": "agent", "q": question, "resp": obj})
        return obj

    return {
        "answer": "",
        "citations": [],
        "safety": "unsafe",
        "rationale": "Exceeded step limit",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--max-steps", type=int, default=3)
    args = ap.parse_args()

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    result = run(args.question, client=client, model=model, max_steps=args.max_steps)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
