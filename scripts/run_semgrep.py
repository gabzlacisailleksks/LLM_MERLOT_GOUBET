#!/usr/bin/env python3
import json, subprocess, argparse, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
reports = root / "reports"
reports.mkdir(exist_ok=True)


def build_cmd():
    cmd = [
        "semgrep",
        "--config", "p/kubernetes",
        "--config", "p/dockerfile",
        "--config", str(root / "config" / "semgrep_rules.yml"),
        "--json",
        str(root),
    ]
    # TODO: narrow or expand targets/configs here to reflect the IaC stack your team is responsible for.
    return cmd


def run(after: bool = False, *, runner=subprocess.run, report_dir: Path = reports) -> Path:
    out = report_dir / ("semgrep_after.json" if after else "semgrep.json")
    try:
        res = runner(build_cmd(), capture_output=True, text=True, check=False)
        text = res.stdout.strip()
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
        if res.returncode not in (0, 1):
            print(f"semgrep exit code {res.returncode}: see stderr below", file=sys.stderr)
            print(res.stderr, file=sys.stderr)
    except FileNotFoundError:
        print("Semgrep not found. Install with: pip install semgrep", file=sys.stderr)
        sys.exit(2)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--after", action="store_true", help="Write *_after.json")
    args = parser.parse_args()
    run(after=args.after)


if __name__ == "__main__":
    main()
