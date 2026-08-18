# AutoVoice — Architecture & Progress Log

## System Overview

```
┌──────────────────────┐      HTTP/JSON       ┌──────────────────────┐
│   Python/PyQt         │ ◄── 127.0.0.1:56014 ──┤   Rust Backend       │
│   Frontend            │      (port 56014)    │   (axum + tokio)     │
│                       │                      │                      │
│ • Voice selector      │                      │ • edge-tts-rust      │
│ • Subtitle preview    │                      │ • Audio file mgmt    │
│ • Speed/pitch/volume  │                      │ • Format conversion  │
│ • Progress tracking   │                      │ • HTTP API server    │
└──────────────────────┘                      └──────────┬───────────┘
                                                         │ HTTP/JSON
                                                         │ 127.0.0.1:56013
                                              ┌──────────▼───────────┐
                                              │   Lua Script in      │
                                              │   DaVinci Resolve    │
                                              │                      │
                                              │ • Read subtitles     │
                                              │ • Import audio       │
                                              │ • Place on timeline  │
                                              └──────────────────────┘
```

## Component Breakdown

### 1. Rust Backend (`backend/`)

- **Framework:** `axum` (async HTTP) + `tokio` (runtime)
- **TTS:** `edge-tts-rust` crate — direct WebSocket, no Python needed
- **Audio conversion:** `symphonia` crate or shell out to `ffmpeg` for WAV conversion
- **Port:** `56014`

**API Endpoints:**

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /health` | GET | Check if backend is running |
| `GET /voices` | GET | List available Edge TTS voices |
| `POST /generate` | POST | Generate TTS audio from subtitle text, returns audio file path |
| `POST /generate-batch` | POST | Generate audio for multiple subtitle segments |
| `GET /audio/{id}` | GET | Serve generated audio file |
| `DELETE /audio/{id}` | DELETE | Clean up generated audio |
| `POST /import-to-resolve` | POST | Send audio to Lua script for timeline placement |

### 2. Lua Script (`AutoVoice.lua`)

- **Port:** `56132` (changed from 56013 to avoid Windows reserved ports)

**Endpoints:**

| Endpoint | Purpose |
|---|---|
| `Ping` | Health check (done) |
| `GetTimelineInfo` | Timeline metadata (done) |
| `GetSubtitles` | Read subtitle track, return `{segments: [{start, end, text}]}` |
| `GetAudioTracks` | List available audio tracks |
| `ImportAudio` | Import audio file into media pool |
| `PlaceAudioOnTimeline` | Place audio clip at specific frame position on a track |
| `GenerateVoiceover` | Orchestrator: get subtitles → send to backend → place audio |

### 3. Python/PyQt Frontend (`app/`)

- **Framework:** PySide6 (Qt6 for Python)

**UI Components:**

- Subtitle track selector
- Voice picker (with preview play)
- Speed / pitch / volume sliders
- Generate button + progress bar
- Timeline preview (show subtitle ↔ audio alignment)

## Data Flow

```
1. User opens frontend, clicks "Read Subtitles"
2. Frontend → POST /get-subtitles → Lua → reads Resolve timeline → returns segments
3. Frontend displays subtitle segments with timing
4. User selects voice, adjusts settings, clicks "Generate"
5. Frontend → POST /generate-batch → Rust → edge-tts-rust → saves MP3 files
6. Rust → POST /place-audio → Lua → ImportMedia + AppendToTimeline
7. Lua returns success/failure
8. Frontend shows completion
```

## Project Structure

```
autoVoice/
├── AutoVoice.lua                    # Resolve Lua script (existing)
├── app/                             # Python/PyQt frontend
│   ├── main.py                      # Entry point
│   ├── ui/
│   │   ├── main_window.py           # Main window
│   │   ├── voice_selector.py        # Voice picker widget
│   │   └── subtitle_view.py         # Subtitle list widget
│   ├── core/
│   │   ├── api_client.py            # HTTP client for Rust backend
│   │   └── models.py                # Data models
│   ├── resources/
│   │   └── styles.qss               # Qt styles
│   └── requirements.txt
├── backend/                         # Rust backend
│   ├── Cargo.toml
│   ├── src/
│   │   ├── main.rs                  # Entry point + axum server
│   │   ├── tts/
│   │   │   ├── mod.rs               # TTS engine trait
│   │   │   └── edge.rs              # Edge TTS implementation
│   │   ├── audio/
│   │   │   ├── mod.rs               # Audio file management
│   │   │   └── convert.rs           # Format conversion
│   │   ├── api/
│   │   │   ├── mod.rs               # Route handlers
│   │   │   └── routes.rs            # Route definitions
│   │   └── config.rs                # Configuration
│   └── Cargo.lock
├── Resolve-integration/
│   └── modules/
│       ├── ljsocket.lua             # TCP sockets (done)
│       ├── dkjson.lua               # JSON (done)
│       ├── autovoice_core.lua       # Core logic (to build)
│       └── luaresolve.lua           # Resolve helpers (to build)
└── installer/                       # Future installer
```

## Build Order

1. **Rust backend** — get TTS working standalone first
2. **Lua endpoints** — `GetSubtitles` + `PlaceAudioOnTimeline`
3. **Python frontend** — UI to tie it all together
4. **Polish** — error handling, progress, edge cases

## TTS Engine Details

- **Edge TTS** — free, no API key, 400+ voices, WebSocket protocol
- **Output:** MP3 CBR (compatible with Resolve), WAV 48kHz recommended for best compatibility
- **Rust crate:** `edge-tts-rust` v0.1.3
- **Python alternative:** `edge-tts` v7.2.8 (if needed later)
- **Resolve audio support:** WAV, MP3 (CBR only), FLAC, AIFF

## DaVinci Resolve Lua API Key Points

- `mediaPool:ImportMedia({"/path/to/audio.mp3"})` — import files to media pool
- `mediaPool:AppendToTimeline({{mediaPoolItem, startFrame, endFrame, mediaType=2, trackIndex, recordFrame}})` — place audio on timeline
- `mediaType=2` means audio only
- MP3 must be CBR (constant bit rate) to import correctly

---

## Progress Log

### 2026-08-17 — Session 1

**What was done:**
- Created project directory `autoVoice/`
- Wrote `AutoVoice.lua` — HTTP server in Lua for DaVinci Resolve (703 lines)
  - Connects to Resolve API
  - Exposes `Ping` and `GetTimelineInfo` endpoints
  - TCP server on `127.0.0.1:56013`
- Copied `ljsocket.lua` (1320 lines) from AutoSubs to `Resolve-integration/modules/`
- Copied `dkjson.lua` (714 lines) from AutoSubs to `Resolve-integration/modules/`
- Updated `AutoVoice.lua` to reference local modules via absolute path instead of AutoSubs
- Researched Edge TTS protocol, Rust crates, Python library, and Resolve audio import API
- Designed full system architecture (Rust backend + Python frontend + Lua bridge)
- Created this architecture document

**Files created:**
- `AutoVoice.lua` — main Lua script
- `Resolve-integration/modules/ljsocket.lua` — TCP socket library
- `Resolve-integration/modules/dkjson.lua` — JSON library
- `ARCHITECTURE.md` — this file

**Next steps:**
- Build Rust backend with axum + edge-tts-rust
- Implement `GetSubtitles` and `PlaceAudioOnTimeline` Lua endpoints
- Build Python/PyQt frontend

### 2026-08-17 — Session 2

**What was done:**
- Installed Rust toolchain (rustup, rustc 1.97.1, cargo 1.97.1)
- Created full project directory structure (app/, backend/src/tts|audio|api/, installer/)
- Backed up `AutoVoice.lua` → `AutoVoice.lua.bak`
- Created `backend/Cargo.toml` with dependencies: axum 0.8, tokio, edge-tts-rust 0.1.3, serde, uuid, tower-http (cors), tracing, anyhow
- Implemented `backend/src/config.rs` — Config struct with backend_port, resolve_port, resolve_host, audio_dir
- Implemented `backend/src/tts/edge.rs` — TtsEngine wrapping edge-tts-rust
  - `new()` — creates EdgeTtsClient
  - `synthesize(req)` — generates audio bytes from text+voice+rate+pitch+volume
  - `list_voices()` — returns 21 popular Edge TTS voices
  - `SynthesizeRequest` / `SynthesizeResult` / `VoiceInfo` structs
- Implemented `backend/src/audio/convert.rs` — AudioManager for audio files
  - `new(output_dir)` — creates output directory
  - `save_audio(id, data)` — saves MP3 to disk with UUID filename
  - `get_path(id)` / `exists(id)` / `delete(id)` — file operations
  - `cleanup_old_files(max_age_secs)` — removes old files
  - `generate_id()` — UUID v4 generation
- Implemented `backend/src/api/routes.rs` — 7 API endpoints
  - `GET /health` — returns `{ok, service, version}`
  - `GET /voices` — list available voices
  - `POST /generate` — single TTS synthesis → saves MP3 → returns id+path
  - `POST /generate-batch` — batch TTS for multiple subtitle segments
  - `GET /audio/{id}` — serve generated MP3 file
  - `DELETE /audio/{id}` — clean up audio file
  - `POST /cleanup` — clean old files
- Implemented `backend/src/main.rs` — axum server entry point with CORS, Arc state, tracing
- Built successfully — 0 errors, 0 warnings

**Files created:**
- `backend/Cargo.toml`
- `backend/Cargo.lock`
- `backend/src/main.rs`
- `backend/src/config.rs`
- `backend/src/tts/mod.rs`
- `backend/src/tts/edge.rs`
- `backend/src/audio/mod.rs`
- `backend/src/audio/convert.rs`
- `backend/src/api/mod.rs`
- `backend/src/api/routes.rs`
- `app/` directory structure (ui/, core/, resources/)
- `installer/` directory
- `AutoVoice.lua.bak` — backup of original Lua script

**Next steps:**
- Implement `GetSubtitles` and `PlaceAudioOnTimeline` Lua endpoints in AutoVoice.lua
- Build Python/PyQt frontend
- Test full pipeline: Lua ↔ Rust ↔ Edge TTS

### 2026-08-17 — Session 3

**What was done:**
- Set up Python virtual environment (`app/venv/`) with Python 3.12.3
- Installed PySide6 6.11.1 and httpx 0.28.1
- Created `app/requirements.txt`
- Implemented `app/core/models.py` — data models (Voice, SubtitleSegment, TtsJob, TimelineInfo, GenerateSettings)
- Implemented `app/core/api_client.py` — HTTP client for Rust backend
  - `check_health()` — ping backend
  - `get_voices()` — fetch available voices
  - `generate_tts()` — single TTS request
  - `generate_batch()` — batch TTS for multiple segments
- Implemented `app/ui/voice_selector.py` — voice picker with speed/pitch/volume sliders
- Implemented `app/ui/subtitle_view.py` — subtitle table with load/generate buttons
- Implemented `app/ui/main_window.py` — main window with dark theme, backend status, threaded generation
- Implemented `app/main.py` — entry point with Fusion style and dark palette
- All imports verified working

**Files created:**
- `app/requirements.txt`
- `app/main.py`
- `app/core/__init__.py`
- `app/core/models.py`
- `app/core/api_client.py`
- `app/ui/__init__.py`
- `app/ui/voice_selector.py`
- `app/ui/subtitle_view.py`
- `app/ui/main_window.py`

**To run frontend:** `cd app && venv/bin/python main.py`
**To run backend:** `cd backend && cargo run`

### 2026-08-17 — Session 4

**What was done:**
- Implemented `GetSubtitles` endpoint in `AutoVoice.lua`
  - Reads subtitle items from a given track index via `timeline:GetItemListInTrack("subtitle", trackIndex)`
  - Returns per-item: name, startFrame, endFrame, duration
  - Note: subtitle **text content** is NOT accessible via Resolve's Lua API — only timing/metadata
- Implemented `PlaceAudioOnTimeline` endpoint in `AutoVoice.lua`
  - Accepts `files` (array of absolute paths) and `targets` (array of `{recordFrame}`)
  - Imports files into Media Pool via `mediaPool:ImportMedia()`
  - Places on timeline via `mediaPool:AppendToTimeline()` with `mediaType=2` (audio only)
  - Returns count of imported and placed items
- Updated dispatch handler in `AutoVoice.lua` to route `GetSubtitles` and `PlaceAudioOnTimeline` requests

**Lua API endpoints now available:**
| Function | Purpose |
|---|---|
| `Ping` | Health check |
| `GetTimelineInfo` | Timeline name, FPS, frame range |
| `GetSubtitles` | Read subtitle track timing from timeline |
| `PlaceAudioOnTimeline` | Import + place audio clips on timeline |

**Next steps:**
- Connect frontend to Lua endpoints (read subtitles from Resolve, send audio back after generation)
- Test full pipeline end-to-end
- Handle subtitle text input (SRT file or manual entry, since Resolve API can't read subtitle text)

### 2026-08-17 — Session 4

**What was done:**
- Implemented `GetSubtitles` endpoint in `AutoVoice.lua`
  - Reads subtitle items from a given track index via `timeline:GetItemListInTrack("subtitle", trackIndex)`
  - Returns per-item: name, startFrame, endFrame, duration
  - Note: subtitle **text content** is NOT accessible via Resolve's Lua API — only timing/metadata
- Implemented `PlaceAudioOnTimeline` endpoint in `AutoVoice.lua`
  - Accepts `files` (array of absolute paths) and `targets` (array of `{recordFrame}`)
  - Imports files into Media Pool via `mediaPool:ImportMedia()`
  - Places on timeline via `mediaPool:AppendToTimeline()` with `mediaType=2` (audio only)
  - Returns count of imported and placed items
- Updated dispatch handler in `AutoVoice.lua` to route `GetSubtitles` and `PlaceAudioOnTimeline` requests
- Created `app/core/srt_parser.py` — SRT file parser
  - Parses standard SRT format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
  - Converts timestamps to frame numbers using configurable FPS
  - Strips HTML tags from subtitle text
  - Returns list of `SubtitleSegment` objects
- Updated `app/ui/subtitle_view.py` — clear SRT loading workflow
  - Green "Load SRT File" button prominently displayed
  - Instructional hint text: "Export subtitles from DaVinci Resolve → right-click subtitle track → Export Subtitle → load the .srt file here"
  - Separator line between instructions and subtitle table
- Updated `app/ui/main_window.py` — wired SRT file dialog + parser
  - File dialog filters for `.srt` files
  - Shows filename in subtitle count label after loading
  - Error handling for empty or unparseable files
  - Kept sample subtitles accessible for demo/testing

**Installer created:**
- `installer/launch.bat` — launcher that starts Rust backend + Python frontend together
- `installer/build.bat` — pre-build script (builds Rust release, checks venv, verifies files)
- `installer/autovoice.iss` — Inno Setup installer script
  - Copies project to `Program Files\AutoVoice\`
  - Places `AutoVoice.lua` into DaVinci Resolve's Fusion Scripts folder
  - Creates Start Menu + optional Desktop shortcut
  - Post-install: launches AutoVoice

**Installer workflow:**
1. User runs `build.bat` (builds Rust release + checks Python venv)
2. User compiles `autovoice.iss` with Inno Setup
3. User runs the generated `AutoVoice_Setup_0.1.0.exe`
4. In DaVinci Resolve: Workspace → Scripts → AutoVoice
5. Frontend opens, user loads SRT → picks voice → generates voiceover

### 2026-08-17 — Session 5

**What was done:**
- Fixed Rust backend `audio_dir` — was relative (`audio_output`), now uses exe's directory via `std::env::current_exe()`. Prevents audio files going to wrong location when launched from Lua.
- Fixed Lua script `PROJECT_DIR` — was hardcoded, now auto-detects via:
  1. Reading `autovoice.ini` config file next to the script
  2. Looking for `app/main.py` relative to script dir
  3. Hardcoded fallback for dev machine
- Added backend path detection — checks installed path first (`{app}\backend\autovoice-server.exe`), falls back to dev path (`backend\target\release\...`)
- Created Windows Python venv (`app/venv-win/`) — WSL venv had `bin/` instead of `Scripts/`, Python frontend couldn't launch on Windows
- Updated `installer/autovoice.iss` — writes `autovoice.ini` to both install dir and Resolve Scripts dir with correct install path
- Updated `installer/launch.bat` — uses `venv-win` instead of `venv`
- Updated `installer/build.bat` — creates `venv-win` instead of `venv`
- Added startup logging for `PROJECT_DIR` and `MODULES_DIR` in Lua script

**Windows compatibility fixes:**
- Rust backend: `audio_output` path now absolute (relative to exe)
- Lua script: auto-detects project root regardless of install location
- Python frontend: Windows venv with PySide6 installed
- Installer: writes config file so Lua script knows where the project is
