from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt

from core.models import TtsConfig
from core import api_client

PROVIDER_OPENAI_MODELS = ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]
PROVIDER_ELEVENLABS_MODELS = [
    "eleven_multilingual_v2",
    "eleven_multilingual_v1",
    "eleven_turbo_v2_5",
    "eleven_turbo_v2",
    "eleven_flash_v2_5",
]


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TTS Settings")
        self.setMinimumWidth(460)
        self._config: TtsConfig | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        hint = QLabel(
            "Pick your TTS provider and paste your API key.\n"
            "The key is stored locally in config.json next to the backend."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6b7280;")
        layout.addWidget(hint)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Edge TTS (free, no key)", "edge")
        self.provider_combo.addItem("OpenAI", "openai")
        self.provider_combo.addItem("ElevenLabs", "elevenlabs")
        self.provider_combo.currentIndexChanged.connect(self._update_form_visibility)
        layout.addWidget(QLabel("Provider:"))
        layout.addWidget(self.provider_combo)

        self.openai_group = QGroupBox("OpenAI")
        openai_form = QFormLayout()
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("sk-...")
        self.openai_model = QComboBox()
        self.openai_model.addItems(PROVIDER_OPENAI_MODELS)
        openai_form.addRow("API key:", self.openai_key)
        openai_form.addRow("Model:", self.openai_model)
        self.openai_group.setLayout(openai_form)

        self.elevenlabs_group = QGroupBox("ElevenLabs")
        elevenlabs_form = QFormLayout()
        self.elevenlabs_key = QLineEdit()
        self.elevenlabs_key.setEchoMode(QLineEdit.Password)
        self.elevenlabs_key.setPlaceholderText("xi-...")
        self.elevenlabs_model = QComboBox()
        self.elevenlabs_model.addItems(PROVIDER_ELEVENLABS_MODELS)
        elevenlabs_form.addRow("API key:", self.elevenlabs_key)
        elevenlabs_form.addRow("Model:", self.elevenlabs_model)
        self.elevenlabs_group.setLayout(elevenlabs_form)

        layout.addWidget(self.openai_group)
        layout.addWidget(self.elevenlabs_group)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    @property
    def selected_provider(self) -> str:
        return self.provider_combo.currentData()

    def _update_form_visibility(self):
        provider = self.selected_provider
        self.openai_group.setVisible(provider == "openai")
        self.elevenlabs_group.setVisible(provider == "elevenlabs")

    def _current_config(self) -> TtsConfig:
        return TtsConfig(
            provider=self.selected_provider,
            openai_api_key=self.openai_key.text().strip(),
            openai_model=self.openai_model.currentText(),
            elevenlabs_api_key=self.elevenlabs_key.text().strip(),
            elevenlabs_model=self.elevenlabs_model.currentText(),
        )

    def load(self):
        try:
            self._config = api_client.get_tts_config()
        except Exception as e:
            QMessageBox.critical(self, "Config Error", f"Could not read backend config:\n{e}")
            self.reject()
            return

        provider = self._config.provider
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        self.openai_key.setText(self._config.openai_api_key)
        mi = self.openai_model.findText(self._config.openai_model)
        if mi >= 0:
            self.openai_model.setCurrentIndex(mi)

        self.elevenlabs_key.setText(self._config.elevenlabs_api_key)
        mi = self.elevenlabs_model.findText(self._config.elevenlabs_model)
        if mi >= 0:
            self.elevenlabs_model.setCurrentIndex(mi)

        self._update_form_visibility()

    def _on_save(self):
        cfg = self._current_config()
        if cfg.provider in ("openai", "elevenlabs") and not (
            cfg.openai_api_key if cfg.provider == "openai" else cfg.elevenlabs_api_key
        ):
            QMessageBox.warning(self, "Missing API key", "Please enter your API key for the selected provider.")
            return
        try:
            api_client.set_tts_config(cfg)
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save config:\n{e}")
            return
        self._config = cfg
        self.accept()