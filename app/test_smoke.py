"""Smoke test for the AutoVoice backend + frontend api_client.

Usage:
    python app/test_smoke.py

Starts the backend, exercises every endpoint (health, config, voices,
generate, audio fetch, batch, cleanup), then shuts it down.

TTS synthesis needs internet. If the TTS provider is unreachable the
synthesis checks are reported as SKIP instead of FAIL so you can still
see the rest of the pipeline verified. A FAIL means something is
actually broken.

Optional: BACKEND_EXE=path/to/autovoice-server to override binary lookup.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import httpx
from core import api_client

RESULTS: list[tuple[str, str, str]] = []
ORIGINAL_CONFIG = None


def record(name: str, status: str, detail: str = ""):
    RESULTS.append((name, status, detail))
    print(f"  [{status:5s}] {name}" + (f" — {detail}" if detail else ""))


def find_backend() -> Path:
    env = os.environ.get("BACKEND_EXE")
    if env:
        p = Path(env)
        if p.exists():
            return p
        raise FileNotFoundError(f"BACKEND_EXE does not exist: {p}")
    on_windows = os.name == "nt"
    name = "autovoice-server.exe" if on_windows else "autovoice-server"
    candidates = [
        ROOT / "backend" / "target" / "debug" / name,
        ROOT / "backend" / "target" / "release" / name,
        ROOT / "backend" / "autovoice-server.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("autovoice-server binary not found — build it first: cd backend && cargo build")


def wait_healthy(timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_client.check_health():
            return True
        time.sleep(0.25)
    return False


def is_network_error(text: str) -> bool:
    text = text.lower()
    return any(
        kw in text
        for kw in [
            "connect",
            "connection",
            "timeout",
            "timed out",
            "dns",
            "unreachable",
            "no route",
            "failed to connect",
            "error 3004",
            "websocket",
            "send request",
        ]
    )


def main() -> int:
    exe = find_backend()
    print(f"Backend: {exe}")

    if api_client.check_health():
        print("A backend is already answering on 56133 — refusing to touch it.")
        return 2

    logf = tempfile.NamedTemporaryFile(prefix="autovoice-test-", suffix=".log", delete=False)
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        stdin=subprocess.DEVNULL,
        stdout=logf,
        stderr=logf,
    )
    print(f"Log: {logf.name}")

    import atexit

    def teardown():
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        logf.close()

    atexit.register(teardown)

    if not wait_healthy():
        record("server startup", "FAIL", "did not become healthy — see log")
        print_result()
        return 1
    record("server startup", "PASS")

    try:
        run_checks()
    except Exception as exc:
        record("fatal", "FAIL", f"{exc}\n{traceback.format_exc()}")
    finally:
        if ORIGINAL_CONFIG is not None:
            try:
                api_client.set_tts_config(ORIGINAL_CONFIG)
                record("config restored", "PASS")
            except Exception as exc:
                record("config restore", "FAIL", str(exc))

    print_result()
    return 1 if any(s == "FAIL" for _, s, _ in RESULTS) else 0


def run_checks():
    global ORIGINAL_CONFIG

    health = api_client.check_health()
    record("GET /health (check_health)", "PASS" if health else "FAIL")

    cfg = api_client.get_tts_config()
    expected_fields = {"provider", "openai_api_key", "openai_model", "elevenlabs_api_key", "elevenlabs_model"}
    if cfg.provider == "edge" and expected_fields == set(cfg.to_dict().keys()):
        record("GET /config defaults", "PASS")
    else:
        record("GET /config defaults", "FAIL", str(cfg.to_dict()))

    ORIGINAL_CONFIG = cfg

    from core.models import TtsConfig

    scratch = TtsConfig(
        provider="openai",
        openai_api_key="sk-invalid-test",
        openai_model="tts-1",
        elevenlabs_api_key="",
        elevenlabs_model="eleven_multilingual_v2",
    )
    api_client.set_tts_config(scratch)
    got = api_client.get_tts_config()
    if got.provider == "openai" and got.openai_api_key == "sk-invalid-test":
        record("PUT /config roundtrip", "PASS")
    else:
        record("PUT /config roundtrip", "FAIL", str(got.to_dict()))

    voices = api_client.get_voices()
    if voices and all(v.name and v.short_name for v in voices):
        record("GET /voices (openai)", "PASS", f"{len(voices)} voices")
    else:
        record("GET /voices (openai)", "FAIL", f"got {len(voices)}")

    try:
        api_client.generate_tts("provider routing works", voice="alloy")
        record("generate routed to OpenAI", "FAIL", "expected error with invalid key")
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        if "401" in body or "OpenAI error" in body:
            record("generate routed to OpenAI", "PASS", "backend rejects bad key (401)")
        else:
            record("generate routed to OpenAI", "FAIL", body)
    except httpx.HTTPError as exc:
        if is_network_error(str(exc)):
            record("generate routed to OpenAI", "SKIP", "no network to api.openai.com")
        else:
            record("generate routed to OpenAI", "FAIL", str(exc))

    api_client.set_tts_config(ORIGINAL_CONFIG)
    voices = api_client.get_voices()
    if voices and all(v.name and v.short_name for v in voices):
        record("GET /voices (edge restored)", "PASS", f"{len(voices)} voices")
    else:
        record("GET /voices (edge restored)", "FAIL", f"got {len(voices)}")

    audio_id = None
    try:
        result = api_client.generate_tts("This is a smoke test.", voice="en-US-GuyNeural")
        audio_id = result.get("id")
        record("POST /generate (edge)", "PASS", f"id={audio_id}")
    except httpx.HTTPStatusError as exc:
        if is_network_error(exc.response.text):
            record("POST /generate (edge)", "SKIP", "no network to Edge TTS")
        else:
            record("POST /generate (edge)", "FAIL", exc.response.text)
    except httpx.HTTPError as exc:
        if is_network_error(str(exc)):
            record("POST /generate (edge)", "SKIP", "no network to Edge TTS")
        else:
            record("POST /generate (edge)", "FAIL", str(exc))

    if audio_id:
        r = httpx.get(f"{api_client.BACKEND_URL}/audio/{audio_id}", timeout=30.0)
        r.raise_for_status()
        data = r.content
        is_mp3 = data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
        if data and is_mp3:
            record("GET /audio/{id} (mp3)", "PASS", f"{len(data)} bytes")
        else:
            record("GET /audio/{id} (mp3)", "FAIL", f"{len(data)} bytes, not mp3")

        missing = httpx.get(f"{api_client.BACKEND_URL}/audio/does-not-exist", timeout=10.0)
        record("GET /audio unknown -> 404", "PASS" if missing.status_code == 404 else "FAIL",
               str(missing.status_code))

        from core.models import TtsJob

        jobs = [TtsJob(0, "First batch line.", "en-US-GuyNeural"), TtsJob(1, "Second batch line.", "en-US-GuyNeural")]
        segments = [{"start_frame": 0.0, "end_frame": 90.0}, {"start_frame": 90.0, "end_frame": 180.0}]
        try:
            results = api_client.generate_batch(jobs, segments_data=segments)
            if len(results) == 2 and all(r.get("id") for r in results):
                record("POST /generate-batch", "PASS", f"{len(results)} clips")
            else:
                record("POST /generate-batch", "FAIL", str(results))
        except httpx.HTTPStatusError as exc:
            if is_network_error(exc.response.text):
                record("POST /generate-batch", "SKIP", "no network to Edge TTS")
            else:
                record("POST /generate-batch", "FAIL", exc.response.text)
        except httpx.HTTPError as exc:
            if is_network_error(str(exc)):
                record("POST /generate-batch", "SKIP", "no network to Edge TTS")
            else:
                record("POST /generate-batch", "FAIL", str(exc))
    else:
        record("POST /generate-batch", "SKIP", "skipped because single generate had no audio")

    try:
        r = httpx.post(f"{api_client.BACKEND_URL}/cleanup", timeout=10.0)
        r.raise_for_status()
        removed = r.json().get("removed")
        record("POST /cleanup", "PASS", f"{removed} files removed")
    except Exception as exc:
        record("POST /cleanup", "FAIL", str(exc))


def print_result():
    failed = [r for r in RESULTS if r[1] == "FAIL"]
    print()
    print(f"{'=' * 50}")
    print(f"Passed: {sum(1 for r in RESULTS if r[1] == 'PASS')}  "
          f"Skipped: {sum(1 for r in RESULTS if r[1] == 'SKIP')}  "
          f"Failed: {len(failed)}")
    if failed:
        print("FAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
    print("=" * 50)


if __name__ == "__main__":
    sys.exit(main())