Lab 3 Student Runbook — Config & IaC Security (Checkov + Semgrep + Gemini)
=======================================================
> Author : Badr TAJINI - LLM Cybersecurity - ECE 2025/2026

**Goal:** Scan **Terraform**, **Kubernetes**, and **Dockerfile** for security misconfigurations, fix at least **3 issues**, re-scan, and document the improvement.

---

## Table of Contents

1. [Prerequisites](#0-prerequisites)
2. [Getting Started](#1-getting-started)
3. [Baseline Scans](#2-baseline-scans)
4. [Understanding Findings](#3-understanding-findings)
5. [Applying Fixes](#4-applying-fixes)
6. [Re-scan After Fixes](#5-re-scan-after-fixes)
7. [Gemini Remediation (Optional)](#6-gemini-remediation-optional)
8. [Troubleshooting](#7-troubleshooting)
9. [Deliverables](#deliverables-checklist)

---

## 0. Prerequisites (do these before class)

- **Python 3.11+** installed locally (3.11-3.13 supported)
- **Node.js 22+ LTS** — For promptfoo eval in Final Project
- A Google **Gemini API key** from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (optional for AI remediation)
- Basic terminal and Git familiarity

Optional but recommended:

- Visual Studio Code or another editor with Jupyter support.
- A GitHub account if you plan to push lab artifacts to a remote repo.

### No Cloud Accounts Needed
This lab uses **static analysis only**. You do NOT need:
- AWS account
- Kubernetes cluster (microk8s is optional)
- Terraform state files

---

## 1. Getting Started

### Step 1: Clone and Navigate
```bash
# Clone the course repository
git clone https://github.com/btajini/llm-course.git
cd llm-course

# Or navigate if already cloned
cd llm-course/labs/lab3
```

### Step 2: Activate the Shared Virtual Environment
The course uses a **single shared venv** at the repository root:

```bash
# From repo root (llm-course/)
make install                    # Creates .venv and installs all dependencies
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1

# Verify activation - should show (.venv) prefix
which python
```

### Step 3: Navigate to Lab 3
```bash
cd labs/lab3
```

### Step 4: (Optional) Configure Gemini
```bash
# From repo root - .env is shared across all labs
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

---

## 2. Baseline Scans

Run both scanners to see what security issues exist in the starter code:

### Checkov Scan (Terraform + K8s + Dockerfile)
```bash
python scripts/run_checkov.py
```

**Expected output:**
```
Wrote /path/to/reports/checkov.json
```

### Semgrep Scan (Custom Rules)
```bash
python scripts/run_semgrep.py
```

**Expected output:**
```
Wrote /path/to/reports/semgrep.json
```

### View Summary
```bash
# Count failed checks
grep -c '"result": "FAILED"' reports/checkov.json
# Count Semgrep findings
python -c "import json; d=json.load(open('reports/semgrep.json')); print(f'{len(d.get(\"results\",[]))} findings')"
```

---

## 3. Understanding Findings

### Files to Fix

| File | Issues |
|------|--------|
| `terraform/main.tf` | Public S3 bucket, open security group, overly permissive IAM |
| `k8s/deployment.yaml` | `nginx:latest` tag, `privileged: true` container |
| `docker/Dockerfile` | `ubuntu:latest`, running as root, piping curl to shell |

### Critical Issues to Fix

1. **S3 Bucket with `acl = "public-read"`** → Change to `private` or remove ACL
2. **Security Group open to `0.0.0.0/0`** → Restrict to specific IPs
3. **Kubernetes `privileged: true`** → Set to `false`
4. **Kubernetes `allowPrivilegeEscalation: true`** → Set to `false`
5. **Docker `FROM ubuntu:latest`** → Pin to specific version
6. **Docker `USER root`** → Create and use non-root user

---

## 4. Applying Fixes

### Example Fix 1: Kubernetes Security Context

**Before (k8s/deployment.yaml):**
```yaml
securityContext:
  privileged: true
  allowPrivilegeEscalation: true
```

**After:**
```yaml
securityContext:
  privileged: false
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  readOnlyRootFilesystem: true
```

### Example Fix 2: Pin Docker Image

**Before (docker/Dockerfile):**
```dockerfile
FROM ubuntu:latest
USER root
```

**After:**
```dockerfile
FROM ubuntu:22.04
RUN useradd -m appuser
USER appuser
```

### Example Fix 3: S3 Bucket ACL

**Before (terraform/main.tf):**
```hcl
acl = "public-read"
```

**After:**
```hcl
# Remove the acl line entirely or:
acl = "private"
```

---

## 5. Re-scan After Fixes

After making changes, run the scanners with `--after` flag:

```bash
python scripts/run_checkov.py --after
python scripts/run_semgrep.py --after
```

This creates:
- `reports/checkov_after.json`
- `reports/semgrep_after.json`

### Compare Results
```bash
# Before
grep -c '"result": "FAILED"' reports/checkov.json

# After
grep -c '"result": "FAILED"' reports/checkov_after.json
```

**Goal:** Reduce the number of FAILED checks!

---

## 6. Gemini Remediation (Optional)

If you have a Gemini API key, you can get AI-powered remediation suggestions:

```bash
# Make sure .env has GEMINI_API_KEY
source .env

python src/gemini_remediate.py reports/checkov.json reports/semgrep.json \
  > reports/remediation_suggestions.json
```

**⚠️ Important:** Treat LLM output as untrusted. Always validate fixes by re-scanning!

---

## 7. Troubleshooting

### "Checkov not found"
```bash
pip install checkov
# Or ensure your venv is activated
source .venv/bin/activate
```

### "Semgrep exit code 7"
This is a warning, not an error. Your results are still valid. The exit code indicates findings were found.

### YAML Syntax Error in semgrep_rules.yml
If you see YAML errors, check `config/semgrep_rules.yml` for proper indentation.

### JSON Parse Errors
The checkov output may contain multiple JSON objects. Use `grep` to search for specific patterns rather than `json.load()`.

### "No module named 'src'"
Run from the project root with:
```bash
PYTHONPATH=. python scripts/run_checkov.py
```

---

## 8. Run Automated Tests

```bash
python -m unittest discover tests
```

**Expected output:**
```
test_run_checkov_writes_expected_file ... ok
test_run_semgrep_writes_after_file ... ok
----------------------------------------------------------------------
Ran 2 tests in 0.001s
OK
```

---

## 9. Document Your Work

Create or update `reports/summary.md` with:

| Issue | File | Change Made | Status | Reference |
|-------|------|-------------|--------|-----------|
| Public S3 bucket | terraform/main.tf | Changed acl to private | Fixed | [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html) |
| Privileged container | k8s/deployment.yaml | Set privileged: false | Fixed | [K8s Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) |
| ... | ... | ... | ... | ... |

---

## DELIVERABLES CHECKLIST — What You Must Submit

### This Lab Has the Clearest Before/After Pattern — Follow It Exactly!

The `--after` flag creates separate files so you can compare improvements.

### Step-by-Step Workflow:

```bash
# STEP 1: Run BASELINE scans (before any fixes)
python scripts/run_checkov.py
python scripts/run_semgrep.py
# Creates: reports/checkov.json, reports/semgrep.json

# STEP 2: Count baseline issues
echo "=== BASELINE ISSUES ==="
grep -c '"result": "FAILED"' reports/checkov.json
python -c "import json; d=json.load(open('reports/semgrep.json')); print(f'{len(d.get(\"results\",[]))} Semgrep findings')"

# STEP 3: Fix at least 3 issues across these files:
#   - terraform/main.tf
#   - k8s/deployment.yaml  
#   - docker/Dockerfile

# STEP 4: Run AFTER scans (after your fixes)
python scripts/run_checkov.py --after
python scripts/run_semgrep.py --after
# Creates: reports/checkov_after.json, reports/semgrep_after.json

# STEP 5: Count issues after fixes
echo "=== AFTER FIXES ==="
grep -c '"result": "FAILED"' reports/checkov_after.json
```

### Files to Create:

| File | Description | When to Create |
|------|-------------|----------------|
| `reports/checkov.json` | Baseline Checkov scan (BEFORE fixes) | Step 1 |
| `reports/semgrep.json` | Baseline Semgrep scan (BEFORE fixes) | Step 1 |
| `reports/checkov_after.json` | After-fix Checkov scan | Step 4 |
| `reports/semgrep_after.json` | After-fix Semgrep scan | Step 4 |
| `reports/summary.md` | Issue tracking table (see template above) | During Step 3 |

### Code Files to Fix (at least 3 total):

| File | Example Issues to Fix |
|------|----------------------|
| `terraform/main.tf` | Public S3 ACL, open security group, admin IAM |
| `k8s/deployment.yaml` | `privileged: true`, `latest` tag, no resource limits |
| `docker/Dockerfile` | `FROM ubuntu:latest`, running as root, piping curl to shell |

### Document to Write:

**1-Page Reflection** (`reports/reflection.md` or PDF):

| Section | What to Write |
|---------|---------------|
| **1. Baseline Summary** | How many issues did each scanner find? |
| **2. Fixes Applied** | What 3+ issues did you fix? (use the table above) |
| **3. After Summary** | How many issues remain after fixes? |
| **4. Patterns Observed** | What common misconfigurations did you see? |
| **5. Prevention Ideas** | How could these be prevented in CI/CD? |

### Before Submitting, Verify:

```bash
# From repo root:
make w03-day

# Check your reports folder:
ls reports/
# Should show: checkov.json, semgrep.json, checkov_after.json, 
#              semgrep_after.json, summary.md

# Verify improvement:
echo "BEFORE:" && grep -c '"result": "FAILED"' reports/checkov.json
echo "AFTER:" && grep -c '"result": "FAILED"' reports/checkov_after.json
```

---

## References

- [Checkov Documentation](https://www.checkov.io/1.Welcome/Quick%20Start.html)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/security-checklist/)
- [AWS S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

Good luck hardening the config stack! 
