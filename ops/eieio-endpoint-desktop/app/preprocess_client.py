from __future__ import annotations

import json
from typing import Any

import requests

from app.chunking import Segment, Unit


class LmStudioPreprocessClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def segment_units(self, source_name: str, units: list[Unit], model: str | None = None) -> list[Segment]:
        if not units:
            return []

        schema = {
            "name": "semantic_chunk_plan",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "start_unit": {"type": "integer"},
                                "end_unit": {"type": "integer"},
                                "label": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["start_unit", "end_unit", "label", "reason"],
                        },
                    }
                },
                "required": ["segments"],
            },
        }

        units_payload = []
        for unit in units:
            entry = {"i": unit.unit_index, "kind": unit.kind, "text": unit.text}
            units_payload.append(entry)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a semantic chunk planner. Group adjacent source units into coherent segments. "
                    "Do not rewrite or summarize the source. Output JSON only. "
                    "Prefer stable, meaningful ranges. Do not overlap segments. "
                    "Do not skip units. Every unit must belong to exactly one segment."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "source_name": source_name,
                        "task": "Group these source units into semantically coherent contiguous segments.",
                        "rules": [
                            "Use adjacent unit ranges only.",
                            "Keep headings with the material they introduce when that makes sense.",
                            "Keep speaker turns together when they stay on the same topic.",
                            "Split on obvious topic, scene, or section changes.",
                            "Return all units exactly once.",
                        ],
                        "units": units_payload,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": model or self.model,
                "temperature": 0,
                "messages": messages,
                "response_format": {"type": "json_schema", "json_schema": schema},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        data = json.loads(content)
        segments = []
        for segment in data.get("segments", []):
            segments.append(
                Segment(
                    start_unit=int(segment["start_unit"]),
                    end_unit=int(segment["end_unit"]),
                    label=str(segment.get("label", "")).strip() or None,
                    reason=str(segment.get("reason", "")).strip() or None,
                )
            )
        return segments
