Final Project — Secure RAG **or** Safe Agent
=======================================================
> Author : Badr TAJINI - LLM Cybersecurity - ECE 2025/2026

Pick **both** tracks and deliver a minimal, defendable system with metrics and CI gates.

> **Note:** Both tracks live in this same starter. You can keep shared utilities under `src/` and gate behaviour with configuration flags (e.g., `--mode rag` vs `--mode agent`).

## Tracks
1) **Secure RAG**: local TF‑IDF retrieval over `data/corpus/` + Gemini answerer that must return **JSON** with citations and a safety decision.
2) **Safe Agent**: a constrained agent with an **allow‑listed toolset** (`search_corpus`, `calc`) that plans, executes up to N steps, and returns **JSON** with the final answer and the executed steps.

## Core constraints
- **Replay logging**: all interactions logged to `logs.jsonl` with timestamps, prompts, outputs, and policy decisions.
- **Guardrails**: input and output guards, plus JSON schema validation.
- **Eval loop**: `promptfoo` tests for both correctness and safety. Produce `reports/*.html, *.json, metrics.csv`.
- **CI gate**: GitHub Actions runs promptfoo + metrics and fails if thresholds are not met.

## Quick start
```bash
# From repo root (llm-course/)
make install                      # Creates .venv at repo root
source .venv/bin/activate
cp .env.example .env              # set GEMINI_API_KEY
cd project

# Unified runner (choose track)
python -m src.app --track rag --question "What is LLM01?" --k 3
python -m src.app --track agent --question "Add 21 and 21; cite the doc id mentioning OWASP." --max-steps 3

# Evals
npm i -g promptfoo@latest
promptfoo eval -c promptfooconfig.yaml -o reports/report.html -o reports/results.json
python tools/metrics.py reports/results.json reports/metrics.csv
```

## Deliverables
- Source repo with both tracks completed
- **Replay file** `logs.jsonl`
- `reports/report.html`, `reports/results.json`, `reports/metrics.csv`
- 3–5 page report: threat model, design decisions, eval results, failures and fixes, mapping to OWASP LLM Top‑10 & MITRE ATLAS

## Grading thresholds (CI)
- JSON validity ≥ 0.95
- Safety (attack tests blocked or labeled unsafe) ≥ 0.85
- RAG track: citation present on ≥ 0.80 of knowledge questions
- Agent track: tool use stays within allow‑list with ≤ 3 steps

Edit thresholds in `.github/workflows/ci.yml` or `tools/metrics.py` as needed.
