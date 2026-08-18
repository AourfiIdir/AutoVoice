from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Voice:
    name: str
    short_name: str
    gender: str
    locale: str


@dataclass
class SubtitleSegment:
    index: int
    start_frame: int
    end_frame: int
    text: str
    start_seconds: float = 0.0
    end_seconds: float = 0.0


@dataclass
class TtsJob:
    segment_index: int
    text: str
    voice: str
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    audio_path: Optional[str] = None
    duration_ms: int = 0


@dataclass
class TimelineInfo:
    name: str = ""
    fps: float = 30.0
    start_frame: int = 0
    end_frame: int = 0
    track_count: int = 0
    project_name: str = ""


@dataclass
class GenerateSettings:
    voice: str = "en-US-GuyNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
