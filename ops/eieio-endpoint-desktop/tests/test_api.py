from io import BytesIO
import zipfile

from fastapi.testclient import TestClient

from app.chunking import Segment
from app.main import AppState, build_app


class FakeEmbedClient:
    def embed_batch(self, texts):
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


class FakePreprocessClient:
    def segment_units(self, source_name, units, model=None):
        if not units:
            return []
        if len(units) == 1:
            return [Segment(start_unit=0, end_unit=0, label="solo", reason="single unit")]
        return [
            Segment(start_unit=0, end_unit=min(1, len(units) - 1), label="intro", reason="keep together"),
            Segment(start_unit=min(2, len(units) - 1), end_unit=len(units) - 1, label="rest", reason="remaining"),
        ]


def make_client(tmp_path, preprocess_client=None):
    state = AppState(
        api_token="secret-token",
        settings=type(
            "S",
            (),
            {
                "argus_model": "pplx-test-model",
                "default_chunk_chars": 40,
                "default_overlap_chars": 5,
                "default_batch_size": 8,
                "work_dir": tmp_path,
                "preprocess_model": "google/gemma-4-e2b",
            },
        )(),
        embed_client=FakeEmbedClient(),
        preprocess_client=preprocess_client,
    )
    return TestClient(build_app(state))


def test_text_ingest_returns_manifest_and_jsonl(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/v1/ingest/text",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "documents": [
                {"name": "notes.md", "content": "alpha " * 30},
                {"name": "scene.md", "content": "beta " * 30},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "pplx-test-model"
    assert body["chunk_count"] > 0
    assert tmp_path.joinpath(f"{body['job_id']}.jsonl").exists()


def test_archive_ingest_accepts_markdown_zip(tmp_path):
    client = make_client(tmp_path)
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("folder/a.md", "hello world " * 20)
        archive.writestr("folder/b.txt", "goodbye world " * 20)
    payload.seek(0)

    response = client.post(
        "/v1/ingest/archive?return_vectors_inline=true",
        headers={"Authorization": "Bearer secret-token"},
        files={"file": ("docs.zip", payload.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_count"] == 2
    assert body["chunks"]


def test_auth_is_required(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 401


def test_help_describes_text_and_archive_modes(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/help")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "EIEIO Endpoint Desktop Ingest Helper"
    assert body["routes"]["ingest_text"]["path"] == "/v1/ingest/text"
    assert body["routes"]["ingest_archive"]["path"] == "/v1/ingest/archive"
    assert any("folder of markdown" in note for note in body["notes"])


def test_text_ingest_can_use_preprocessor(tmp_path):
    client = make_client(tmp_path, preprocess_client=FakePreprocessClient())
    response = client.post(
        "/v1/ingest/text",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "documents": [
                {
                    "name": "transcript.md",
                    "content": "# Scene\n\nDad: first thought\n\nDad: second thought\n\nShifted topic paragraph here.",
                }
            ],
            "use_preprocessor": True,
            "return_vectors_inline": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["preprocess_used"] is True
    assert body["chunk_count"] == 2
    assert body["chunks"][0]["label"] == "intro"
