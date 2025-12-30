#!/usr/bin/env python3
import os, sys, json
from dotenv import load_dotenv
from google import genai

PROMPT = r"""
You are a senior cloud security engineer. From the following static-analysis findings,
produce a JSON array of remediation suggestions. Each item must be:
{
  "tool": "checkov|semgrep",
  "file": "relative/path",
  "issue_id": "CKV_... or semgrep rule id",
  "title": "short title",
  "proposed_fix": "exact changes or YAML/Terraform/Dockerfile snippet to apply",
  "justification": "why this fix addresses the risk with a reference to official docs"
}
Rules:
- Do not invent file paths or IDs. Only use items present in the input.
- Prefer concrete code/config edits over vague advice.
- Keep each 'proposed_fix' under 12 lines.
"""

def main(checkov_json, semgrep_json):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY missing (.env). Skipping.", file=sys.stderr)
        return
    client = genai.Client(api_key=api_key)
    model = os.getenv("MODEL_ID", "gemini-2.5-flash")

    payload = {
        "checkov": json.load(open(checkov_json, encoding="utf-8")) if os.path.exists(checkov_json) else None,
        "semgrep": json.load(open(semgrep_json, encoding="utf-8")) if os.path.exists(semgrep_json) else None
    }
    text = json.dumps(payload)[:200000]  # avoid excessive tokens
    resp = client.models.generate_content(
        model=model,
        contents=[
            {"role":"user","parts":[{"text":PROMPT}]},
            {"role":"user","parts":[{"text":text}]}
        ],
    )
    print(resp.text or "[]")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/gemini_remediate.py reports/checkov.json reports/semgrep.json")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
