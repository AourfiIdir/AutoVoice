from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QAbstractItemView, QFileDialog, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from core.models import SubtitleSegment


class SubtitleView(QWidget):
    generate_requested = Signal()
    srt_loaded = Signal(str)  # emits file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: list[SubtitleSegment] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.track_label = QLabel("No subtitles loaded")
        header.addWidget(self.track_label)
        header.addStretch()

        self.load_srt_btn = QPushButton("Load SRT File")
        self.load_srt_btn.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; "
            "padding: 6px 14px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #047857; }"
        )
        header.addWidget(self.load_srt_btn)

        self.generate_btn = QPushButton("Generate Voiceover")
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; "
            "padding: 8px 16px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:disabled { background-color: #6b7280; }"
        )
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        header.addWidget(self.generate_btn)

        layout.addLayout(header)

        hint = QLabel(
            "Export subtitles from DaVinci Resolve  \u2192  "
            "right-click subtitle track  \u2192  Export Subtitle  \u2192  "
            "load the .srt file here"
        )
        hint.setStyleSheet(
            "color: #9ca3af; font-style: italic; padding: 4px 0;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #374151;")
        layout.addWidget(sep)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def set_segments(self, segments: list[SubtitleSegment], source: str = ""):
        self._segments = segments
        self.table.setRowCount(len(segments))

        for i, seg in enumerate(segments):
            self.table.setItem(i, 0, QTableWidgetItem(str(seg.index)))
            self.table.setItem(i, 1, QTableWidgetItem(
                self._format_time(seg.start_seconds)
            ))
            self.table.setItem(i, 2, QTableWidgetItem(
                self._format_time(seg.end_seconds)
            ))
            self.table.setItem(i, 3, QTableWidgetItem(seg.text))

        label = f"{len(segments)} subtitle segments"
        if source:
            label += f"  \u2014  {source}"
        self.track_label.setText(label)
        self.generate_btn.setEnabled(len(segments) > 0)

    def _format_time(self, seconds: float) -> str:
        m = int(seconds) // 60
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def get_segments(self) -> list[SubtitleSegment]:
        return self._segments
