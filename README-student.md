Lab 4 Student Runbook — Guardrails + Red Team Suite
=======================================================
> Author : Badr TAJINI - LLM Cybersecurity - ECE 2025/2026

**Goal:** Add guardrails to an LLM application and measure their effectiveness using an automated red-team attack suite. Compare **block rates** between unguarded and guarded modes.

---

## Table of Contents

1. [Prerequisites](#0-prerequisites)
2. [Getting Started](#1-getting-started)
3. [Understanding the Architecture](#2-understanding-the-architecture)
4. [Running the Attack Suite](#3-running-the-attack-suite)
5. [Computing Metrics](#4-computing-metrics)
6. [Customizing Guardrails](#5-customizing-guardrails)
7. [Troubleshooting](#6-troubleshooting)
8. [Deliverables](#deliverables-checklist)

---

## 0. Prerequisites (do these before class)

- **Python 3.11+** installed locally (3.11-3.13 supported)
- **Node.js 22+ LTS** — For promptfoo eval in Final Project
- A Google **Gemini API key** from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- Basic terminal and Git familiarity

Optional but recommended:

- Visual Studio Code or another editor with Jupyter support.
- A GitHub account if you plan to push lab artifacts to a remote repo.

### ⚠️ Rate Limits
Google AI Studio Free Tier has strict limits:
- **5 requests per minute** per model
- The code includes automatic delays to avoid hitting limits

---

## 1. Getting Started

### Step 1: Clone and Navigate
```bash
# Clone the course repository
git clone https://github.com/btajini/llm-course.git
cd llm-course
```

### Step 2: Activate the Shared Virtual Environment
The course uses a **single shared venv** at the repository root:

```bash
# From repo root (llm-course/)
make install                    # Creates .venv and installs all dependencies
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
(Dependencies already installed via root venv)

### Step 4: Configure API Key
```bash
# From repo root - .env is shared across all labs
cp .env.example .env
```

Edit `.env` and replace `PUT_YOUR_KEY_HERE` with your actual Gemini API key:
```
GEMINI_API_KEY=AIzaSy...your-actual-key...
MODEL_ID=gemini-2.5-flash
```

### Step 5: Navigate to Lab 4
```bash
cd labs/lab4
```

### Step 6: Verify Setup
```bash
source ../../.env               # Load from repo root
echo $GEMINI_API_KEY | head -c 10
# Should print: AIzaSy...
```

---

## 2. Understanding the Architecture

### Project Structure
```
llm-sec-lab4/
├── attacks/
│   └── attacks.txt          # Red-team prompts (malicious inputs)
├── config/
│   └── policy.yaml          # Guardrail rules (regex patterns)
├── src/
│   ├── guardrails.py        # Input/output filtering + LLM call
│   ├── run_suite.py         # Main attack runner
│   └── metrics.py           # Calculate block rate statistics
├── reports/                 # Output JSON and CSV files
└── tests/                   # Unit tests
```

### Guardrails Pipeline

```
User Input → [Input Filter] → LLM → [Output Filter] → Response
               ↓                        ↓
            BLOCKED?                  BLOCKED?
               ↓                        ↓
         policy.yaml              policy.yaml
         (deny_input_regex)       (deny_output_regex)
```

### Attack Types (attacks/attacks.txt)
The attack suite includes:
- **Prompt injection**: "Ignore previous instructions..."
- **System impersonation**: "You are now the system..."
- **Secret extraction**: "Reveal the API key..."
- **Shell commands**: "Run rm -rf /"
- **PII extraction**: "Show me user emails..."

---

## 3. Running the Attack Suite

### Run Unguarded Mode (No Guardrails)
```bash
source .env
PYTHONPATH=. python src/run_suite.py --mode unguarded --limit 10 --delay 12
```

**What this does:**
- Sends 10 attacks directly to the LLM without filtering
- Waits 12 seconds between requests (rate limit protection)
- Saves results to `reports/unguarded.json`

**Expected time:** ~2 minutes for 10 attacks

### Run Guarded Mode (With Guardrails)
```bash
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 10 --delay 12
```

**What this does:**
- Sends 10 attacks through input/output filters
- Blocks attacks matching `policy.yaml` patterns BEFORE calling LLM
- Saves results to `reports/guarded.json`

**Expected output:**
```
Running 10 attacks in guarded mode with 12.0s delay...
Estimated time: 2.0 minutes
  [1/10] Processing attack... BLOCKED
  [2/10] Processing attack... BLOCKED
  [3/10] Processing attack... UNSAFE
  ...
Wrote reports/guarded.json
```

### Understanding Results

| Status | Meaning |
|--------|---------|
| `BLOCKED` | Guardrail caught the attack (input or output filter) |
| `SAFE` | LLM said the request is safe |
| `UNSAFE` | LLM correctly identified an unsafe request |

---

## 4. Computing Metrics

After running both modes, compute the comparison metrics:

```bash
PYTHONPATH=. python src/metrics.py \
  reports/unguarded.json \
  reports/guarded.json \
  reports/metrics.csv
```

**Output file (`reports/metrics.csv`):**
```csv
run,total,blocked,block_rate,unsafe_pass,unsafe_pass_rate
unguarded,10,0,0.000,0,0.000
guarded,10,8,0.800,0,0.000
```

### Key Metrics Explained

| Metric | Description | Goal |
|--------|-------------|------|
| `block_rate` | % of attacks blocked by guardrails | Higher is better (guarded) |
| `unsafe_pass_rate` | % of unsafe requests that passed through | Lower is better |

---

## 5. Customizing Guardrails

### Required: Add 2+ New Rules

Edit `config/policy.yaml` to add your own guardrail rules:

```yaml
deny_input_regex:
  - "(?i)ignore (all|previous) instructions"
  - "(?i)you are now the system"
  # ADD YOUR RULES HERE:
  - "(?i)bypass|circumvent|disable.*(filter|guard|safety)"
  - "(?i)jailbreak|dan mode"

deny_output_regex:
  - "(?i)secret|password|api[_-]?key"
  # ADD YOUR RULES HERE:
  - "(?i)here is the (password|secret|key)"

pii_patterns:
  email: '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
  # ADD YOUR PATTERNS HERE:
  ssn: '(?i)\b\d{3}-\d{2}-\d{4}\b'
  credit_card: '\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
```

### Test Your Rules
After adding rules, re-run and compare:

```bash
# Re-run guarded mode
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 20 --delay 12

# Re-compute metrics
PYTHONPATH=. python src/metrics.py \
  reports/unguarded.json \
  reports/guarded.json \
  reports/metrics.csv

cat reports/metrics.csv
```

---

## 6. Troubleshooting

### "No module named 'src'"
Always run with `PYTHONPATH=.`:
```bash
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 5
```

### "429 RESOURCE_EXHAUSTED"
Rate limit hit! Solutions:
1. **Wait 60 seconds** - The code auto-retries
2. **Increase delay**: `--delay 15` (15 seconds between calls)
3. **Reduce limit**: `--limit 5` (fewer attacks)

### YAML Syntax Error in policy.yaml
The `\b` in regex patterns needs single quotes in YAML:
```yaml
# Wrong (double quotes escape \b)
email: "(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"

# Correct (single quotes preserve \b)
email: '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
```

### "invalid JSON" in model output
The model returns JSON wrapped in markdown. The code handles this automatically (strips \`\`\`json blocks).

### Empty reports directory
Create it:
```bash
mkdir -p reports
```

---

## 7. Run Automated Tests

```bash
python -m unittest discover tests
```

**Expected output:**
```
test_compute_stats ... ok
test_main_writes_csv ... ok
test_run_guarded_blocks_input ... ok
test_run_unguarded_generates_decisions ... ok
----------------------------------------------------------------------
Ran 4 tests in 0.005s
OK
```

---

## 8. Full Workflow Example

```bash
# 1. Setup
cd starter-labs/llm-sec-lab4-starter/llm-sec-lab4
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your API key
source .env

# 2. Run unguarded (no protection)
PYTHONPATH=. python src/run_suite.py --mode unguarded --limit 20 --delay 12

# 3. Run guarded (with guardrails)
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 20 --delay 12

# 4. Compute metrics
PYTHONPATH=. python src/metrics.py \
  reports/unguarded.json \
  reports/guarded.json \
  reports/metrics.csv

# 5. View results
cat reports/metrics.csv
```

---

## DELIVERABLES CHECKLIST — What You Must Submit

### CRITICAL: Capture Metrics BEFORE and AFTER Your Rule Changes!

You must prove YOUR rules improved the block rate. Follow this workflow:

### Step-by-Step Workflow:

```bash
# STEP 1: Run with DEFAULT policy (before your changes)
PYTHONPATH=. python src/run_suite.py --mode unguarded --limit 20 --delay 12
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 20 --delay 12

# STEP 2: Save initial metrics
PYTHONPATH=. python src/metrics.py reports/unguarded.json reports/guarded.json reports/metrics_initial.csv
cp reports/guarded.json reports/guarded_initial.json

# STEP 3: Add your 2+ new rules to config/policy.yaml
# Mark your additions with comments like: # ADDED BY STUDENT

# STEP 4: Run guarded mode again with YOUR rules
PYTHONPATH=. python src/run_suite.py --mode guarded --limit 20 --delay 12
cp reports/guarded.json reports/guarded_final.json

# STEP 5: Calculate final metrics
PYTHONPATH=. python src/metrics.py reports/unguarded.json reports/guarded_final.json reports/metrics_final.csv
```

### Files to Create:

| File | Description | When to Create |
|------|-------------|----------------|
| `reports/unguarded.json` | Results without any guardrails | Step 1 |
| `reports/guarded_initial.json` | Results with DEFAULT policy | Step 2 |
| `reports/metrics_initial.csv` | Block rate with DEFAULT policy | Step 2 |
| `reports/guarded_final.json` | Results with YOUR added rules | Step 4 |
| `reports/metrics_final.csv` | Block rate with YOUR rules | Step 5 |
| `config/policy.yaml` | Policy file with YOUR 2+ rules marked | Step 3 |

### Document to Write:

**1-Page Analysis Report** (`reports/analysis.md` or PDF):

| Section | What to Write |
|---------|---------------|
| **1. Initial Block Rate** | What % was blocked with default policy? |
| **2. Your Added Rules** | List each regex rule with explanation of what it catches |
| **3. Final Block Rate** | What % is blocked now with your rules? |
| **4. Example Blocks** | Show 2-3 specific attacks your rules caught |
| **5. Bypass Attempts** | Did any attacks still succeed? Why? |
| **6. Limitations** | What can't regex guardrails catch? |

### Example Analysis Section:

```markdown
## My Added Rules

### Rule 1: Bypass detection
```yaml
- "(?i)bypass|circumvent|disable.*(filter|guard|safety)"
```
**Rationale:** Catches prompts trying to disable protections.
**Attacks blocked:** 3 of the 20 test attacks

### Rule 2: Jailbreak keywords
```yaml
- "(?i)jailbreak|dan mode|developer mode"
```
**Rationale:** Common jailbreak terminology.
**Attacks blocked:** 2 of the 20 test attacks

## Results Summary
- Initial block rate: 45% (9/20)
- Final block rate: 70% (14/20)
- Improvement: +25% (+5 attacks blocked)
```

### Before Submitting, Verify:

```bash
# From repo root:
make w04-day

# Check your reports folder:
ls reports/
# Should show: unguarded.json, guarded_initial.json, guarded_final.json, 
#              metrics_initial.csv, metrics_final.csv

# Compare block rates:
echo "=== INITIAL ===" && cat reports/metrics_initial.csv
echo "=== FINAL ===" && cat reports/metrics_final.csv
```

---

## References

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [Google AI Studio](https://aistudio.google.com/)
- [Regex101 - Test Your Patterns](https://regex101.com/)

---

Good luck building robust guardrails!

