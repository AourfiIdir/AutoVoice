import sys
import os
import json
import time
from pathlib import Path
import httpx
from typing import Optional
from core.models import Voice, TtsJob


BACKEND_URL = "http://127.0.0.1:56133"
LUA_PORT = 56132

if getattr(sys, 'frozen', False):
    _PROJECT_DIR = Path(sys.executable).parent
else:
    _PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

_JOBS_FILE = _PROJECT_DIR / "autovoice_jobs.json"
_RESULTS_FILE = _PROJECT_DIR / "autovoice_results.json"


def _get_lua_url() -> str:
    port_file = str(_PROJECT_DIR / "autovoice_port.txt")
    try:
        with open(port_file, "r") as f:
            port = int(f.read().strip())
            return f"http://127.0.0.1:{port}"
    except Exception:
        return f"http://127.0.0.1:{LUA_PORT}"


def check_health() -> bool:
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        return r.status_code == 200
    except Exception:
        return False


def check_resolve() -> str | None:
    """Returns the Lua server version string, or None if unreachable."""
    try:
        r = httpx.post(
            _get_lua_url(),
            json={"func": "Ping"},
            timeout=5.0,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("version", "unknown")
        return None
    except Exception:
        return None


def get_voices() -> list[Voice]:
    r = httpx.get(f"{BACKEND_URL}/voices", timeout=15.0)
    r.raise_for_status()
    voices = []
    for v in r.json():
        voices.append(Voice(
            name=v.get("name", ""),
            short_name=v.get("short_name", v.get("name", "")),
            gender=v.get("gender", ""),
            locale=v.get("locale", ""),
        ))
    return voices


def generate_tts(
    text: str,
    voice: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> dict:
    r = httpx.post(
        f"{BACKEND_URL}/generate",
        json={
            "text": text,
            "voice": voice,
            "rate": rate,
            "volume": volume,
            "pitch": pitch,
        },
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


def generate_batch(jobs: list[TtsJob], segments_data: list[dict] = None) -> list[dict]:
    body = {
        "segments": [
            {
                "text": j.text,
                "start_frame": segments_data[i]["start_frame"] if segments_data and i < len(segments_data) else 0.0,
                "end_frame": segments_data[i]["end_frame"] if segments_data and i < len(segments_data) else 0.0,
            }
            for i, j in enumerate(jobs)
        ],
        "voice": jobs[0].voice if jobs else "en-US-GuyNeural",
        "rate": jobs[0].rate if jobs else "+0%",
        "volume": jobs[0].volume if jobs else "+0%",
        "pitch": jobs[0].pitch if jobs else "+0Hz",
    }
    r = httpx.post(
        f"{BACKEND_URL}/generate-batch",
        json=body,
        timeout=300.0,
    )
    r.raise_for_status()
    return r.json()["results"]


def place_audio_on_timeline(
    files: list[str],
    targets: list[dict],
    track_index: int = 2,
) -> dict:
    job = {
        "func": "PlaceAudioOnTimeline",
        "files": files,
        "targets": targets,
        "trackIndex": track_index,
    }
    _RESULTS_FILE.unlink(missing_ok=True)
    _JOBS_FILE.write_text(json.dumps(job), encoding="utf-8")
    for _ in range(120):
        if _RESULTS_FILE.exists():
            result = json.loads(_RESULTS_FILE.read_text(encoding="utf-8"))
            _RESULTS_FILE.unlink(missing_ok=True)
            _JOBS_FILE.unlink(missing_ok=True)
            if not result.get("ok"):
                raise RuntimeError(f"Resolve error: {result.get('error', result)}")
            return result
        time.sleep(0.5)
    _JOBS_FILE.unlink(missing_ok=True)
    raise RuntimeError("Timeout waiting for Resolve to place audio on timeline")
