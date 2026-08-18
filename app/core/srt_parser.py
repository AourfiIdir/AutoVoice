import re
from core.models import SubtitleSegment


def parse_srt(file_path: str, fps: float = 30.0) -> list[SubtitleSegment]:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    segments = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        time_line = lines[1]
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
            time_line,
        )
        if not match:
            continue

        g = match.groups()
        start_ms = (
            int(g[0]) * 3600000
            + int(g[1]) * 60000
            + int(g[2]) * 1000
            + int(g[3])
        )
        end_ms = (
            int(g[4]) * 3600000
            + int(g[5]) * 60000
            + int(g[6]) * 1000
            + int(g[7])
        )

        start_seconds = start_ms / 1000.0
        end_seconds = end_ms / 1000.0
        start_frame = int(round(start_seconds * fps))
        end_frame = int(round(end_seconds * fps))

        text = " ".join(lines[2:]).strip()
        text = re.sub(r"<[^>]+>", "", text)

        if text:
            segments.append(SubtitleSegment(
                index=len(segments) + 1,
                start_frame=start_frame,
                end_frame=end_frame,
                text=text,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            ))

    return segments
