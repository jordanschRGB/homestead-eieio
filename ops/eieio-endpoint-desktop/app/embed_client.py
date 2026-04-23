from __future__ import annotations

from typing import Any

import requests


class ArgusEmbedClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": texts},
            timeout=180,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return [item["embedding"] for item in payload["data"]]
