#!/usr/bin/env python3
import json, subprocess, argparse, sys, shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
reports = root / "reports"
reports.mkdir(exist_ok=True)


def build_cmd():
    # Find checkov executable in PATH
    checkov_path = shutil.which("checkov")
    if not checkov_path:
        raise FileNotFoundError("checkov not found in PATH")
    
    cmd = [
        checkov_path,
        "-d", str(root / "terraform"),
        "-d", str(root / "k8s"),
        "-d", str(root / "docker"),
        "--output", "json",
    ]
    # TODO: adjust directories/output flags if you introduce new IaC targets or prefer SARIF output.
    return cmd


def run(after: bool = False, *, runner=subprocess.run, report_dir: Path = reports) -> Path:
    out = report_dir / ("checkov_after.json" if after else "checkov.json")
    try:
        res = runner(build_cmd(), capture_output=True, text=True, check=False)
        text = res.stdout.strip()
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
        if res.returncode not in (0, 1):
            print(f"checkov exit code {res.returncode}: see stderr below", file=sys.stderr)
            print(res.stderr, file=sys.stderr)
    except FileNotFoundError:
        print("Checkov not found. Install with: pip install checkov", file=sys.stderr)
        sys.exit(2)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--after", action="store_true", help="Write *_after.json")
    args = parser.parse_args()
    run(after=args.after)


if __name__ == "__main__":
    main()
