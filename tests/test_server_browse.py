from __future__ import annotations

from pathlib import Path

import pytest

import server


@pytest.mark.asyncio
async def test_browse_directory_rejects_path_outside_sandbox(
    monkeypatch, tmp_path: Path
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    monkeypatch.setattr(server, "FFSA_ENABLED", False)
    monkeypatch.setattr(server, "SANDBOX_ROOT", sandbox_root)

    result = await server.browse_directory(str(outside_dir))

    assert result == {"error": "Access denied: Path is outside the sandbox"}


@pytest.mark.asyncio
async def test_browse_directory_lists_child_directories_in_sandbox(
    monkeypatch, tmp_path: Path
) -> None:
    sandbox_root = tmp_path / "sandbox"
    child_dir = sandbox_root / "photos"
    hidden_dir = sandbox_root / ".hidden"
    image_file = sandbox_root / "image.jpg"
    child_dir.mkdir(parents=True)
    hidden_dir.mkdir()
    image_file.write_bytes(b"image")

    monkeypatch.setattr(server, "FFSA_ENABLED", False)
    monkeypatch.setattr(server, "SANDBOX_ROOT", sandbox_root)

    result = await server.browse_directory(str(sandbox_root))

    assert result["current_path"] == str(sandbox_root)
    assert result["sandbox"] is True
    assert result["items"] == [
        {"name": "photos", "path": str(child_dir), "is_dir": True}
    ]
