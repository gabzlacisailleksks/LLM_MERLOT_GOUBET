Lab 1 Student Runbook — Threat Modeling & Secure Prompting
=======================================================
> Author : Badr TAJINI - LLM Cybersecurity - ECE 2025/2026

This guide walks you through the Lab 1 workflow end-to-end. Each section includes the exact commands to run, screenshots of the warm-up games, and explanations of what to record for your deliverables. Treat every model output as **untrusted** until it passes your own checks.

---

## 0. Prerequisites (do these before class)

- **Python 3.11+** installed locally (3.11-3.13 supported)
- **Node.js 22+ LTS** — For promptfoo eval in Labs 2 and Project
- A Google **Gemini API key** from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- Basic terminal and Git familiarity

Optional but recommended:

- Visual Studio Code or another editor with Jupyter support.
- A GitHub account if you plan to push lab artifacts to a remote repo.

---

## 1. Pull the starter project

```bash
git clone https://github.com/<your-org>/<your-course-repo>.git
cd llm-course
```

> Already inside the repo? Just `cd llm-course` from wherever you are.

---

## 2. Create and activate the virtual environment

The course uses a **single shared venv** at the repository root:

```bash
# From repo root (llm-course/)
make install    # Creates .venv and installs all dependencies

# Activate it:
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\Activate.ps1
```

> **Manual alternative** (if make doesn't work):
> ```bash
> python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
> ```

---

## 3. Configure environment variables

The `.env` file lives at the **repository root** (not inside each lab):

```bash
# From repo root (llm-course/)
cp .env.example .env
```

Edit `.env` so it contains:

```
GEMINI_API_KEY=your-real-key-here
MODEL_ID=gemini-2.5-flash   # default; feel free to change later
```

Do **not** commit the real key. `.env` is already in `.gitignore`.

---

## 4. Warm-up: red-team playgrounds

Spend 15–20 minutes attacking hosted LLM challenges to see how prompt-injection works in practice.

### Gandalf (Lakera Agent Breaker)

![Gandalf Agent Breaker dashboard](docs/images/gandalf-agent-breaker.png)

1. Visit <https://gandalf.lakera.ai/agent-breaker>.
2. Pick a scenario (e.g., *PortfolioIQ Advisor* or *Clause AI*).
3. Document:
   - The payload you tried.
   - Whether the model refused or leaked data.
   - Which OWASP LLM Top-10 risk the behavior matches.

### RedArena

![RedArena home](docs/images/redarena-home.png)

1. Visit <https://redarena.ai/>.
2. Attempt at least one challenge.
3. Record the prompt you submitted and what guardrails failed or held.

Bring your notes (payload, effect, mapped risk) into your threat model later.

---

## 5. Inspect the starter code

- `src/app.py` orchestrates the pipeline: input filter → Gemini call → JSON schema validation → `reports/baseline.json`.
- `src/filters.py` performs minimal prompt scrubbing (e.g., removing “ignore previous instructions”).
- `src/prompts.py` houses the system policy and user template you will harden.
- `data/prompts_lab1.json` contains the seed prompts (mix of benign, malicious, and policy questions).

Skim the files so you know where to add constraints or logging.

---

## 6. Run the baseline analysis

With your virtual environment active and `.env` configured:

```bash
python -m src.app
```

You should see:

```
Wrote .../reports/baseline.json with 10 items.
```

Open `reports/baseline.json` to review the structured findings. Each entry contains:

- `id` and original `text`
- `llm_risks`: OWASP LLM identifiers (e.g., `LLM01`)
- `findings`: array with `title`, `severity`, `rationale`, `cwe`

---

## 7. Validate in a notebook (optional but recommended)

Launch Jupyter (VS Code or CLI):

```bash
pip install nbformat nbclient ipykernel  # already installed in this repo
python -m ipykernel install --user --name llm-sec-lab1
jupyter notebook notebooks/lab1_live_run.ipynb
```

Run the cells:

1. Imports the app.
2. Executes `app.main()` (uses your `.env`).
3. Displays the first two results inline.

Notebook parity is important for demoing and debugging when CLI access is restricted.

---

## 8. Capture before/after evidence

### ⚠️ CRITICAL: Save BEFORE state first!

**You MUST save your baseline BEFORE making any changes.** Without this, you cannot prove improvement.

### Step-by-Step Workflow:

```bash
# STEP 1: Run the baseline FIRST (before any changes)
python -m src.app
# This creates reports/baseline.json

# STEP 2: IMMEDIATELY save it as "before"
cp reports/baseline.json reports/baseline_before.json
git add reports/baseline_before.json
git commit -m "Lab 1: Capture baseline BEFORE improvements"
```

### Step 3: Make your improvements

Now edit these files to harden the prompts:
- `src/prompts.py` — Tighten SYSTEM_POLICY, add refusal instructions
- `src/filters.py` — Add input filtering patterns
- `data/prompts_lab1.json` — Test with adversarial prompts

### Step 4: Capture the AFTER state

```bash
# Run again AFTER your changes
python -m src.app
# This overwrites reports/baseline.json

# Save it as "after"
cp reports/baseline.json reports/baseline_after.json
git add reports/baseline_after.json
git commit -m "Lab 1: Capture baseline AFTER improvements"
```

### Step 5: Compare and document

```bash
# Compare the two files
diff reports/baseline_before.json reports/baseline_after.json

# Or use a visual diff tool
code --diff reports/baseline_before.json reports/baseline_after.json
```

Write in your analysis:
- Which prompts were blocked after your changes?
- Which ones still bypass controls? Why?
- What OWASP/ATLAS risks do they represent?

---

## 9. Threat model deliverable checklist

Your 2-page report should include:

- **Assets & trust boundaries**: data stores, model API, reporting pipeline.
- **Adversaries & entry points**: user prompts, external URLs, plugin calls.
- **Mapped risks**: cite OWASP LLM Top-10 and MITRE ATLAS tactics seen in Gandalf/RedArena and in `prompts_lab1.json`.
- **Mitigations**: filters, schema validation, rate limits, human review.
- **Residual risk & next steps**: what still needs to be fixed after your hardening.

---

## 10. Explore other Gemini models (optional extension)

Swap the model at runtime:

```bash
MODEL_ID=gemini-flash-latest python -m src.app
MODEL_ID=gemini-2.5-pro python -m src.app
MODEL_ID=gemini-2.5-flash-lite python -m src.app
```

The repo stores sample outputs:

- `reports/baseline_gemini-2.5-flash.json`
- `reports/baseline_gemini-flash-latest.json`
- `reports/baseline_gemini-2.5-pro.json`
- `reports/baseline_gemini-2.5-flash-lite.json`

Take note of response length, CWE coverage, and refusal behavior. This feeds into the “Observations” section below.

---

## 11. Run the automated tests

The project ships with a regression suite covering Gemini error handling and schema parsing.

```bash
python -m unittest discover tests
```

Five tests should pass. From the repo root you can instead run:

```bash
make w01-day
```

That target executes the same unittest suite (using the project virtualenv when available) and reminds you where to find the archived model outputs. If they fail, inspect `src/app.py` changes or your environment.

---

## 12. Observations from the reference runs

- **Gemini 2.5 Flash (default)** returns the richest rationales and consistent CWE tagging across all prompts.
- **Gemini 2.5 Flash-Lite** mirrors the Flash findings but shortens the explanations—handy when latency/cost matters.
- **Gemini 2.5 Pro** is more conservative: low-risk prompts can yield empty findings, but sensitive prompts (password exfiltration) still trigger high-severity alerts.
- The added retry logic in `src/app.py` eliminates prior `503 UNAVAILABLE` crashes. If you see warnings about `thought_signature`, they are informational; the JSON payload remains valid.
- A quick reference table lives at `reports/model-comparison.md`.

Use these insights to justify which model you pick for your lab submission.

---

## 13. Why we integrate GitHub Actions / CI

- Running `.venv/bin/python -m unittest discover tests` on every push catches regressions in error handling before we hit the lab.
- CI can automatically run the baseline script with a mocked Gemini client to verify JSON schema compliance, providing quick feedback.
- Centralized logs help professor monitor when API quotas or guardrails start failing.

The repo now ships with `make w01-day`, which runs the unittest suite and reminds you where the archived model outputs live. If you have an existing automation flow, invoke that target or replicate its steps in your CI system.

---

## 14. Next actions after the lab

1. **CI integration** – Done for you via `.github/workflows/lab1-tests.yml`. Use it as a reference or extend it for additional checks.
2. **Model selection review** – Use the JSON archives listed in the `make w01-day` output (and `reports/model-comparison.md`) to pick the Gemini tier that matches your budget and risk tolerance.
3. **Post-processing extensions** – If your downstream tooling requires confidence scores or normalized severity labels, add them to `src/app.py` after the schema validation step.
4. **Prepare your submission** – Bundle:
   - Updated prompts/policy files.
   - `reports/baseline_after.json` (or similar).
   - Your 2-page threat model PDF.
   - One slide summarizing key risks and mitigations.

---

## DELIVERABLES CHECKLIST — What You Must Submit

### Files to Create (in `reports/` folder):

| File | Description | When to Create |
|------|-------------|----------------|
| `baseline_before.json` | First run, BEFORE any prompt changes | Step 1 (immediately after setup) |
| `baseline_after.json` | Second run, AFTER your improvements | After hardening prompts |
| `gandalf_notes.md` | Your Gandalf attack attempts + OWASP mapping | During warm-up (Section 4) |
| `redarena_notes.md` | Your RedArena attempts + lessons learned | During warm-up (Section 4) |

### Documents to Write:

| Document | Description | Format |
|----------|-------------|--------|
| **Threat Model** | 2-page security analysis | PDF |
| **Risk Summary Slide** | 1 slide with key risks + mitigations | PDF or PPTX |

### Threat Model Must Include:
1. **Assets & Trust Boundaries** — What data does the LLM handle?
2. **Adversaries & Entry Points** — How can attackers interact?
3. **Mapped Risks** — Cite OWASP LLM Top-10 (LLM01, LLM02, etc.) and MITRE ATLAS
4. **Your Mitigations** — What filters, schemas, policies did you add?
5. **Residual Risks** — What still needs fixing?

### Before Submitting, Verify:

```bash
# From repo root, run:
make w01-day

# All 5 tests should pass
# Check your reports folder has all files:
ls reports/
# Should show: baseline_before.json, baseline_after.json, gandalf_notes.md, redarena_notes.md
```

---

## 15. Troubleshooting quick answers

| Issue | Quick fix |
| ----- | --------- |
| `Gemini API error after retries` | Check your API quota, verify `MODEL_ID`, and rerun later. |
| Report missing findings | Ensure `response_mime_type="application/json"` is intact and the model didn’t return empty text. |
| Notebook kernel missing | Run `python -m ipykernel install --user --name llm-sec-lab1`. |
| JSON still wrapped in ``` fences | The starter strips them. If you change prompts, keep that logic or tighten the prompt. |

---

## Appendix: Getting the starter

### Option A — Professor invites you to the private GitHub repo

Once you accept the invite, do the following:

1. **Clone the repo**
   ```bash
   git clone https://github.com/btajini/llm-course.git
   cd llm-course
   ```

2. **Create your `.env`**
   ```bash
   cp .env.example .env
   # Add your Gemini API key in .env
   ```

3. **Install dependencies (single venv for all labs)**
   ```bash
   make install    # Creates .venv and installs everything
   source .venv/bin/activate  # Activate it
   ```

4. **Verify the setup**
   ```bash
   make w01-day    # Run Lab 1 tests
   ```

5. **Work on the lab**
   ```bash
   cd labs/lab1    # Go to Lab 1 directory
   # Read README-student.md and follow the steps
   ```

6. **Publish updates later**
   ```bash
   git status -sb          # shows modified files
   git add <path>          # stage the changes you want to commit
   # example: git add labs/lab1/reports/baseline_after.json
   git commit -m "Describe your change"
   git push                # send the commit to GitHub
   ```

### Option B — Professor shares a ZIP archive

1. **Unzip the archive**
   ```bash
   unzip llm-course.zip -d ~/projects
   cd ~/projects/llm-course
   ```

2. **Initialize the repo content**
   ```bash
   git init
   git branch -m main
   git add .
   git commit -m "Initial commit"
   ```

3. **Setup environment**
   ```bash
   make install
   cp .env.example .env
   # Add your GEMINI_API_KEY in .env
   ```


3. **Publish to GitHub**
   - **Using GitHub CLI (recommended)**
     ```bash
     # install gh if needed: https://github.com/cli/cli/
     # Ubuntu/Debian: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
     # MacOS (Homebrew): https://github.com/cli/cli/blob/trunk/docs/install_macos.md
     # Then:
     gh auth login
     gh repo create <your-username>/llm-sec-lab1-starter --private --source=. --remote=origin --push
     ```
   - **Without GitHub CLI (manual git)**
     ```bash
     git remote add origin https://github.com/<your-username>/llm-sec-lab1-starter.git
     git push -u origin main
     ```
   - **VS Code workflow** (no CLI): open the folder in VS Code → Source Control view (Ctrl+Shift+G / Cmd+Shift+G) → **Initialize Repository** → stage `README.md` and `llm-sec-lab1/` → commit → click **Publish Branch**/**Publish to GitHub**, select your account, and mark the repo private.

4. **Continue with steps from Option A (create `.env`, install deps, run tests).**

Keep your copy private to avoid sharing API keys or lab answers.

**Need help?** Tag your professor, compare findings with peers, and submit PRs early so automated checks can guide you. Have fun breaking (and defending) LLMs!
