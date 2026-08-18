# AutoVoice

AI Voice-over Generator for DaVinci Resolve.

Load an SRT subtitle file, pick a voice, and AutoVoice generates TTS audio for each subtitle and places it on your timeline — all from within Resolve.

## Architecture

```
┌────────────────────┐     HTTP/JSON      ┌────────────────────┐
│  Python/PyQt UI    │ ◄─────────────────► │  Rust Backend      │
│  (Voice, SRT, ...) │    :56133          │  (Edge TTS API)    │
└────────────────────┘                    └─────────┬──────────┘
                                                    │ File I/O
┌────────────────────┐    File-based jobs           │
│  Lua Script        │ ◄────────────────────────────┘
│  (DaVinci Resolve) │
│                    │    reads autovoice_jobs.json
│  Imports & places  │    writes autovoice_results.json
│  audio on timeline │
└────────────────────┘
```

**Three components:**

| Component | Language | Role |
|-----------|----------|------|
| **Backend** | Rust (Axum) | TTS generation via Edge TTS, audio file management |
| **Frontend** | Python (PySide6) | UI for voice selection, SRT loading, generation |
| **Bridge** | Lua | Runs inside Resolve — imports audio, places clips on timeline |

Communication between the Python frontend and the Lua bridge uses **file-based IPC** (`autovoice_jobs.json` / `autovoice_results.json`) to avoid socket stability issues inside Resolve's scripting environment.

## Features

- 400+ voices via Edge TTS (free, no API key)
- Load any SRT subtitle file
- Voice selection with gender/locale filtering
- Adjustable speed, pitch, and volume
- Automatic audio placement on a new Resolve timeline track
- Media Pool organized into an "AutoVoice" folder
- Clips placed back-to-back (concatenated)

## Status

Prototype / Work in Progress.

- [x] Rust TTS backend with batch generation
- [x] Python/PyQt frontend with voice selector
- [x] SRT parser with timeline-aware FPS
- [x] Lua bridge for Resolve integration
- [x] File-based IPC (stable communication)
- [x] Automatic audio track creation
- [ ] Installer / executable packaging
- [ ] Subtitle duration sync
- [ ] Real-time preview
- [ ] Multi-language support

## Project Structure

```
AutoVoice/
├── app/                          # Python frontend
│   ├── core/
│   │   ├── api_client.py         # HTTP + file-based IPC client
│   │   ├── models.py             # Data models
│   │   └── srt_parser.py         # SRT file parser
│   ├── ui/
│   │   ├── main_window.py        # Main window + generation worker
│   │   ├── voice_selector.py     # Voice picker widget
│   │   └── subtitle_view.py      # Subtitle table widget
│   ├── main.py                   # Entry point
│   └── venv-win/                 # Windows Python venv
├── backend/                      # Rust TTS backend
│   ├── src/
│   │   ├── main.rs               # Axum server entry
│   │   ├── api/routes.rs         # HTTP handlers
│   │   ├── audio/convert.rs      # Audio file management
│   │   ├── config.rs             # Configuration
│   │   └── tts/edge.rs           # Edge TTS integration
│   └── Cargo.toml
├── Resolve-integration/          # DaVinci Resolve scripts
│   └── modules/
│       ├── autovoice_server.lua  # TCP server + Resolve API bridge
│       ├── ljsocket.lua          # TCP socket library
│       └── dkjson.lua            # JSON library
├── installer/                    # Inno Setup scripts
├── AutoVoice.lua                 # Resolve script entry point
└── ARCHITECTURE.md               # Detailed architecture docs
```

## Setup

### Prerequisites

- **DaVinci Resolve** (Studio or Free)
- **Rust** toolchain (for building the backend)
- **Python 3.12+** with pip

### Backend

```bash
cd backend
cargo build --release
```

The binary will be at `backend/target/release/autovoice-server.exe`.

### Frontend

```bash
cd app
python -m venv venv-win
venv-win\Scripts\activate
pip install PySide6 httpx
```

### Resolve Integration

1. Copy `AutoVoice.lua` to:
   ```
   %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
   ```

2. Open DaVinci Resolve → Workspace → Console → Run `AutoVoice`

   This starts the backend, frontend, and Lua server automatically.

## Usage

1. Open a project in DaVinci Resolve with a timeline
2. Run the `AutoVoice` script from the Script menu
3. In the AutoVoice UI:
   - Select a voice
   - Load an SRT subtitle file
   - Click **Generate**
4. Audio clips appear on a new track in your timeline

## Tech Stack

- **Rust** — Axum, tokio, edge-tts-rust
- **Python** — PySide6, httpx
- **Lua** — ljsocket (TCP), dkjson (JSON)
- **TTS** — Microsoft Edge TTS (free, 400+ voices)

## License

MIT
