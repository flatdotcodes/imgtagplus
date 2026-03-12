from imgtagplus.app import _format_runtime


def test_format_runtime_zero_pads_components() -> None:
    assert _format_runtime(0) == "00:00:00"
    assert _format_runtime(65) == "00:01:05"
    assert _format_runtime(3661.8) == "01:01:01"
