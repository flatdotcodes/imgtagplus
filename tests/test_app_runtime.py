import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from imgtagplus.app import _format_runtime, run


def test_format_runtime_zero_pads_components() -> None:
    assert _format_runtime(0) == "00:00:00"
    assert _format_runtime(65) == "00:01:05"
    assert _format_runtime(3661.8) == "01:01:01"


def _make_args(tmp_path: Path, **overrides) -> argparse.Namespace:
    """Build a minimal argparse.Namespace for app.run()."""
    defaults = dict(
        input=tmp_path,
        recursive=False,
        threshold=0.25,
        max_tags=20,
        silent=True,
        continue_on_error=False,
        log_file=None,
        model_dir=None,
        model_id="clip",
        output_dir=None,
        accelerator=None,
        overwrite=False,
        input_timeout=30,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _create_test_image(path: Path) -> Path:
    """Create a minimal valid JPEG file (SOI + APP0 + EOI)."""
    soi = b'\xff\xd8'
    app0 = b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    eoi = b'\xff\xd9'
    path.write_bytes(soi + app0 + eoi)
    return path


class FakeTagger:
    """Mock tagger that returns fixed results."""

    def __init__(self, results=None, error_on=None):
        self.results = results or [("landscape", 0.9), ("nature", 0.8)]
        self.error_on = error_on or set()
        self.precompute_tag_embeddings = MagicMock()

    def tag_image(self, image_path, tags=None, threshold=0.25, max_tags=20):
        if image_path.name in self.error_on:
            raise RuntimeError(f"Simulated error on {image_path.name}")
        return self.results[:max_tags]


@patch("imgtagplus.app.Monitor")
@patch("imgtagplus.app.scan")
def test_run_happy_path_writes_xmp(mock_scan, mock_monitor_cls, tmp_path):
    """Full pipeline: scan -> tag -> write XMP sidecar."""
    img = _create_test_image(tmp_path / "photo.jpg")
    mock_scan.return_value = [img]
    mock_monitor = MagicMock()
    mock_monitor.stop.return_value = MagicMock(summary=lambda: "test stats")
    mock_monitor_cls.return_value = mock_monitor

    fake_tagger = FakeTagger(results=[("sunset", 0.95), ("sky", 0.8)])

    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger):
        args = _make_args(tmp_path)
        exit_code = run(args)

    assert exit_code == 0
    xmp_path = tmp_path / "photo.xmp"
    assert xmp_path.exists()
    content = xmp_path.read_text()
    assert "sunset" in content
    assert "sky" in content


@patch("imgtagplus.app.Monitor")
@patch("imgtagplus.app.scan")
def test_run_continue_on_error_skips_failures(mock_scan, mock_monitor_cls, tmp_path):
    """With continue_on_error=True, errors are skipped and remaining images processed."""
    img_ok = _create_test_image(tmp_path / "good.jpg")
    img_bad = _create_test_image(tmp_path / "bad.jpg")
    mock_scan.return_value = [img_bad, img_ok]
    mock_monitor = MagicMock()
    mock_monitor.stop.return_value = MagicMock(summary=lambda: "test stats")
    mock_monitor_cls.return_value = mock_monitor

    fake_tagger = FakeTagger(error_on={"bad.jpg"})

    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger):
        args = _make_args(tmp_path, continue_on_error=True)
        exit_code = run(args)

    # Exit code 2 = completed with errors
    assert exit_code == 2
    # The good image should still have been processed
    assert (tmp_path / "good.xmp").exists()


@patch("imgtagplus.app.Monitor")
@patch("imgtagplus.app.scan")
def test_run_unknown_model_falls_back_to_clip(mock_scan, mock_monitor_cls, tmp_path):
    """Unknown model_id falls back to clip gracefully."""
    img = _create_test_image(tmp_path / "photo.jpg")
    mock_scan.return_value = [img]
    mock_monitor = MagicMock()
    mock_monitor.stop.return_value = MagicMock(summary=lambda: "test stats")
    mock_monitor_cls.return_value = mock_monitor

    fake_tagger = FakeTagger()

    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger):
        args = _make_args(tmp_path, model_id="nonexistent-model-xyz")
        exit_code = run(args)

    assert exit_code == 0
    # Should have fallen back to clip and still processed
    assert (tmp_path / "photo.xmp").exists()


@patch("imgtagplus.app.Monitor")
@patch("imgtagplus.app.scan")
def test_run_progress_callback_is_called(mock_scan, mock_monitor_cls, tmp_path):
    """Progress callback receives correct current/total values."""
    img1 = _create_test_image(tmp_path / "a.jpg")
    img2 = _create_test_image(tmp_path / "b.jpg")
    mock_scan.return_value = [img1, img2]
    mock_monitor = MagicMock()
    mock_monitor.stop.return_value = MagicMock(summary=lambda: "test stats")
    mock_monitor_cls.return_value = mock_monitor

    fake_tagger = FakeTagger()
    callback = MagicMock()

    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger):
        args = _make_args(tmp_path)
        exit_code = run(args, progress_callback=callback)

    assert exit_code == 0
    assert callback.call_count == 2
    callback.assert_any_call(1, 2, str(img1))
    callback.assert_any_call(2, 2, str(img2))


@patch("imgtagplus.app.Monitor")
@patch("imgtagplus.app.scan")
def test_run_overwrite_replaces_tags(mock_scan, mock_monitor_cls, tmp_path):
    """With overwrite=True, existing XMP tags are replaced, not merged."""
    img = _create_test_image(tmp_path / "photo.jpg")
    mock_scan.return_value = [img]
    mock_monitor = MagicMock()
    mock_monitor.stop.return_value = MagicMock(summary=lambda: "test stats")
    mock_monitor_cls.return_value = mock_monitor

    # First run: write initial tags
    fake_tagger = FakeTagger(results=[("old_tag", 0.9)])
    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger):
        run(_make_args(tmp_path))

    xmp_path = tmp_path / "photo.xmp"
    assert "old_tag" in xmp_path.read_text()

    # Second run: overwrite with new tags
    mock_scan.return_value = [img]
    mock_monitor_cls.return_value = mock_monitor
    fake_tagger2 = FakeTagger(results=[("new_tag", 0.9)])
    with patch("imgtagplus.tagger.Tagger", return_value=fake_tagger2):
        run(_make_args(tmp_path, overwrite=True))

    content = xmp_path.read_text()
    assert "new_tag" in content
    assert "old_tag" not in content
