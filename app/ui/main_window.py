from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QSplitter,
    QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont

from core.models import SubtitleSegment, GenerateSettings
from core.srt_parser import parse_srt
from core import api_client
from ui.voice_selector import VoiceSelector
from ui.subtitle_view import SubtitleView
from ui.settings_dialog import SettingsDialog


class VoicesLoader(QThread):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            voices = api_client.get_voices()
            self.finished.emit(voices)
        except Exception as e:
            self.error.emit(str(e))


class GenerateWorker(QThread):
    progress = Signal(int, int)  # current, total
    status = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, segments: list[SubtitleSegment], settings: GenerateSettings):
        super().__init__()
        self.segments = segments
        self.settings = settings
        self._cancel = False

    def run(self):
        try:
            from core.models import TtsJob
            jobs = []
            for i, seg in enumerate(self.segments):
                if self._cancel:
                    return
                jobs.append(TtsJob(
                    segment_index=i,
                    text=seg.text,
                    voice=self.settings.voice,
                    rate=self.settings.rate,
                    volume=self.settings.volume,
                    pitch=self.settings.pitch,
                ))
                self.progress.emit(i + 1, len(self.segments))

            self.status.emit("Generating TTS audio...")
            segments_data = [
                {"start_frame": s.start_frame, "end_frame": s.end_frame}
                for s in self.segments
            ]
            results = api_client.generate_batch(jobs, segments_data=segments_data)

            if self._cancel:
                return

            self.status.emit("Placing audio on timeline...")
            files = [r["path"] for r in results]
            targets = [{"start_seconds": s.start_seconds} for s in self.segments]
            api_client.place_audio_on_timeline(files, targets, track_index=2)

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancel = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoVoice")
        self.setMinimumSize(800, 600)

        self._voices_loader = None
        self._generate_worker = None

        self._setup_ui()
        self._check_backend()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        title = QLabel("AutoVoice")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        subtitle = QLabel("AI Voice-over Generator for DaVinci Resolve")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6b7280; margin-bottom: 10px;")
        main_layout.addWidget(subtitle)

        self.status_indicator = QLabel("Checking backend...")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_indicator)

        splitter = QSplitter(Qt.Vertical)

        self.voice_selector = VoiceSelector()
        splitter.addWidget(self.voice_selector)

        self.subtitle_view = SubtitleView()
        self.subtitle_view.generate_requested.connect(self._on_generate)
        self.subtitle_view.load_srt_btn.clicked.connect(self._on_load_srt)
        splitter.addWidget(self.subtitle_view)

        splitter.setSizes([200, 400])
        main_layout.addWidget(splitter, 1)

        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.progress_label = QLabel("")
        bottom_bar.addWidget(self.progress_label)

        self.settings_btn = QPushButton("TTS Settings")
        self.settings_btn.clicked.connect(self._on_open_settings)
        bottom_bar.addWidget(self.settings_btn)

        main_layout.addLayout(bottom_bar)

        self.statusBar().showMessage("Ready")

    def _check_backend(self):
        backend_ok = api_client.check_health()
        resolve_version = api_client.check_resolve()

        if backend_ok and resolve_version:
            self.status_indicator.setText(f"Backend + Resolve connected (Lua v{resolve_version})")
            self.status_indicator.setStyleSheet("color: #16a34a; font-weight: bold;")
            self._load_voices()
        elif backend_ok:
            self.status_indicator.setText("Backend connected — run AutoVoice script in Resolve")
            self.status_indicator.setStyleSheet("color: #ca8a04; font-weight: bold;")
            self._load_voices()
        elif resolve_version:
            self.status_indicator.setText("Resolve connected — start backend: cargo run")
            self.status_indicator.setStyleSheet("color: #ca8a04; font-weight: bold;")
        else:
            self.status_indicator.setText("Neither backend nor Resolve running")
            self.status_indicator.setStyleSheet("color: #dc2626; font-weight: bold;")

    def _load_voices(self):
        self.statusBar().showMessage("Loading voices...")
        self._voices_loader = VoicesLoader()
        self._voices_loader.finished.connect(self._on_voices_loaded)
        self._voices_loader.error.connect(self._on_voices_error)
        self._voices_loader.start()

    def _on_open_settings(self):
        dialog = SettingsDialog(self)
        dialog.load()
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.statusBar().showMessage("TTS settings saved")
            self._load_voices()

    @Slot(list)
    def _on_voices_loaded(self, voices):
        self.voice_selector.set_voices(voices)
        self.statusBar().showMessage(f"Loaded {len(voices)} voices")

    @Slot(str)
    def _on_voices_error(self, error):
        self.status_indicator.setText(f"Voice load failed: {error}")
        self.status_indicator.setStyleSheet("color: #dc2626; font-weight: bold;")
        self.statusBar().showMessage(f"Failed to load voices: {error}")

    def _load_sample_subtitles(self):
        segments = [
            SubtitleSegment(1, 0, 90, "Welcome to this video tutorial.", 0.0, 3.0),
            SubtitleSegment(2, 90, 210, "Today we will learn about DaVinci Resolve.", 3.0, 7.0),
            SubtitleSegment(3, 210, 360, "Let's get started with the basics.", 7.0, 12.0),
            SubtitleSegment(4, 360, 510, "First, open your project timeline.", 12.0, 17.0),
            SubtitleSegment(5, 510, 660, "Navigate to the media pool on the left.", 17.0, 22.0),
        ]
        self.subtitle_view.set_segments(segments, source="sample")
        self.statusBar().showMessage(f"Loaded {len(segments)} sample segments")

    def _on_load_srt(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load SRT File",
            "",
            "SRT Files (*.srt);;All Files (*)",
        )
        if not path:
            return

        try:
            fps = 30.0
            try:
                import httpx as _hx
                _r = _hx.post(
                    api_client._get_lua_url(),
                    json={"func": "GetTimelineInfo"},
                    timeout=5.0,
                )
                if _r.status_code == 200:
                    _d = _r.json()
                    if _d.get("ok") and _d.get("timeline", {}).get("fps", 0) > 0:
                        fps = _d["timeline"]["fps"]
            except Exception:
                pass
            segments = parse_srt(path, fps=fps)
            if not segments:
                QMessageBox.warning(
                    self,
                    "No Subtitles",
                    "The file was loaded but no subtitle entries were found.",
                )
                return

            import os
            name = os.path.basename(path)
            self.subtitle_view.set_segments(segments, source=name)
            self.statusBar().showMessage(f"Loaded {len(segments)} subtitles from {name}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Failed to Load SRT",
                f"Could not parse the SRT file:\n{e}",
            )

    def _on_generate(self):
        segments = self.subtitle_view.get_segments()
        if not segments:
            return

        settings = self.voice_selector.get_settings()
        if not settings.voice:
            QMessageBox.warning(self, "No Voice", "Please select a voice first.")
            return

        self.subtitle_view.generate_btn.setEnabled(False)
        self.progress_label.setText("Generating...")

        self._generate_worker = GenerateWorker(segments, settings)
        self._generate_worker.progress.connect(self._on_progress)
        self._generate_worker.status.connect(self._on_status)
        self._generate_worker.finished.connect(self._on_generate_done)
        self._generate_worker.error.connect(self._on_generate_error)
        self._generate_worker.start()

    @Slot(int, int)
    def _on_progress(self, current, total):
        self.progress_label.setText(f"Generating: {current}/{total}")
        self.statusBar().showMessage(f"Generating segment {current} of {total}...")

    @Slot(str)
    def _on_status(self, msg):
        self.statusBar().showMessage(msg)

    @Slot(list)
    def _on_generate_done(self, results):
        self.subtitle_view.generate_btn.setEnabled(True)
        self.progress_label.setText(f"Done — {len(results)} files placed on timeline")
        self.statusBar().showMessage("Voiceover placed on timeline!")

    @Slot(str)
    def _on_generate_error(self, error):
        self.subtitle_view.generate_btn.setEnabled(True)
        self.progress_label.setText("Error")
        self.statusBar().showMessage(f"Generation failed: {error}")
        QMessageBox.critical(self, "Generation Failed", error)
