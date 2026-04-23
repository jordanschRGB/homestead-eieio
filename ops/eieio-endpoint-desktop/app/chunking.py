from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class Chunk:
    text: str
    chunk_index: int
    source_name: str
    start_char: int
    end_char: int
    unit_start: int | None = None
    unit_end: int | None = None
    label: str | None = None
    reason: str | None = None


@dataclass
class Unit:
    unit_index: int
    kind: str
    text: str
    start_char: int
    end_char: int


@dataclass
class Segment:
    start_unit: int
    end_unit: int
    label: str | None = None
    reason: str | None = None


SPEAKER_RE = re.compile(r"^[A-Za-z0-9 _.'-]{1,40}:\s+\S")


def split_into_units(text: str) -> list[Unit]:
    if not text.strip():
        return []

    units: list[Unit] = []
    lines = text.splitlines(keepends=True)
    cursor = 0
    unit_index = 0
    block_lines: list[str] = []
    block_start = 0

    def flush_block(end_pos: int):
        nonlocal unit_index, block_lines, block_start
        if not block_lines:
            return
        raw = "".join(block_lines)
        stripped = raw.strip()
        if stripped:
            units.append(
                Unit(
                    unit_index=unit_index,
                    kind="block",
                    text=stripped,
                    start_char=block_start,
                    end_char=end_pos,
                )
            )
            unit_index += 1
        block_lines = []

    for line in lines:
        stripped = line.strip()
        line_start = cursor
        line_end = cursor + len(line)
        is_heading = stripped.startswith("#")
        is_speaker = bool(SPEAKER_RE.match(stripped))

        if not stripped:
            flush_block(line_start)
            cursor = line_end
            continue

        if is_heading or is_speaker:
            flush_block(line_start)
            units.append(
                Unit(
                    unit_index=unit_index,
                    kind="heading" if is_heading else "speaker_turn",
                    text=stripped,
                    start_char=line_start,
                    end_char=line_end,
                )
            )
            unit_index += 1
            cursor = line_end
            continue

        if not block_lines:
            block_start = line_start
        block_lines.append(line)
        cursor = line_end

    flush_block(len(text))
    return units


def chunks_from_segments(text: str, source_name: str, units: list[Unit], segments: list[Segment]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for chunk_index, segment in enumerate(segments):
        start_unit = max(0, segment.start_unit)
        end_unit = min(len(units) - 1, segment.end_unit)
        if end_unit < start_unit:
            continue
        start_char = units[start_unit].start_char
        end_char = units[end_unit].end_char
        piece = text[start_char:end_char].strip()
        if not piece:
            continue
        chunks.append(
            Chunk(
                text=piece,
                chunk_index=chunk_index,
                source_name=source_name,
                start_char=start_char,
                end_char=end_char,
                unit_start=start_unit,
                unit_end=end_unit,
                label=segment.label,
                reason=segment.reason,
            )
        )
    return chunks


def split_text(text: str, source_name: str, chunk_chars: int, overlap_chars: int) -> list[Chunk]:
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be non-negative")
    if overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must be smaller than chunk_chars")

    stripped = text.strip()
    if not stripped:
        return []

    chunks: list[Chunk] = []
    cursor = 0
    chunk_index = 0
    length = len(text)

    while cursor < length:
        stop = min(length, cursor + chunk_chars)
        if stop < length:
            split_at = text.rfind("\n", cursor, stop)
            if split_at <= cursor:
                split_at = text.rfind(" ", cursor, stop)
            if split_at > cursor:
                stop = split_at

        piece = text[cursor:stop].strip()
        if piece:
            chunks.append(
                Chunk(
                    text=piece,
                    chunk_index=chunk_index,
                    source_name=source_name,
                    start_char=cursor,
                    end_char=stop,
                )
            )
            chunk_index += 1

        if stop >= length:
            break

        cursor = max(stop - overlap_chars, cursor + 1)

    return chunks
