"""Pure-Python helpers for PK2 -> Blender importer; no bpy dependency."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import struct

SIGNATURES = {
    '.bsr': b'JMXVRES 0109',
    '.bms': b'JMXVBMS 0110',
    '.bsk': b'JMXVBSK 0101',
    '.ban': b'JMXVBAN 0102',
    '.dof': b'JMXVDOF 0101',
    '.nvm': b'JMXVNVM 1000',
}


class InvalidAsset(ValueError):
    pass


def validate_asset(path: str | Path) -> None:
    path = Path(path)
    expected = SIGNATURES.get(path.suffix.lower())
    if expected is None:
        raise InvalidAsset(f"Unsupported file extension: {path.suffix}")
    if not path.is_file():
        raise InvalidAsset(f"File not found: {path}")
    with path.open('rb') as fp:
        header = fp.read(12)
    if header != expected:
        raise InvalidAsset(f"Invalid {path.suffix.upper()} signature: {path.name}")


class Reader:
    def __init__(self, contents: bytes):
        self.data = memoryview(contents)
        self.pos = 0

    def read(self, n: int) -> bytes:
        if n < 0 or n > len(self.data) - self.pos:
            raise InvalidAsset('BSR file is incomplete or corrupted')
        result = bytes(self.data[self.pos:self.pos+n])
        self.pos += n
        return result

    def skip(self, n: int):
        self.read(n)

    def uint(self) -> int:
        return struct.unpack('<I', self.read(4))[0]

    def string(self) -> str:
        length = self.uint()
        if length > 4096:
            raise InvalidAsset('Invalid reference length in BSR')
        return self.read(length).decode('cp1252', errors='replace')


@dataclass
class BsrReferences:
    meshes: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    skeleton: str = ''
    animations: list[str] = field(default_factory=list)


def parse_bsr(path: str | Path) -> BsrReferences:
    validate_asset(path)
    data = Path(path).read_bytes()
    r = Reader(data)
    r.skip(12)                 # signature
    r.skip(8 * 4)              # file offsets
    flags = r.uint()
    r.skip(4 * 4)              # reserved
    r.skip(4)
    r.string()                 # object name
    r.skip(8 + 40)
    r.skip(r.uint())           # collision data
    r.skip(24 + 24)            # bbox + unused fields
    if r.uint():
        r.skip(64)             # collision matrix

    refs = BsrReferences()
    count = r.uint()
    if count > 20000:
        raise InvalidAsset('Invalid material count in BSR')
    for _ in range(count):
        r.uint()              # material type
        refs.materials.append(r.string())

    count = r.uint()
    if count > 20000:
        raise InvalidAsset('Invalid mesh count in BSR')
    for _ in range(count):
        refs.meshes.append(r.string())
        if flags & 1:
            r.skip(4)

    r.skip(8)
    count = r.uint()
    if count > 20000:
        raise InvalidAsset('Invalid animation count in BSR')
    for _ in range(count):
        refs.animations.append(r.string())
    if r.uint():
        refs.skeleton = r.string()
    return refs


def resolve_relative(root: str | Path, ref: str) -> Path:
    clean = ref.replace('\\', '/').strip().lstrip('/')
    items = clean.split('/')
    # Avoid escaping the exported Data root. BSR normally stores relative PK2 paths.
    if not clean or '..' in items or ':' in clean or clean.startswith('//'):
        raise InvalidAsset(f'Invalid relative PK2 path: {ref}')
    return Path(root).joinpath(*items)


def discover_data_root(file_path: str | Path, configured: str = '', watched: str = '') -> Path:
    """Return the folder containing prim/, navmesh/, etc. (not prim/ itself)."""
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.name.lower() == 'prim':
            candidate = candidate.parent
        if (candidate / 'Data').is_dir() and not (candidate / 'prim').is_dir():
            candidate = candidate / 'Data'
        return candidate

    file_path = Path(file_path).resolve()
    for part in (file_path.parent, *file_path.parents):
        if part.name.lower() == 'data':
            return part
        if part.name.lower() == 'prim':
            return part.parent
    if watched:
        candidate = Path(watched).expanduser()
        if (candidate / 'Data').is_dir():
            return candidate / 'Data'
        return candidate
    return file_path.parent


def missing_references(path: str | Path, root: str | Path, require_skeleton: bool = True):
    refs = parse_bsr(path)
    required = list(refs.meshes)
    if require_skeleton and refs.skeleton:
        required.append(refs.skeleton)
    missing = []
    for ref in required:
        target = resolve_relative(root, ref)
        if not target.is_file():
            missing.append(ref)
    optional = [ref for ref in refs.materials if not resolve_relative(root, ref).is_file()]
    return refs, missing, optional
