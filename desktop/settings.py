import json, os
from pathlib import Path

APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "G-Labs-Flow-Video-Generator"
FILE = APP_DIR / "settings.json"

DEFAULTS = {
    "base_url": "http://127.0.0.1:8765",
    "api_key": "",
    "output_dir": str(Path.home() / "Documents" / "G-Labs Studio" / "output" / "flow-video"),
    "concurrency": 1,
    "wait_seconds": 10,
    "poll_seconds": 4,
    "timeout_seconds": 1800,
}

def load():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        return DEFAULTS.copy()
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        out = DEFAULTS.copy()
        out.update(data)
        return out
    except Exception:
        return DEFAULTS.copy()

def save(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
