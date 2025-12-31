# Final Project Student Runbook — Secure RAG & Safe Agent

> **Author:** Badr TAJINI — LLM Cybersecurity — ECE 2025/2026

This project combines everything from Labs 1-4 into a complete secure LLM application. You will build both a **RAG (Retrieval-Augmented Generation)** system and an **Agent** system with proper security guardrails.

---

## 0. Prerequisites (complete before class)

| Requirement | Why You Need It |
|-------------|-----------------|
| **Python 3.11+** | Core runtime (3.11-3.13 all work) |
| **Node.js 22+ LTS** | Required for promptfoo evaluation framework |
| **Gemini API Key** | Get free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **OpenRouter API Key** | Optional but **highly recommended** — Get free at [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Git** | Version control for your submissions |

### Why OpenRouter?

Google's free tier has **strict rate limits** (15-20 requests/minute). During evaluation runs with promptfoo, you'll hit these limits quickly and see `429 RESOURCE_EXHAUSTED` errors. OpenRouter provides free models without these restrictions.

---

## 1. Environment Setup

### Step 1: Install Dependencies (from repo root)

```bash
cd /path/to/llm-course
make install                          # Creates .venv at repo root
```

### Step 2: Activate Virtual Environment

<details>
<summary><strong> Linux / macOS (bash/zsh)</strong></summary>

```bash
source .venv/bin/activate
```
</details>

<details>
<summary><strong> Windows (PowerShell)</strong></summary>

```powershell
.\.venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
</details>

<details>
<summary><strong> Windows (Command Prompt)</strong></summary>

```cmd
.venv\Scripts\activate.bat
```
</details>

### Step 3: Configure API Keys

```bash
cp .env.example .env
# Edit .env and add your keys:
#   GEMINI_API_KEY=your-gemini-key
#   OPENROUTER_API_KEY=your-openrouter-key   # Recommended!
#   MODEL_ID=gemini-2.5-flash
```

### Step 4: Navigate to Project and Verify

```bash
cd project
python -m unittest discover tests -v
```

**Expected output:**
```
test_run_blocks_on_input_guard ... ok
test_run_handles_tool_and_returns_steps ... ok
...
Ran 6 tests in 0.031s
OK
```

---

## 2. Understanding the Project Structure

```
project/
├── src/
│   ├── app.py              # Main entrypoint (routes to RAG or Agent)
│   ├── rag/app.py          # RAG implementation with citations
│   ├── agent/app.py        # Agent implementation with tool calls
│   └── common/
│       ├── guards.py       # Input/output guardrails
│       └── logger.py       # JSON logging for replay
├── tests/
│   ├── prompts/            # Promptfoo evaluation prompts
│   │   ├── rag_question.json
│   │   └── attack_prompt.json
│   ├── test_rag_app.py     # Unit tests for RAG
│   ├── test_agent_app.py   # Unit tests for Agent
│   └── test_entrypoint.py  # Integration tests
├── tools/
│   ├── metrics.py          # Calculate precision/recall from results
│   ├── analyze_results.py  # Debug failures in batch runs
│   └── cleanup.py          # Reset for fresh evaluation run
├── data/corpus/            # RAG knowledge base documents
├── reports/                # Output directory for evaluations
├── promptfooconfig_custom.yaml       # Offline deterministic testing
├── promptfooconfig_openrouter.yaml   # Fast probabilistic evaluation
├── promptfooconfig_gemini_free_tier.yaml  # Gemini with rate-limit handling
└── run_batches_simple.py   # Batch runner with auto-retry
```

---

## 3. Running Locally

> **First**: Make sure you're in the `project/` directory with your virtual environment activated (see Section 1).

### Loading Environment Variables

Before running any commands that need API keys, load your `.env` file:

<details>
<summary><strong> Linux / macOS (bash/zsh)</strong></summary>

```bash
# Option 1: Export all variables from .env
export $(grep -v '^#' ../.env | xargs)

# Option 2: Source if your shell supports it
set -a && source ../.env && set +a
```
</details>

<details>
<summary><strong> Windows (PowerShell)</strong></summary>

```powershell
# Load .env variables into current session
Get-Content ..\.env | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
```

Or use a `.ps1` helper script:
```powershell
# Create load-env.ps1 (one-time)
@'
Get-Content $args[0] | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
'@ | Out-File -FilePath load-env.ps1

# Then use it:
.\load-env.ps1 ..\.env
```
</details>

<details>
<summary><strong> Windows (Command Prompt)</strong></summary>

```cmd
@REM Manually set each variable, or use a batch file:
for /f "tokens=1,2 delims==" %%a in (..\.env) do set %%a=%%b
```
</details>

<details>
<summary><strong> Python (cross-platform, recommended)</strong></summary>

Install `python-dotenv` (already in requirements.txt):
```bash
pip install python-dotenv
```

Then in Python scripts, add at the top:
```python
from dotenv import load_dotenv
load_dotenv('../.env')
```

Or use CLI:
```bash
python -c "from dotenv import load_dotenv; load_dotenv('../.env'); import os; print(os.environ.get('GEMINI_API_KEY', 'NOT SET')[:10] + '...')"
```
</details>

---

### Test RAG Mode

```bash
python -m src.app --track rag --question "What is LLM01?"
```

**Expected output:**
```json
{"answer": "LLM01 refers to Prompt Injection...", "citations": ["001.txt"], "safety": "safe"}
```

### Test Agent Mode
```bash
python -m src.app --track agent --question "Add 12 and 30"
```

**Expected output:**
```json
{"steps": [...], "final_answer": "42", "doc_id": "calc_001"}
```

### Rate Limit Warning

If you see this error:
```
google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
```

This means Gemini's free tier is rate-limited. Solutions:
1. **Wait 1-5 minutes** and try again
2. **Use OpenRouter** (see Section 4 below)
3. **Run unit tests instead** (they use mocks, no API needed)

---

## 4. Evaluation with promptfoo

You have **3 options** for running the evaluation. Choose based on your situation:

| Option | Best For | Time | API Needed | Behavior |
|--------|----------|------|------------|----------|
| **Custom (Offline)** | Testing your setup works | ~2 seconds | None | **Deterministic** |
| **OpenRouter (Fast)** | Reliable real LLM testing | ~2 minutes | Free key | **Probabilistic** |
| **Gemini (Batch)** | Using only Google API | ~25-30 min | Gemini key | **Probabilistic** |

### Understanding Deterministic vs Probabilistic Evaluation

| Type | Meaning | Example |
|------|---------|---------|
| **Deterministic** | Same input → **always** same output | Custom provider: rule-based pattern matching. Run 100 times, get 100 identical results. |
| **Probabilistic** | Same input → **variable** output | Real LLMs (Gemini, OpenRouter): temperature, sampling, model state cause variance. Run 100 times, get slightly different results each time. |

**Why this matters:**
- Use **Custom (deterministic)** to validate your setup and CI pipelines — 100% reproducible
- Use **OpenRouter/Gemini (probabilistic)** to test real-world security — expect 75-90% pass rates
- Document differences in your Written Report to show you understand LLM behavior

### OpenRouter Free Tier: Important Pricing Note

> **Source**: [OpenRouter FAQ - Free Tier Options](https://openrouter.ai/docs/faq#what-free-tier-options-exist)

| Status | Rate Limit | Notes |
|--------|------------|-------|
| **New user (no purchase)** | 50 requests/day total | Very limited, for testing only |
| **After buying $10 credits** | 1000 requests/day on free models | Sufficient for this course |

⚠️ **Recommendation**: Purchase $10 credits once to unlock 1000 req/day. The credits themselves last forever and free models don't consume them — you just need the purchase to unlock higher limits.

---

###  Option 1: Custom Provider (Offline Testing)

**Best for**: Verifying your setup works without any API calls

**Run from repo root** (single copy-paste block):

<details>
<summary><strong> Linux / macOS</strong></summary>

```bash
cd project && \
npx promptfoo eval \
  -c promptfooconfig_custom.yaml \
  -o reports/results_custom.json
```
</details>

<details>
<summary><strong> Windows (PowerShell)</strong></summary>

```powershell
cd project
npx promptfoo eval `
  -c promptfooconfig_custom.yaml `
  -o reports/results_custom.json
```
</details>

**What this does**:
- Uses a mock provider that simulates RAG responses
- Runs instantly (2 seconds)
- Always produces valid JSON with citations
- Perfect for validating your environment before using real APIs

**Expected result**: 100% pass rate (8/8 tests)

---

### Option 2: OpenRouter (Recommended for Real Testing)

**Best for**: Fast, reliable evaluation with real LLMs — no rate limits!

**Run from repo root** (single copy-paste block):

<details>
<summary><strong> Linux / macOS</strong></summary>

```bash
cd project && \
source ../.venv/bin/activate && \
export $(grep -v '^#' ../.env | xargs) && \
npx promptfoo eval \
  -c promptfooconfig_openrouter.yaml \
  -o reports/results_openrouter.json
```
</details>

<details>
<summary><strong> Windows (PowerShell)</strong></summary>

```powershell
cd project
..\.venv\Scripts\Activate.ps1
Get-Content ..\.env | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
npx promptfoo eval `
  -c promptfooconfig_openrouter.yaml `
  -o reports/results_openrouter.json
```
</details>

**What this does**:
- Uses Mistral's free model via OpenRouter
- No rate limits (unlike Gemini free tier)
- Takes ~2 minutes for 8 test cases
- Real LLM responses with actual security reasoning

**Expected result**: 75-87% pass rate (real LLM variability is normal)

---

### Option 3: Gemini Free Tier (Smart Batch Method)

**Best for**: Students who only have a Gemini API key

⚠️ **Important**: Google's free tier has strict rate limits (15-20 RPM). The smart batch runner handles this automatically with **timeout enforcement**, **circuit breaker**, and **auto-fallback to faster models**.

**Run from repo root** (single copy-paste block):

<details>
<summary><strong> Linux / macOS</strong></summary>

```bash
# From repo root - activates venv, loads env, runs batch evaluation
cd project && \
source ../.venv/bin/activate && \
export $(grep -v '^#' ../.env | xargs) && \
python run_batches_simple.py \
  --config promptfooconfig_gemini_free_tier.yaml \
  --batch-size 2 \
  --delay 60 \
  --timeout 120
```
</details>

<details>
<summary><strong> Windows (PowerShell)</strong></summary>

```powershell
# From repo root - activates venv, loads env, runs batch evaluation
cd project
..\.venv\Scripts\Activate.ps1
Get-Content ..\.env | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
python run_batches_simple.py `
  --config promptfooconfig_gemini_free_tier.yaml `
  --batch-size 2 `
  --delay 60 `
  --timeout 120
```
</details>

**Smart Features:**

| Feature | What It Does |
|---------|--------------|
| **Enforced Timeout** | Kills stuck promptfoo after 120s (configurable via `--timeout`) |
| **Auto-Fallback** | Switches to faster model on timeout/503 (Flash-Lite → Pro) |
| **Circuit Breaker** | Stops after 2 consecutive API errors (not test failures!) |
| **Rate Limit Detection** | Detects 429 errors and stops immediately with resume instructions |

> **Note**: Test failures (wrong answers) are **normal** for LLM evaluation. The batch runner continues even with some failures - only API errors (429, 503, timeout) trigger fallback or stopping.

**Command Options:**

```bash
python run_batches_simple.py --help

Options:
  --batch-size N    Tests per batch (default: 2)
  --delay N         Seconds between batches (default: 60)
  --timeout N       Max seconds per batch before killing (default: 120)
  --config FILE     Config file (default: promptfooconfig_gemini_free_tier.yaml)
  --start N         Resume from batch number N
  --model ID        Force specific model (e.g., google:gemini-2.0-flash)
  --no-fallback     Disable auto-fallback to faster models
```

**If tests are slow or timing out:**

```bash
# Option A: Use a faster model explicitly
python run_batches_simple.py \
  --config promptfooconfig_gemini_free_tier.yaml \
  --model google:gemini-2.0-flash \
  --timeout 90

# Option B: Let auto-fallback handle it (default behavior)
# The runner will automatically try faster models if one times out
```

**After completion**, merge and view results:

```bash
python merge_batch_results.py
npx promptfoo view reports/merged_results.json
```

---

### Quick Decision Guide

```
Are you just testing your setup works?
  → Use Option 1 (Custom)

Do you have an OpenRouter API key?
  → Use Option 2 (OpenRouter) - it's free and fast!

Only have Gemini API key?
  → Use Option 3 (Gemini Batch)

Getting 429 rate limit errors?
  → Switch to OpenRouter, or increase --delay to 180
```

---

## 5. Calculate Metrics

After running evaluation:

```bash
python tools/metrics.py reports/results.json reports/metrics.csv
cat reports/metrics.csv
```

**Expected output:**
```csv
metric,value
json_rate,1.000
citation_rate,0.250
safety_field_rate,1.000
```

### CI Gate Thresholds

| Metric | Target | What It Measures |
|--------|--------|------------------|
| `json_rate` | ≥ 0.95 | % of outputs that are valid JSON |
| `safety_field_rate` | ≥ 0.85 | % of outputs with correct safety classification |
| `citation_rate` | ≥ 0.80 | % of RAG outputs with document citations |

---

## 6. Debug Failures

### View Results Dashboard
```bash
npx promptfoo view reports/results.json
```

### Analyze Batch Results
```bash
# See comprehensive analysis of all batches
python tools/analyze_results.py

# Show only failures for debugging
python tools/analyze_results.py --failures-only
```

### Cleanup for Fresh Run
```bash
python tools/cleanup.py
```

---

## 7. Automated Tests

Unit tests use mocks (no API needed):

```bash
# From project directory
python -m unittest discover tests -v

# Or from repo root
make project-test
```

Tests verify:
- Input guards block malicious prompts
- Output validates against JSON schema
- RAG returns citations
- Agent handles tool calls correctly

---

## 8. Publish Your Changes

```bash
# Stage your work
git add -A

# Commit with descriptive message
git commit -m "Final project: RAG guardrails + Agent safety + metrics passing"

# Push to your repository
git push origin main
```

### Required Deliverables Checklist

| Deliverable | Location | Description |
|-------------|----------|-------------|
| ✅ Source code | `src/` | RAG + Agent implementations |
| ✅ Prompts | `tests/prompts/` | JSON chat format prompts |
| ✅ Config | `promptfooconfig*.yaml` | Evaluation configurations |
| ✅ Results | `reports/results.json` | Raw evaluation output |
| ✅ Report | `reports/report.html` | Visual evaluation report |
| ✅ Metrics | `reports/metrics.csv` | Calculated metrics |
| ✅ Logs | `logs.jsonl` | Interaction replay logs |
| ✅ Written Report | (separate) | 3-5 page analysis document |

### Written Report Requirements

Your 3-5 page report **MUST** include:

1. **RAG Architecture Explanation** (REQUIRED)
   - What is RAG? Why is it used?
   - How does your RAG system retrieve documents?
   - How do citations work? Why are they important for security?
   - What happens when RAG can't find relevant documents?

2. **Agent Architecture Explanation** (REQUIRED)
   - What is an LLM Agent? How is it different from RAG?
   - What tools does your agent have access to?
   - How do you prevent the agent from misusing tools?
   - What is the agent's decision-making loop?

3. **Threat Model** — What attacks does your system defend against?
   - Prompt injection (direct and indirect)
   - Data exfiltration attempts
   - Tool misuse in Agent mode

4. **Guardrails Implementation**
   - Input filters: What do they block?
   - Output validation: How do you ensure safe responses?
   - Code examples of your guard functions

5. **Evaluation Results**
   - Metrics achieved (json_rate, citation_rate, safety_field_rate)
   - Failures encountered and how you fixed them
   - Comparison: Custom vs OpenRouter vs Gemini results

6. **OWASP/ATLAS Mapping** — Which LLM risks does your system address?
   - LLM01: Prompt Injection
   - LLM02: Insecure Output Handling
   - LLM06: Sensitive Information Disclosure

---

## 9. Troubleshooting

### Error 429: Rate Limit (RESOURCE_EXHAUSTED)

**Cause**: Too many requests to Google AI Studio (free tier: 15-20 RPM)

**Symptoms**:
```
google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
Error: Request failed after 4 retries: Rate limited
```

**Solutions** (in order of preference):

1. **Switch to OpenRouter** (recommended):
   ```bash
   # Get free key at https://openrouter.ai/keys, add to .env
   npx promptfoo eval -c promptfooconfig_openrouter.yaml -o reports/results.json
   ```

2. **Use the batch runner with longer delays**:
   ```bash
   python run_batches_simple.py \
     --config promptfooconfig_gemini_free_tier.yaml \
     --batch-size 2 \
     --delay 180   # 3 minutes between batches
   ```

3. **Wait and retry**: Rate limits reset every minute. Wait 5 minutes and try again.

---

### Error 503: Model Overloaded

**Cause**: Google servers are overloaded (not your fault!)

**Symptoms**:
```
503: The model is overloaded. Please try again later.
```

**Solutions**:
- The batch runner auto-switches to fallback models
- Or use OpenRouter instead (different infrastructure)

---

### "Invalid JSON from model"

**Cause**: Model returning markdown code blocks instead of raw JSON

**Symptoms**:
```
Invalid JSON from model: ```json\n{...}\n```
```

**Solutions**:
1. Use the `.json` prompt files (not `.txt`)
2. Prompts include "Do not wrap in backticks" instruction
3. If persists, try a different model

---

### Tests Pass but Metrics Are Low

**Cause**: Real LLMs don't always return citations or set safety="unsafe"

**This is normal!** Expected metrics:
- `json_rate`: Should be 1.0 (100%)
- `citation_rate`: 0.25-0.50 is acceptable
- `safety_field_rate`: 1.0 is the target

**To improve citation rate**: Modify prompts to emphasize citation requirements.

---

### promptfoo Command Not Found

**Cause**: Node.js not installed or wrong version

**Fix**:
```bash
# Check Node version (need 22+)
node --version

# Install Node 22 via nvm
nvm install 22
nvm use 22

# Install promptfoo
npm install -g promptfoo

# Or use npx (no global install needed)
npx promptfoo eval -c ...
```

---

### How to Start Fresh

```bash
# Clean up all previous results
python tools/cleanup.py

# Verify clean state
ls reports/

# Run again
npx promptfoo eval -c promptfooconfig_openrouter.yaml -o reports/results.json
```

---

### Batch Runner Stopped Mid-Way

**Cause**: Rate limit hit or network error

**How to resume**:
```bash
# Check which batch failed
ls reports/batches/

# Resume from batch N
python run_batches_simple.py \
  --config promptfooconfig_gemini_free_tier.yaml \
  --batch-size 2 \
  --delay 180 \
  --start N
```

---

## 10. Quick Reference

### Configuration Files (3 options only)

| File | Purpose | Time | Behavior |
|------|---------|------|----------|
| `promptfooconfig_custom.yaml` | Offline testing | ~2s | Deterministic |
| `promptfooconfig_openrouter.yaml` | Fast real LLM | ~2min | Probabilistic |
| `promptfooconfig_gemini_free_tier.yaml` | Gemini batch | ~25min | Probabilistic |

### Complete Workflow

```bash
# ============ SETUP (once) ============
make install && source .venv/bin/activate && cd project
cp ../.env.example ../.env   # Add GEMINI_API_KEY and OPENROUTER_API_KEY

# ============ RUN LOCALLY ============
export $(cat ../.env | xargs)
python -m src.app --track rag --question "What is prompt injection?"
python -m src.app --track agent --question "Calculate 15 + 27"

# ============ EVALUATE ALL 3 OPTIONS (compare results!) ============

# Option 1: Custom (offline, deterministic - always 100%)
npx promptfoo eval -c promptfooconfig_custom.yaml -o reports/results_custom.json

# Option 2: OpenRouter (fast, probabilistic - expect ~75-90%)
npx promptfoo eval -c promptfooconfig_openrouter.yaml -o reports/results_openrouter.json

# Option 3: Gemini (slow, probabilistic - expect ~75-90%)
python run_batches_simple.py \
  --config promptfooconfig_gemini_free_tier.yaml \
  --batch-size 2 --delay 180
python merge_batch_results.py   # Merge batch results

# ============ METRICS ============
python tools/metrics.py reports/results_openrouter.json reports/metrics.csv
cat reports/metrics.csv

# ============ TESTS (no API needed) ============
python -m unittest discover tests -v

# ============ DEBUG ============
python tools/analyze_results.py --failures-only
npx promptfoo view reports/results_openrouter.json
python tools/cleanup.py   # Start fresh
```

---

**Good luck with your final project!** 

