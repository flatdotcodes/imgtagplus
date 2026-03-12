from __future__ import annotations

import queue
import threading
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server


class _ImmediateThread:
    def __init__(self, target, daemon=None):
        self._target = target
        self.daemon = daemon

    def start(self) -> None:
        self._target()


@pytest.fixture
def tagging_client(monkeypatch, tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.setattr(server, "FFSA_ENABLED", False)
    monkeypatch.setattr(server, "SANDBOX_ROOT", sandbox_root)
    monkeypatch.setattr(server, "log_queue", queue.Queue())
    monkeypatch.setattr(server, "progress_queue", queue.Queue())
    monkeypatch.setattr(server, "_job_lock", threading.Lock())
    monkeypatch.setattr(server, "_job_started_at", None)
    monkeypatch.setattr(server, "_job_started_monotonic", None)
    monkeypatch.setattr(server, "_last_job_runtime_seconds", None)
    monkeypatch.setattr(server.threading, "Thread", _ImmediateThread)

    def fake_run(args, progress_callback=None):
        captured["args"] = args
        return 0

    monkeypatch.setattr(server, "app_run", fake_run)

    return TestClient(server.app), sandbox_root, captured


def test_start_tagging_rejects_input_outside_sandbox(tagging_client, tmp_path: Path) -> None:
    client, _, _ = tagging_client
    outside_image = tmp_path / "outside.jpg"
    outside_image.write_bytes(b"image")

    response = client.post("/api/tag", json={"input": str(outside_image)})

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: path outside sandbox"}


def test_start_tagging_invalid_path_does_not_leave_server_busy(tagging_client, tmp_path: Path) -> None:
    client, _, _ = tagging_client
    missing_path = tmp_path / "missing"

    response = client.post("/api/tag", json={"input": str(missing_path)})

    assert response.status_code == 200
    assert response.json() == {"error": f"Invalid or non-existent path: {missing_path}"}
    assert client.get("/api/status").json()["is_processing"] is False


def test_start_tagging_rejects_output_dir_outside_sandbox(
    tagging_client, tmp_path: Path
) -> None:
    client, sandbox_root, _ = tagging_client
    image_path = sandbox_root / "photo.jpg"
    image_path.write_bytes(b"image")
    outside_dir = tmp_path / "outside-output"
    outside_dir.mkdir()

    response = client.post(
        "/api/tag",
        json={"input": str(image_path), "output_dir": str(outside_dir)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: path outside sandbox"}


def test_start_tagging_clamps_threshold_and_max_tags(tagging_client) -> None:
    client, sandbox_root, captured = tagging_client
    image_path = sandbox_root / "photo.jpg"
    image_path.write_bytes(b"image")

    response = client.post(
        "/api/tag",
        json={"input": str(image_path), "threshold": -5, "max_tags": 10_000},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "started"
    assert datetime.fromisoformat(payload["started_at"])
    assert captured["args"].threshold == 0.0
    assert captured["args"].max_tags == 200


def test_start_tagging_passes_manual_accelerator(tagging_client) -> None:
    client, sandbox_root, captured = tagging_client
    image_path = sandbox_root / "photo.jpg"
    image_path.write_bytes(b"image")

    response = client.post(
        "/api/tag",
        json={"input": str(image_path), "accelerator": "cpu"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "started"
    assert datetime.fromisoformat(payload["started_at"])
    assert captured["args"].accelerator == "cpu"


def test_security_headers_are_added_to_api_responses(tagging_client) -> None:
    client, _, _ = tagging_client

    response = client.get("/api/status")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_index_uses_external_scripts_for_csp(tagging_client) -> None:
    client, _, _ = tagging_client

    response = client.get("/")

    assert response.status_code == 200
    assert "<script>" not in response.text
    assert '<script src="/static/theme.js"></script>' in response.text
    assert 'id="runtime-clock"' in response.text
    assert 'id="copy-logs"' in response.text


def test_health_endpoint_reports_ok(tagging_client) -> None:
    client, _, _ = tagging_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_reports_runtime_details_when_idle(tagging_client) -> None:
    client, _, _ = tagging_client

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json() == {
        "is_processing": False,
        "started_at": None,
        "runtime_seconds": None,
    }
