from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QPushButton, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from core.models import Voice, GenerateSettings


class VoiceSelector(QWidget):
    settings_changed = Signal(GenerateSettings)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._voices: list[Voice] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Voice Settings")
        group_layout = QVBoxLayout()

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.currentIndexChanged.connect(self._on_setting_changed)
        voice_row.addWidget(self.voice_combo, 1)
        group_layout.addLayout(voice_row)

        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Speed:"))
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(-50, 100)
        self.rate_slider.setValue(0)
        self.rate_slider.setTickPosition(QSlider.TicksBelow)
        self.rate_slider.setTickInterval(10)
        self.rate_slider.valueChanged.connect(self._on_setting_changed)
        self.rate_label = QLabel("+0%")
        self.rate_slider.valueChanged.connect(
            lambda v: self.rate_label.setText(f"{v:+d}%")
        )
        rate_row.addWidget(self.rate_slider, 1)
        rate_row.addWidget(self.rate_label)
        group_layout.addLayout(rate_row)

        pitch_row = QHBoxLayout()
        pitch_row.addWidget(QLabel("Pitch:"))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-50, 50)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.valueChanged.connect(self._on_setting_changed)
        self.pitch_label = QLabel("+0Hz")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_label.setText(f"{v:+d}Hz")
        )
        pitch_row.addWidget(self.pitch_slider, 1)
        pitch_row.addWidget(self.pitch_label)
        group_layout.addLayout(pitch_row)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(-50, 50)
        self.volume_slider.setValue(0)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.valueChanged.connect(self._on_setting_changed)
        self.volume_label = QLabel("+0%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v:+d}%")
        )
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_label)
        group_layout.addLayout(volume_row)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def set_voices(self, voices: list[Voice]):
        self._voices = voices
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        for v in voices:
            label = v.name if v.name else v.short_name
            gender = f" ({v.gender})" if v.gender else ""
            self.voice_combo.addItem(f"{label}{gender}", v.short_name)
        self.voice_combo.blockSignals(False)
        self._on_setting_changed()

    def get_settings(self) -> GenerateSettings:
        idx = self.voice_combo.currentIndex()
        voice = self._voices[idx].short_name if idx >= 0 and idx < len(self._voices) else ""
        return GenerateSettings(
            voice=voice,
            rate=f"{self.rate_slider.value():+d}%",
            volume=f"{self.volume_slider.value():+d}%",
            pitch=f"{self.pitch_slider.value():+d}Hz",
        )

    def _on_setting_changed(self):
        self.settings_changed.emit(self.get_settings())
