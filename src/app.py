import json
import os
import argparse

from dotenv import load_dotenv

try:  # pragma: no cover - exercised in runtime envs
    from google import genai
except ModuleNotFoundError:  # pragma: no cover
    class _MissingGenAI:
        class Client:  # pylint: disable=too-few-public-methods
            def __init__(self, *_, **__):
                raise ImportError(
                    "google-genai is not installed. Run `pip install -r requirements.txt` to enable final project code."
                )

    genai = _MissingGenAI()

from src.rag.app import run as run_rag
from src.agent.app import run as run_agent


def main():
    parser = argparse.ArgumentParser(description="Unified entrypoint for final project tracks")
    parser.add_argument("--track", choices=["rag", "agent"], required=True, help="Which track to execute")
    parser.add_argument("--question", required=True)
    parser.add_argument("--k", type=int, default=3, help="Number of docs to retrieve (rag track)")
    parser.add_argument("--max-steps", type=int, default=3, help="Agent step cap (agent track)")
    args = parser.parse_args()

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    if args.track == "rag":
        result = run_rag(args.question, k=args.k, client=client, model=model)
    else:
        result = run_agent(args.question, client=client, model=model, max_steps=args.max_steps)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
