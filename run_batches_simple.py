#!/usr/bin/env python3
"""
Smart batch runner for promptfoo evaluations with:
- Per-batch timeout enforcement (kills stuck promptfoo processes)
- Circuit breaker (stops after consecutive failures)
- Auto-fallback to faster models on timeout/503
- Proper cross-platform signal handling

Usage:
    python run_batches_simple.py --batch-size 2 --delay 60 --timeout 120
    
    # With auto-fallback enabled (default):
    python run_batches_simple.py --config promptfooconfig_gemini_free_tier.yaml
    
    # Disable auto-fallback:
    python run_batches_simple.py --no-fallback
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import yaml
from pathlib import Path

# ==============================================================================
# MODEL FALLBACK CONFIGURATION
# ==============================================================================
# Main model: google:gemini-2.5-flash (balanced speed/capability)
# Fallback order: fastest → slowest (try lighter models first on timeout/503)
FALLBACK_MODELS = [
    ("google:gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (Fastest, lower load)"),
    ("google:gemini-3-pro-preview", "Gemini 3 Pro Preview (More heavy capacity)"),
    ("google:gemini-2.5-pro", "Gemini 2.5 Pro (More capacity)"),
]

# Circuit breaker: stop if this many consecutive batches fail
MAX_CONSECUTIVE_FAILURES = 2


def load_tests(test_file="_generated/tests_flat.yaml"):
    """Load all tests from the YAML file."""
    with open(test_file, 'r') as f:
        tests = yaml.safe_load(f)
    return tests


def split_into_batches(tests, batch_size=6):
    """Split tests into batches of specified size."""
    batches = []
    for i in range(0, len(tests), batch_size):
        batches.append(tests[i:i+batch_size])
    return batches


def create_batch_file(batch, batch_num, output_dir="_generated"):
    """Create a temporary batch YAML file."""
    os.makedirs(output_dir, exist_ok=True)
    batch_file = os.path.join(output_dir, f"batch_{batch_num:02d}_temp.yaml")
    
    with open(batch_file, 'w') as f:
        yaml.dump(batch, f, default_flow_style=False, allow_unicode=True)
    
    return batch_file


def create_batch_config(base_config, batch_file, batch_num, output_dir="reports/batches", fallback_model=None):
    """Create a temporary config file pointing to the batch."""
    os.makedirs(output_dir, exist_ok=True)
    config_file = os.path.join(output_dir, f"_temp_config_batch_{batch_num:02d}.yaml")
    
    # Load the config as YAML to properly extract non-test sections
    with open(base_config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Remove inline tests - we'll point to the batch file instead
    config.pop('tests', None)
    
    # Convert relative paths to absolute paths in prompts
    # Use the directory of the config file, not cwd (in case script is run from different dir)
    config_dir = os.path.dirname(os.path.abspath(base_config))
    if 'prompts' in config:
        new_prompts = []
        for prompt in config['prompts']:
            if isinstance(prompt, str):
                # Handle file:// paths
                if prompt.startswith('file://prompts/'):
                    prompt = f'file://{config_dir}/prompts/' + prompt[len('file://prompts/'):]
                elif prompt.startswith('file://tests/prompts/'):
                    prompt = f'file://{config_dir}/tests/prompts/' + prompt[len('file://tests/prompts/'):]
            new_prompts.append(prompt)
        config['prompts'] = new_prompts
    
    # Switch to fallback model if specified
    if fallback_model and 'providers' in config:
        for provider in config['providers']:
            if isinstance(provider, dict) and 'id' in provider:
                if provider['id'].startswith('google:gemini-'):
                    provider['id'] = fallback_model
    
    # Add the tests file reference
    batch_file_abs = os.path.abspath(batch_file)
    config['tests'] = f'file://{batch_file_abs}'
    
    # Write the new config
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return config_file


def check_api_errors(output_json):
    """Check if batch results contain 429 rate limit or 503 service unavailable errors."""
    try:
        if not os.path.exists(output_json):
            return None, 0, 0
        
        with open(output_json, 'r') as f:
            data = json.load(f)
            results = data.get('results', {}).get('results', [])
            
            rate_limit_count = 0
            service_unavailable_count = 0
            
            for result in results:
                error = str(result.get('response', {}).get('error', ''))
                if '429' in error or 'Rate limit' in error.lower() or 'Too Many Requests' in error:
                    rate_limit_count += 1
                elif '503' in error or 'Service Unavailable' in error or 'overloaded' in error.lower():
                    service_unavailable_count += 1
            
            if rate_limit_count > 0:
                return '429_rate_limit', rate_limit_count, 0
            elif service_unavailable_count > 0:
                return '503_overloaded', 0, service_unavailable_count
            return None, 0, 0
    except Exception as e:
        print(f"⚠️  Could not check for API errors: {e}")
        return None, 0, 0


def run_batch(config_file, batch_num, output_dir="reports/batches", timeout_seconds=120):
    """
    Run promptfoo evaluation for one batch with ENFORCED timeout.
    
    Unlike promptfoo's built-in timeoutSeconds (which is often ignored),
    this uses subprocess timeout + SIGTERM/SIGKILL to actually kill stuck processes.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    output_json = os.path.join(output_dir, f"batch_{batch_num:02d}_results.json")
    output_html = os.path.join(output_dir, f"batch_{batch_num:02d}_report.html")
    
    cmd = [
        "npx", "promptfoo", "eval",
        "-c", config_file,
        "-o", output_json,
        "-o", output_html
    ]
    
    print(f"\n{'='*70}")
    print(f"🚀 Running Batch {batch_num} (timeout: {timeout_seconds}s)")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")
    
    start_time = time.time()
    process = None
    
    try:
        # Start process (don't capture output to show real-time progress)
        process = subprocess.Popen(
            cmd,
            stdout=None,  # Show in real-time
            stderr=None,
            text=True,
            # Create new process group on Unix for proper cleanup
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        # Wait with timeout
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f"\n⏱️  TIMEOUT! Batch {batch_num} exceeded {timeout_seconds}s (took {elapsed:.0f}s)")
            
            # Kill the process group (includes child npx/node processes)
            if os.name != 'nt':
                # Unix: kill entire process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(2)  # Give it time to cleanup
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead
            else:
                # Windows: just terminate
                process.terminate()
                time.sleep(2)
                process.kill()
            
            return {"batch_num": batch_num, "status": "timeout", "elapsed": elapsed}
        
        elapsed = time.time() - start_time
        
        # Check for API errors in output file
        error_type, rate_limit_count, service_503_count = check_api_errors(output_json)
        
        if error_type == '429_rate_limit':
            print(f"\n🚨 RATE LIMIT DETECTED in Batch {batch_num}!")
            print(f"   {rate_limit_count} API calls hit 429 Too Many Requests")
            return {
                "batch_num": batch_num, 
                "status": "rate_limited", 
                "elapsed": elapsed,
                "error_count": rate_limit_count,
                "error_type": "429"
            }
        elif error_type == '503_overloaded':
            print(f"\n⚠️  SERVICE OVERLOADED in Batch {batch_num}!")
            print(f"   {service_503_count} API calls hit 503 Service Unavailable")
            return {
                "batch_num": batch_num, 
                "status": "service_overloaded", 
                "elapsed": elapsed,
                "error_count": service_503_count,
                "error_type": "503"
            }
        
        if return_code == 0:
            print(f"\n✅ Batch {batch_num} completed in {elapsed:.1f}s")
            return {"batch_num": batch_num, "status": "success", "elapsed": elapsed}
        else:
            print(f"\n❌ Batch {batch_num} failed (exit code {return_code})")
            return {"batch_num": batch_num, "status": "failed", "elapsed": elapsed}
    
    except Exception as e:
        print(f"\n💥 Batch {batch_num} error: {e}")
        if process and process.poll() is None:
            process.kill()
        return {"batch_num": batch_num, "status": "error", "error": str(e)}


def _try_fallback_models(args, batch_file, batch_num, results, timeout_seconds, current_model=None):
    """
    Try fallback models in order (fastest to slowest).
    Returns the successful model ID, or None if all failed.
    """
    print("\n🔄 AUTO-FALLBACK: Trying faster models...")
    print("   Available fallback models (fastest → slowest):")
    for idx, (model_id, desc) in enumerate(FALLBACK_MODELS, 1):
        marker = " ← current" if model_id == current_model else ""
        print(f"      {idx}. {desc}{marker}")
    
    # Find current model index and start from a faster one
    current_idx = -1
    for idx, (model_id, _) in enumerate(FALLBACK_MODELS):
        if model_id == current_model:
            current_idx = idx
            break
    
    # Try models starting from the fastest
    for idx, (fallback_model_id, fallback_desc) in enumerate(FALLBACK_MODELS):
        # Skip the current model (we already tried it)
        if fallback_model_id == current_model:
            continue
        
        print(f"\n   ✨ Trying: {fallback_desc}")
        print(f"      Model ID: {fallback_model_id}")
        
        # Create config with fallback model
        fallback_config = create_batch_config(
            args.config, batch_file, batch_num, fallback_model=fallback_model_id
        )
        
        retry_result = run_batch(fallback_config, batch_num, timeout_seconds=timeout_seconds)
        
        # "success" = all tests passed, "failed" = some tests didn't pass but MODEL WORKED
        # Both are acceptable - we only retry on API errors (timeout, 429, 503)
        if retry_result["status"] in ["success", "failed"]:
            if retry_result["status"] == "success":
                print(f"\n   ✅ SUCCESS with {fallback_desc}!")
            else:
                print(f"\n   ✅ MODEL WORKED with {fallback_desc} (some tests didn't pass - normal)")
            results[-1] = retry_result  # Replace the result
            return fallback_model_id  # Return successful model
        elif retry_result["status"] == "timeout":
            print(f"      ⏱️  {fallback_desc} also timed out")
        elif retry_result["status"] in ["rate_limited", "service_overloaded"]:
            print(f"      ❌ {fallback_desc} hit API limits")
        else:
            print(f"      ❌ {fallback_desc} error: {retry_result.get('status')}")
    
    print("\n   ❌ ALL FALLBACK MODELS FAILED")
    return None


def _save_partial_and_exit(results, batch_num, total_batches, args):
    """Save partial results and exit with helpful message."""
    os.makedirs("reports/batches", exist_ok=True)
    summary_file = "reports/batches/batch_summary_partial.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("💾 PARTIAL RESULTS SAVED")
    print(f"{'='*70}")
    print(f"   File: {summary_file}")
    print(f"   Completed: {batch_num - 1}/{total_batches} batches\n")
    print("💡 TO RESUME:")
    print(f"   python run_batches_simple.py --start {batch_num} --config {args.config}\n")
    print("💡 ALTERNATIVE - Use OpenRouter (different infrastructure, no limits):")
    print("   python run_batches_simple.py --config promptfooconfig_openrouter.yaml\n")
    print(f"{'='*70}\n")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Smart batch runner for promptfoo evaluations with timeout enforcement and auto-fallback"
    )
    parser.add_argument("--batch-size", type=int, default=2, help="Tests per batch (default: 2)")
    parser.add_argument("--delay", type=int, default=60, help="Seconds between batches (default: 60)")
    parser.add_argument("--timeout", type=int, default=120, help="Max seconds per batch before killing (default: 120)")
    parser.add_argument("--config", type=str, default="promptfooconfig_gemini_free_tier.yaml", help="Base config file")
    parser.add_argument("--tests", type=str, default=None, help="Test file to split (optional - uses inline tests if not provided)")
    parser.add_argument("--start", type=int, default=None, help="Start from batch number")
    parser.add_argument("--end", type=int, default=None, help="End at batch number")
    parser.add_argument("--no-fallback", action="store_true", help="Disable auto-fallback to faster models on timeout")
    parser.add_argument("--model", type=str, default=None, help="Override model ID (e.g., google:gemini-2.0-flash)")
    
    args = parser.parse_args()
    
    # For Project, tests are typically inline in the config YAML
    # If no separate test file is provided, extract tests from config or run without batching
    if args.tests:
        # Load tests from external file (like Lab 2 structure)
        print(f"📂 Loading tests from {args.tests}...")
        tests = load_tests(args.tests)
        print(f"✅ Loaded {len(tests)} tests")
        
        # Split into batches
        batches = split_into_batches(tests, args.batch_size)
        total_batches = len(batches)
        print(f"📦 Split into {total_batches} batches of {args.batch_size} tests each\n")
    else:
        # Project mode: tests are inline in the config YAML
        # Load tests from the config file itself
        print(f"📂 Loading inline tests from {args.config}...")
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
            tests = config.get('tests', [])
            print(f"✅ Found {len(tests)} inline tests in config")
        except Exception as e:
            print(f"❌ Could not load tests from config: {e}")
            sys.exit(1)
        
        if not tests:
            print("❌ No tests found in config file. Use --tests to specify external test file.")
            sys.exit(1)
        
        # Split into batches
        batches = split_into_batches(tests, args.batch_size)
        total_batches = len(batches)
        print(f"📦 Split into {total_batches} batches of {args.batch_size} tests each\n")
    
    # Determine range
    start_idx = (args.start - 1) if args.start else 0
    end_idx = args.end if args.end else total_batches
    
    results = []
    consecutive_api_errors = 0  # Circuit breaker for API errors ONLY (429, 503, timeout)
    current_model = args.model  # Optional model override
    
    # Show configuration summary
    print(f"\n{'='*70}")
    print("⚙️  CONFIGURATION")
    print(f"{'='*70}")
    print(f"   Batch size: {args.batch_size} tests per batch")
    print(f"   Delay: {args.delay}s between batches")
    print(f"   Timeout: {args.timeout}s per batch (hard kill if exceeded)")
    print(f"   Auto-fallback: {'DISABLED' if args.no_fallback else 'ENABLED'}")
    if current_model:
        print(f"   Model override: {current_model}")
    print(f"{'='*70}\n")
    
    # Run each batch
    for i in range(start_idx, end_idx):
        batch_num = i + 1
        batch = batches[i]
        
        print(f"\n{'#'*70}")
        print(f"# BATCH {batch_num}/{total_batches} ({len(batch)} tests)")
        print(f"{'#'*70}\n")
        
        # Create batch files
        batch_file = create_batch_file(batch, batch_num)
        config_file = create_batch_config(args.config, batch_file, batch_num, fallback_model=current_model)
        
        # Run the batch with enforced timeout
        result = run_batch(config_file, batch_num, timeout_seconds=args.timeout)
        results.append(result)
        
        # ==============================================================
        # SMART ERROR HANDLING - Only act on API/infrastructure errors
        # Test failures (wrong answers) are NORMAL - we continue!
        # API errors (429, 503, timeout) trigger fallback/circuit breaker
        # ==============================================================
        
        if result["status"] == "success":
            consecutive_api_errors = 0  # Reset circuit breaker
            
        elif result["status"] == "timeout":
            consecutive_api_errors += 1
            elapsed = result.get("elapsed", args.timeout)
            
            print(f"\n{'='*70}")
            print(f"⏱️  TIMEOUT at batch {batch_num} ({elapsed:.0f}s > {args.timeout}s limit)")
            print(f"{'='*70}")
            
            if args.no_fallback:
                print("   Auto-fallback is disabled (--no-fallback)")
                if consecutive_api_errors >= MAX_CONSECUTIVE_FAILURES:
                    print(f"\n🚨 CIRCUIT BREAKER: {consecutive_api_errors} consecutive API errors")
                    print("   Stopping to prevent wasted time.\n")
                    _save_partial_and_exit(results, batch_num, total_batches, args)
            else:
                # Try faster model
                print("   🔄 Trying faster fallback model...")
                retry_success = _try_fallback_models(
                    args, batch_file, batch_num, results, args.timeout, current_model
                )
                if retry_success:
                    consecutive_api_errors = 0
                    current_model = retry_success  # Use this model for future batches
                else:
                    if consecutive_api_errors >= MAX_CONSECUTIVE_FAILURES:
                        print(f"\n🚨 CIRCUIT BREAKER: {consecutive_api_errors} consecutive failures")
                        _save_partial_and_exit(results, batch_num, total_batches, args)
        
        elif result["status"] == "rate_limited":
            print(f"\n\n{'='*70}")
            print("🚨 RATE LIMIT HIT - STOPPING EXECUTION")
            print(f"{'='*70}")
            print(f"\n⚠️  Google AI Studio rate limit exceeded at batch {batch_num}")
            print(f"   {result.get('error_count', 0)} API calls returned 429 errors\n")
            print("🛑 DON'T WASTE YOUR TIME - The rate limit is active NOW!\n")
            print("💡 SOLUTIONS:\n")
            print("   1. WAIT 1 HOUR for rate limit to reset")
            print(f"      Then resume: python run_batches_simple.py --start {batch_num} --config {args.config}")
            print(f"\n   2. USE OPENROUTER (different infrastructure, no limits)")
            print("      python run_batches_simple.py --config promptfooconfig_openrouter.yaml")
            print(f"\n{'='*70}\n")
            _save_partial_and_exit(results, batch_num, total_batches, args)
            
        elif result["status"] == "service_overloaded":
            consecutive_api_errors += 1
            
            print(f"\n{'='*70}")
            print("⚠️  MODEL OVERLOADED at batch {batch_num}".format(batch_num=batch_num))
            print(f"{'='*70}")
            
            if args.no_fallback:
                print("   Auto-fallback is disabled (--no-fallback)")
                if consecutive_api_errors >= MAX_CONSECUTIVE_FAILURES:
                    _save_partial_and_exit(results, batch_num, total_batches, args)
            else:
                retry_success = _try_fallback_models(
                    args, batch_file, batch_num, results, args.timeout, current_model
                )
                if retry_success:
                    consecutive_api_errors = 0
                    current_model = retry_success
                else:
                    if consecutive_api_errors >= MAX_CONSECUTIVE_FAILURES:
                        _save_partial_and_exit(results, batch_num, total_batches, args)
        
        elif result["status"] == "failed":
            # "failed" = promptfoo ran but some tests didn't pass
            # This is NORMAL for LLM evaluation - don't stop, just continue!
            print(f"   ℹ️  Some tests didn't pass - this is normal LLM variance")
            # Don't increment consecutive_api_errors - this isn't an API error
        
        elif result["status"] == "error":
            # "error" = something went wrong (not 429/503/timeout which are handled above)
            consecutive_api_errors += 1
            print(f"   ⚠️  Unexpected error in batch {batch_num}")
            if consecutive_api_errors >= MAX_CONSECUTIVE_FAILURES:
                print(f"\n🚨 CIRCUIT BREAKER: {consecutive_api_errors} consecutive errors")
                _save_partial_and_exit(results, batch_num, total_batches, args)
        
        # Cooling delay (except for the last batch)
        # Apply delay after ALL batches (success or failed), not just success
        if i < end_idx - 1 and result["status"] in ["success", "failed"]:
            print(f"\n❄️  Cooling down for {args.delay} seconds...\n")
            time.sleep(args.delay)
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📊 BATCH RUN SUMMARY")
    print(f"{'='*70}\n")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    error_count = sum(1 for r in results if r["status"] in ["timeout", "error"])
    
    print(f"Total batches: {len(results)}")
    print(f"✅ Successes: {success_count}")
    print(f"❌ Failures: {failed_count}")
    print(f"💥 Errors: {error_count}")
    
    if success_count == len(results):
        print(f"\n🎉 All batches completed successfully!")
    
    print(f"\n📁 Results saved to: reports/batches/")
    print(f"{'='*70}\n")
    
    # Save summary
    summary_file = "reports/batches/batch_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"📄 Summary saved to: {summary_file}\n")
    
    # Merge batch results into single file
    if success_count > 0:
        print(f"\n{'='*70}")
        print("🔄 MERGING BATCH RESULTS")
        print(f"{'='*70}\n")
        
        import glob
        batch_files = sorted(glob.glob("reports/batches/batch_*_results.json"))
        if batch_files:
            try:
                # Import merge function from merge_batch_results
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from merge_batch_results import merge_results
                
                merge_results(batch_files, "reports/merged_results.json")
                print("\n✅ To view unified dashboard, run:")
                print("   npx promptfoo view reports/merged_results.json\n")
            except Exception as e:
                print(f"⚠️  Could not auto-merge: {e}")
                print("   Run manually: python merge_batch_results.py\n")


if __name__ == "__main__":
    main()
