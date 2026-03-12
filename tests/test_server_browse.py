from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

import imgtagplus.server as server


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
    monkeypatch.setattr(server, "_check_rate_limit", lambda *a: True)

    with pytest.raises(HTTPException) as exc_info:
        await server.browse_directory(request=None, path=str(outside_dir))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied: Path is outside the sandbox"


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
    monkeypatch.setattr(server, "_check_rate_limit", lambda *a: True)

    result = await server.browse_directory(request=None, path=str(sandbox_root))

    assert result["current_path"] == str(sandbox_root)
    assert result["sandbox"] is True
    assert result["items"] == [
        {"name": "photos", "path": str(child_dir), "is_dir": True}
    ]
