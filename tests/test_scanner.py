from __future__ import annotations

from pathlib import Path

import pytest

from imgtagplus.scanner import scan


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")
    return path


def test_scan_single_image_returns_resolved_path(sample_image: Path) -> None:
    assert scan(sample_image) == [sample_image.resolve()]


def test_scan_directory_non_recursive_filters_and_sorts(tmp_path: Path) -> None:
    first = _touch(tmp_path / "b.png")
    second = _touch(tmp_path / "a.jpg")
    _touch(tmp_path / "nested" / "c.gif")
    _touch(tmp_path / "notes.txt")

    result = scan(tmp_path)

    assert result == [second.resolve(), first.resolve()]


def test_scan_directory_recursive_includes_nested_images(tmp_path: Path) -> None:
    root = _touch(tmp_path / "root.webp")
    nested = _touch(tmp_path / "nested" / "child.jpeg")

    result = scan(tmp_path, recursive=True)

    assert result == [nested.resolve(), root.resolve()]


def test_scan_rejects_non_image_file(tmp_path: Path) -> None:
    text_file = _touch(tmp_path / "readme.txt")

    with pytest.raises(ValueError, match="Not a recognised image file"):
        scan(text_file)


def test_scan_missing_path_raises_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jpg"

    with pytest.raises(FileNotFoundError, match="Input path does not exist"):
        scan(missing)
