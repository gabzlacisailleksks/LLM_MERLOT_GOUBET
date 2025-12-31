"""
Project Security Metrics Calculator

Extracts security metrics from promptfoo results for RAG and Agent evaluation.
Unlike Lab2 (binary is_vuln classification), the project uses multiple metrics:
- safety: Did the model detect prompt injection attacks?
- citation: Did the RAG provide document citations?
- completeness: Did the answer meet minimum length?

Usage:
    python tools/metrics.py results.json metrics.csv
"""
import json, sys, csv
from collections import defaultdict


def main(inp, out_csv):
    with open(inp, encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle promptfoo v3 nested structure: data['results']['results']
    results_container = data.get("results") or {}
    if isinstance(results_container, dict):
        results = results_container.get("results") or []
    else:
        results = results_container
    
    if not results:
        raise SystemExit("No results found in JSON")
    
    # Aggregate metrics from gradingResult.namedScores
    # Each result has: promptIdx, vars (mode, question), gradingResult.namedScores
    metrics = defaultdict(lambda: {"total": 0, "safety_pass": 0, "citation_pass": 0, 
                                    "completeness_pass": 0, "json_valid": 0, "errors": 0})
    
    for r in results:
        promptIdx = r.get("promptIdx", 0)
        vars_ = r.get("vars", {})
        mode = vars_.get("mode", "unknown")
        
        # Get grading result with named scores
        grading = r.get("gradingResult", {})
        named_scores = grading.get("namedScores", {})
        passed = grading.get("pass", False)
        
        metrics[promptIdx]["total"] += 1
        
        # Check if JSON was valid (all results should be JSON)
        response = r.get("response", {})
        if isinstance(response, dict):
            out = response.get("output", "")
        else:
            out = response or ""
        
        try:
            json.loads(out) if isinstance(out, str) else out
            metrics[promptIdx]["json_valid"] += 1
        except:
            metrics[promptIdx]["errors"] += 1
            continue
        
        # Extract individual metric scores (1 = pass, 0 = fail)
        if named_scores.get("safety", 0) >= 1:
            metrics[promptIdx]["safety_pass"] += 1
        if named_scores.get("citation", 0) >= 1:
            metrics[promptIdx]["citation_pass"] += 1
        if named_scores.get("completeness", 0) >= 1:
            metrics[promptIdx]["completeness_pass"] += 1
    
    # Write CSV with rates per prompt
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["promptIdx", "Total", "JSON_Valid", "Safety_Pass", "Citation_Pass", 
                    "Completeness_Pass", "Errors", "Safety_Rate", "Citation_Rate", "Completeness_Rate"])
        
        for pidx, m in sorted(metrics.items()):
            total = m["total"]
            json_valid = m["json_valid"]
            safety = m["safety_pass"]
            citation = m["citation_pass"]
            completeness = m["completeness_pass"]
            errors = m["errors"]
            
            # Calculate rates (avoid division by zero)
            safety_rate = safety / total if total > 0 else 0.0
            citation_rate = citation / total if total > 0 else 0.0
            completeness_rate = completeness / total if total > 0 else 0.0
            
            w.writerow([pidx, total, json_valid, safety, citation, completeness, errors,
                        f"{safety_rate:.3f}", f"{citation_rate:.3f}", f"{completeness_rate:.3f}"])
    
    # Print summary
    total_all = sum(m["total"] for m in metrics.values())
    safety_all = sum(m["safety_pass"] for m in metrics.values())
    citation_all = sum(m["citation_pass"] for m in metrics.values())
    completeness_all = sum(m["completeness_pass"] for m in metrics.values())
    
    print(f"Wrote {out_csv}")
    print(f"\n📊 Summary across all prompts:")
    print(f"   Total tests: {total_all}")
    print(f"   Safety detections: {safety_all}/{total_all} ({100*safety_all/total_all:.1f}%)" if total_all else "")
    print(f"   Citation provided: {citation_all}/{total_all} ({100*citation_all/total_all:.1f}%)" if total_all else "")
    print(f"   Completeness: {completeness_all}/{total_all} ({100*completeness_all/total_all:.1f}%)" if total_all else "")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/metrics.py results.json metrics.csv")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])
