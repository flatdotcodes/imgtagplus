from __future__ import annotations

from pathlib import Path

from imgtagplus.metadata import _build_xmp, _read_existing_tags, write_xmp


def test_write_xmp_creates_sidecar_with_escaped_tags(sample_image: Path) -> None:
    xmp_path = write_xmp(sample_image, ["cats & dogs", "a < b > c"])

    text = xmp_path.read_text(encoding="utf-8")

    assert xmp_path.name == "sample.xmp"
    assert "&amp;" in text
    assert "&lt;" in text
    assert "&gt;" in text
    assert 'rdf:about="sample.jpg"' in text


def test_write_xmp_merges_existing_tags_when_not_overwriting(sample_image: Path) -> None:
    write_xmp(sample_image, ["beta"])

    merged_path = write_xmp(sample_image, ["alpha"], overwrite=False)

    assert _read_existing_tags(merged_path) == {"alpha", "beta"}


def test_write_xmp_overwrites_existing_tags(sample_image: Path) -> None:
    write_xmp(sample_image, ["legacy"])

    xmp_path = write_xmp(sample_image, ["fresh"], overwrite=True)

    assert _read_existing_tags(xmp_path) == {"fresh"}


def test_read_existing_tags_returns_empty_set_for_malformed_xml(
    tmp_path: Path, caplog
) -> None:
    broken_xmp = tmp_path / "broken.xmp"
    broken_xmp.write_text("<not-xml", encoding="utf-8")

    tags = _read_existing_tags(broken_xmp)

    assert tags == set()
    assert "Could not parse existing XMP file" in caplog.text


def test_build_xmp_includes_all_tags_and_packet_markers() -> None:
    xml = _build_xmp(["alpha", "beta"], "image.jpg")

    assert xml.startswith('<?xpacket begin=')
    assert '<rdf:li>alpha</rdf:li>' in xml
    assert '<rdf:li>beta</rdf:li>' in xml
    assert xml.rstrip().endswith('<?xpacket end="w"?>')
