Lab 3 — Config & IaC Security with Checkov + Semgrep (+ Gemini for remediation)
=======================================================
> Author : Badr TAJINI - LLM Cybersecurity - ECE 2025/2026

**Goal.** Scan Terraform, Kubernetes manifests, and Dockerfile for misconfigurations. Then use Gemini to propose **structured remediation suggestions**, apply fixes, and re‑scan to demonstrate measurable improvement.

## Deliverables
- `reports/checkov.json`, `reports/semgrep.json`, and `reports/summary.md`
- After fixes: `reports/checkov_after.json`, `reports/semgrep_after.json`
- Table in `summary.md`: issue → change you made → status (fixed/ignored/false positive) → reference link
- 1‑page reflection: what patterns created most risk and how you’d prevent regressions (policy or CI idea)

## Environment
- **Python 3.11+** (3.11-3.13 supported)
- **Checkov**: installed via root requirements.txt
- **Semgrep**: installed via root requirements.txt
- **Gemini** (optional): installed via root requirements.txt
- VS Code locally; no cloud accounts required. We scan files only.

> **Optional microk8s sandbox.** If you want to apply the manifests to a lightweight cluster for manual validation, install microk8s (`sudo snap install microk8s --classic && sudo usermod -a -G microk8s $USER`) and run `microk8s status --wait-ready`. You can then `microk8s kubectl apply -f k8s/` to inspect pods locally. This is not required for grading—static scans are sufficient.

> Docs: Checkov quick start & CLI, Semgrep quickstart & rules, Gemini quickstart (see end of page).

## Setup
```bash
# From repo root (llm-course/)
make install                            # Creates .venv at repo root
source .venv/bin/activate               # Windows: .venv\Scripts\activate
cp .env.example .env                    # put your Gemini key if you plan to use remediation assistant
cd labs/lab3
```

## 1) Baseline scans
```bash
# Checkov: Terraform + K8s + Dockerfile folders
python scripts/run_checkov.py            # writes reports/checkov.json

# Semgrep: Kubernetes + Dockerfile rules (and a small local ruleset)
python scripts/run_semgrep.py            # writes reports/semgrep.json
```

## 2) Gemini remediation assistant (optional)
```bash
python src/gemini_remediate.py reports/checkov.json reports/semgrep.json   > reports/remediation_suggestions.json
```
Open the JSON and pick **concrete edits** to apply manually to files in `terraform/`, `k8s/`, or `docker/`.

## 3) Re‑scan after edits
```bash
python scripts/run_checkov.py --after
python scripts/run_semgrep.py --after
```
Compare `*_after.json` vs the baseline in `summary.md`.

## Acceptance criteria
- Baseline JSON reports exist and are valid.
- At least **3 distinct fixes** applied across Terraform/K8s/Dockerfile.
- After scans show fewer **FAILED** (Checkov) and fewer **ERROR/WARN** (Semgrep) for the fixed items.
- `summary.md` includes links to official docs that justify each fix.

## Notes
- We do **static** scanning only. No `terraform apply` or cluster required.
- Treat LLM output as untrusted. You **must** validate fixes by re‑scanning.

## References (put these in your `summary.md` when you cite them)
- Checkov install + quick start + CLI flags
- Semgrep quickstart, CLI usage, and Dockerfile/Kubernetes rule packs
- Kubernetes security context docs; AWS S3 public access best practices
- Gemini API quickstart and API key management
