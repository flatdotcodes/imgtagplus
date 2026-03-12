from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake image bytes")
    return image_path
