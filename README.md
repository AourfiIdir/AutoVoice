# AutoVoice

AI Voice-over Generator for DaVinci Resolve.

Load an SRT subtitle file, pick a voice, and AutoVoice generates TTS audio for each subtitle and places it on your timeline — all from within Resolve.

<img width="1892" height="1414" alt="Capture d’écran 2026-08-18 225637" src="https://github.com/user-attachments/assets/fd1f2bda-5414-4bad-bcfb-1298c1012ead" />

Tips for improving the software :)

<a href='https://ko-fi.com/O8E325CVRX' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

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

## Download

| Platform | Installer |
|---|---|
| 🪟 Windows | [AutoSubs-windows-x86_64.exe](https://github.com/tmoroney/auto-subs/releases/latest/download/AutoSubs-windows-x86_64.exe) |

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
- [x] Python/PySide6 frontend with voice selector
- [x] SRT parser with timeline-aware FPS
- [x] Lua bridge for Resolve integration
- [x] File-based IPC (stable communication)
- [x] Automatic audio track creation
- [x] PyInstaller single-exe packaging
- [x] Inno Setup installer
- [ ] Subtitle duration sync
- [ ] Real-time preview
- [ ] Multi-language support

## Setup

### Prerequisites

- **DaVinci Resolve** (Studio or Free)
- **Rust** toolchain ([rustup.rs](https://rustup.rs))
- **Python 3.12+** ([python.org](https://python.org))
- **Inno Setup 6** ([jrsoftware.org](https://jrsoftware.org/isdl.php))
- **Git** (optional)

### Build from Source (Windows)

All commands run in **Windows CMD or PowerShell** (not WSL).

#### 1. Build the Rust backend

```bash
cd backend
cargo build --release
```

Output: `backend/target/release/autovoice-server.exe`

#### 2. Set up the Python frontend

```bash
cd app
python -m venv venv-win
venv-win\Scripts\pip install -r requirements.txt
venv-win\Scripts\pip install pyinstaller
```

#### 3. Build the Python exe with PyInstaller

```bash
cd app
venv-win\Scripts\pyinstaller.exe autovoice.spec --noconfirm
```

Output: `app/dist/AutoVoice.exe`

#### 4. Build the installer with Inno Setup

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\autovoice.iss
```

Or use the build script for all steps at once:

```bash
build.bat
```

Output: `installer_output/AutoVoice_Setup_0.1.0.exe`

### What Gets Installed

```
%LOCALAPPDATA%\AutoVoice\
├── AutoVoice.exe            # Python GUI (PyInstaller)
├── AutoVoice.lua            # Lua launcher
├── launch.bat               # Starts backend + frontend
├── backend\
│   └── autovoice-server.exe # Rust TTS backend
└── modules\
    ├── autovoice_server.lua # Lua HTTP server for Resolve
    ├── ljsocket.lua         # TCP socket library
    └── dkjson.lua           # JSON library

%APPDATA%\...\Fusion\Scripts\Utility\
└── AutoVoice.lua            # Launcher (appears in Resolve Script menu)
```

### Resolve Integration

1. Run the installer — it automatically places `AutoVoice.lua` in Resolve's Script Utility folder
2. Open DaVinci Resolve → Script menu → click **AutoVoice**

If the script doesn't appear, restart Resolve.

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
- **Packaging** — PyInstaller, Inno Setup

## License

MIT
