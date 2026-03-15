from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import imgtagplus.server as server
from imgtagplus.metadata import write_xmp


@pytest.fixture
def image_client(monkeypatch, tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()

    monkeypatch.setattr(server, "FFSA_ENABLED", False)
    monkeypatch.setattr(server, "SANDBOX_ROOT", sandbox_root)
    monkeypatch.setattr(server, "_check_rate_limit", lambda *a: True)

    return TestClient(server.app), sandbox_root


def test_list_images_returns_supported_images_and_tags(image_client) -> None:
    client, sandbox_root = image_client
    photos_dir = sandbox_root / "photos"
    photos_dir.mkdir()

    tagged_image = photos_dir / "alpha.jpg"
    untagged_image = photos_dir / "beta.png"
    ignored_file = photos_dir / "notes.txt"
    tagged_image.write_bytes(b"jpeg-bytes")
    untagged_image.write_bytes(b"png-bytes")
    ignored_file.write_text("ignore me", encoding="utf-8")
    write_xmp(tagged_image, ["sunset", "landscape"])

    response = client.get("/api/images", params={"path": str(photos_dir)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["has_more"] is False
    assert [item["name"] for item in payload["images"]] == ["alpha.jpg", "beta.png"]
    assert payload["images"][0]["tags"] == ["landscape", "sunset"]
    assert payload["images"][0]["xmp_exists"] is True
    assert payload["images"][1]["tags"] == []
    assert payload["images"][1]["xmp_exists"] is False


def test_list_images_supports_pagination(image_client) -> None:
    client, sandbox_root = image_client
    photos_dir = sandbox_root / "photos"
    photos_dir.mkdir()

    for name in ("alpha.jpg", "beta.jpg", "gamma.jpg"):
        (photos_dir / name).write_bytes(b"image")

    response = client.get(
        "/api/images",
        params={"path": str(photos_dir), "offset": 1, "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["offset"] == 1
    assert payload["limit"] == 1
    assert payload["has_more"] is True
    assert [item["name"] for item in payload["images"]] == ["beta.jpg"]


def test_list_images_rejects_directory_outside_sandbox(image_client, tmp_path: Path) -> None:
    client, _ = image_client
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "photo.jpg").write_bytes(b"image")

    response = client.get("/api/images", params={"path": str(outside_dir)})

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: path outside sandbox"}


def test_get_image_file_serves_supported_image(image_client) -> None:
    client, sandbox_root = image_client
    image_path = sandbox_root / "photo.jpg"
    image_path.write_bytes(b"binary-image")

    response = client.get("/api/image", params={"path": str(image_path)})

    assert response.status_code == 200
    assert response.content == b"binary-image"
    assert response.headers["content-type"].startswith("image/jpeg")


def test_get_image_file_rejects_non_image_paths(image_client) -> None:
    client, sandbox_root = image_client
    text_path = sandbox_root / "notes.txt"
    text_path.write_text("nope", encoding="utf-8")

    response = client.get("/api/image", params={"path": str(text_path)})

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported image type"}
