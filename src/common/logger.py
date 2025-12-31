import json, time
from typing import Any, Dict
from pathlib import Path

LOG_PATH = Path("logs.jsonl")

def log(event: Dict[str, Any]) -> None:
    evt = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    evt.update(event)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
