"""XMP sidecar file writer for ImgTagPlus.

Generates Adobe-compatible XMP sidecar files (``.xmp``) that store
keywords in the ``dc:subject`` field.  Recognised by Lightroom, Bridge,
Darktable, digiKam, XnView, and virtually all DAM systems.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

log = logging.getLogger(__name__)

# XML namespaces used in XMP.
_NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
}

# Register namespaces so ElementTree preserves prefixes.
for prefix, uri in _NS.items():
    ET.register_namespace(prefix, uri)


def write_xmp(
    image_path: Path,
    tags: Sequence[str],
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Write (or merge into) an XMP sidecar file for *image_path*.

    Parameters
    ----------
    image_path:
        Absolute path to the source image.
    tags:
        Keyword strings to store in ``dc:subject``.
    output_dir:
        Directory for the ``.xmp`` file.  Defaults to the same
        directory as the image.
    overwrite:
        If ``True``, replace existing tags entirely instead of merging.

    Returns
    -------
    Path
        Absolute path to the written ``.xmp`` file.
    """
    if output_dir is None:
        output_dir = image_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    xmp_path = output_dir / (image_path.stem + ".xmp")

    # If the sidecar already exists, merge tags (unless overwriting).
    existing_tags: set[str] = set()
    if not overwrite and xmp_path.exists():
        existing_tags = _read_existing_tags(xmp_path)
        log.debug("Existing XMP has %d tags: %s", len(existing_tags), xmp_path)

    merged = sorted(existing_tags | set(tags))

    # Build the XMP document.
    xml_str = _build_xmp(merged, image_path.name)
    xmp_path.write_text(xml_str, encoding="utf-8")
    log.debug("Wrote %d tags to %s", len(merged), xmp_path)
    return xmp_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_xmp(tags: list[str], source_filename: str) -> str:
    """Return a complete XMP XML string containing *tags*."""
    lines = [
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>',
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
        '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
        '    <rdf:Description',
        f'      rdf:about="{source_filename}"',
        '      xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '      xmlns:xmp="http://ns.adobe.com/xap/1.0/"',
        '      xmlns:lr="http://ns.adobe.com/lightroom/1.0/">',
        '      <dc:subject>',
        '        <rdf:Bag>',
    ]
    for tag in tags:
        escaped = tag.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"          <rdf:li>{escaped}</rdf:li>")
    lines += [
        '        </rdf:Bag>',
        '      </dc:subject>',
        '    </rdf:Description>',
        '  </rdf:RDF>',
        '</x:xmpmeta>',
        '<?xpacket end="w"?>',
    ]
    return "\n".join(lines) + "\n"


def _read_existing_tags(xmp_path: Path) -> set[str]:
    """Parse existing ``dc:subject`` tags from an XMP file."""
    try:
        tree = ET.parse(xmp_path)
        root = tree.getroot()
        tags: set[str] = set()
        ns = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "dc": "http://purl.org/dc/elements/1.1/",
        }
        # Navigate specifically to dc:subject > rdf:Bag > rdf:li
        for subject in root.iter(f"{{{ns['dc']}}}subject"):
            for bag in subject.iter(f"{{{ns['rdf']}}}Bag"):
                for li in bag.iter(f"{{{ns['rdf']}}}li"):
                    text = (li.text or "").strip()
                    if text:
                        tags.add(text)
        return tags
    except ET.ParseError:
        log.warning("Could not parse existing XMP file: %s", xmp_path)
        return set()
