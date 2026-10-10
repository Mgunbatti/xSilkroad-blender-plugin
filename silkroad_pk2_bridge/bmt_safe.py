"""Bounded Joymax BMT 0102 material reader.

Never trusts length/count fields from an untrusted PK2 entry. Malformed BMT
entries return the successfully decoded prefix plus an explanation; callers
can import geometry even if the material lookup is unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class MaterialRecord:
    name: str
    texture_path: str
    relative_to_data: bool


class BmtParseError(ValueError):
    pass


class _Reader:
    def __init__(self, content: bytes):
        self.content = content
        self.pos = 0

    def require(self, count: int):
        if count < 0 or self.pos > len(self.content) or count > len(self.content) - self.pos:
            raise BmtParseError(
                f'BMT field exceeds file: offset={self.pos}, requested={count}, '
                f'file_size={len(self.content)}'
            )

    def skip(self, count: int):
        self.require(count)
        self.pos += count

    def uint(self) -> int:
        self.require(4)
        value = struct.unpack_from('<I', self.content, self.pos)[0]
        self.pos += 4
        return value

    def byte(self) -> int:
        self.require(1)
        value = self.content[self.pos]
        self.pos += 1
        return value

    def ascii(self) -> str:
        length = self.uint()
        # No legitimate name/path in an asset table needs multi-MB storage.
        if length > 8192:
            raise BmtParseError(f'BMT string length is implausible: {length} at offset {self.pos - 4}')
        self.require(length)
        text = self.content[self.pos:self.pos + length].decode('cp1252')
        self.pos += length
        return text


def parse_bmt_safe(content: bytes) -> tuple[list[MaterialRecord], str | None]:
    """Return (valid_material_prefix, warning). Never raises for corrupt bytes."""
    if not content.startswith(b'JMXVBMT 0102'):
        return [], 'Unsupported BMT signature (expected JMXVBMT 0102)'
    if len(content) < 16:
        return [], 'Truncated BMT header'

    reader = _Reader(content)
    reader.skip(12)
    materials: list[MaterialRecord] = []
    try:
        count = reader.uint()
        # Minimal per-entry layout: name length + 68 + flags + path length + 7.
        min_record_size = 4 + 68 + 4 + 4 + 7
        if count > (len(content) - 16) // min_record_size:
            return [], f'BMT material count {count} exceeds available file size {len(content)}'
        for _ in range(count):
            name = reader.ascii()
            reader.skip(16 * 4 + 4)
            flags = reader.uint()
            path = reader.ascii()
            reader.skip(4 + 2)
            relative = reader.byte() == 1
            if flags & 0x2000:
                reader.skip(reader.uint())
                reader.skip(4)
            materials.append(MaterialRecord(name, path, relative))
    except (BmtParseError, struct.error) as exc:
        return materials, str(exc)
    return materials, None
