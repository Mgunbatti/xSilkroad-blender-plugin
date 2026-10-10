"""Blender-independent PK2 archive bridge.

PK2 I/O is delegated to MIT-licensed pk2api 1.5.0 (installed on demand);
Silkroad import modules handle geometry serialization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import tempfile
import re
from .map_data import parse_dof, parse_nvm

from .bridge_core import BsrReferences, InvalidAsset, Reader, parse_bsr, resolve_relative, SIGNATURES

SUPPORTED_EXTS = frozenset(('.bsr', '.bms', '.bsk', '.ban', '.dof', '.nvm'))
ASSET_PRIORITY = {'.bsr': 0, '.bms': 1, '.bsk': 2, '.ban': 3}


def normalize_path(value: str) -> str:
    """Canonical archive-relative path, disallow traversal and OS-absolute paths."""
    if not isinstance(value, str):
        raise InvalidAsset('PK2 path must be a string')
    path = value.replace('\\', '/').strip()
    if path.startswith('/'):
        raise InvalidAsset(f'Absolute PK2 path is not allowed: {value!r}')
    parts = path.split('/')
    if not path or any(p in ('', '.', '..') for p in parts) or ':' in path or '\x00' in path:
        raise InvalidAsset(f'Invalid PK2 path: {value!r}')
    return '/'.join(parts).lower()


def safe_local_path(root: Path, inner: str) -> Path:
    inner = normalize_path(inner)
    return Path(root).joinpath(*inner.split('/'))


def decode_bms_name(data: bytes) -> str:
    """Read intrinsic mesh name to correlate imported Blender objects to PK2 entry."""
    if len(data) < 84 or not data.startswith(b'JMXVBMS 0110'):
        raise InvalidAsset('Invalid BMS data')
    # 12 signature + 10*4 offsets + 5*4 flags; name is length-prefixed.
    pos = 12 + 40 + 20
    size = struct.unpack_from('<I', data, pos)[0]
    if size > 4096 or pos + 4 + size > len(data):
        raise InvalidAsset('Invalid BMS name length')
    return data[pos + 4:pos + 4 + size].decode('cp1252', 'replace')


def parse_bmt_textures(data: bytes, material_inner_path: str) -> list[str]:
    """Read Material 0102 texture references.

    Other BMT variants are ignored; absent textures don't abort mesh import.
    """
    if not data.startswith(b'JMXVBMT 0102'):
        return []
    reader = Reader(data)
    reader.skip(12)
    count = reader.uint()
    if count > 20000:
        raise InvalidAsset('Invalid BMT material count')
    result = []
    parent = PurePosixPath(normalize_path(material_inner_path)).parent
    for _ in range(count):
        reader.string()           # material name
        reader.skip(64 + 4)
        flag = reader.uint()
        tex_path = reader.string()
        reader.skip(4 + 2)
        relative_to_data = reader.read(1) != b'\x00'
        if flag & 0x2000:
            reader.skip(reader.uint())
            reader.skip(4)
        if not tex_path:
            continue
        try:
            original = normalize_path(tex_path)
            if relative_to_data or original.startswith('prim/'):
                resolved = original
            else:
                resolved = normalize_path(str(parent / original))
            result.append(resolved)
        except InvalidAsset:
            continue
    return sorted(set(result))


def find_sibling_archives(primary: Path) -> list[Path]:
    """Cross-PK2 BSR dependencies often reside in adjacent Data/Media/Map archives."""
    wanted = ('data.pk2', 'media.pk2', 'map.pk2', 'particles.pk2')
    primary = Path(primary).resolve()
    found = [primary]
    for name in wanted:
        match = next((p for p in primary.parent.iterdir() if p.is_file() and p.name.lower() == name), None)
        if match and match.resolve() != primary and match not in found:
            found.append(match)
    return found


class ArchiveSession:
    """Keeps source read-only PK2 streams open for responsive folder browsing."""
    def __init__(self, primary: str | Path, key: str = '169841', backend=None, progress=None):
        primary = Path(primary).expanduser().resolve()
        if not primary.is_file() or primary.suffix.lower() != '.pk2':
            raise FileNotFoundError(f'PK2 archive not found: {primary}')
        if backend is None:
            try:
                from pk2api import Pk2Stream
            except ImportError as exc:
                raise RuntimeError('PK2API is missing. Install the PK2 engine from the Blender panel.') from exc
            backend = Pk2Stream
        self.primary = primary
        self.key = key
        self.backend = backend
        self.streams = {}
        self.errors = []
        try:
            for location in find_sibling_archives(primary):
                try:
                    kwargs = {'read_only': True}
                    if progress is not None:
                        kwargs['progress'] = (lambda done, total, loc=location: progress(loc, done, total))
                    try:
                        stream = backend(str(location), key, **kwargs)
                    except TypeError as exc:
                        # Retry only a missing progress parameter.
                        detail = str(exc)
                        if ('progress' not in kwargs or
                                'unexpected keyword argument' not in detail or
                                not ("'progress'" in detail or '"progress"' in detail)):
                            raise
                        if progress is not None:
                            progress(location, None, None)
                        stream = backend(str(location), key, read_only=True)
                    self.streams[location] = stream
                except Exception as e:
                    if location == primary:
                        raise
                    self.errors.append(f'{location.name}: {e}')
        except Exception:
            self.close()
            raise

    def close(self):
        for stream in self.streams.values():
            try:
                stream.close()
            except Exception:
                pass
        self.streams.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get(self, inner: str):
        """Return (bytes, originating PK2) or (None, None)."""
        inner = normalize_path(inner)
        for archive, stream in self.streams.items():
            candidate = stream.get_file(inner)
            if candidate is not None:
                return candidate.get_content(), archive
        return None, None

    def primary_folder(self, folder_path=''):
        stream = self.streams[self.primary]
        folder = stream.get_folder(folder_path.strip('/'))
        if folder is None:
            raise FileNotFoundError(f'PK2 folder not found: {folder_path}')
        return folder

    def list_folder(self, folder_path='') -> list[dict]:
        folder = self.primary_folder(folder_path)
        rows = []
        for item in folder.folders.values():
            rows.append(dict(name=item.original_name, path=item.get_full_path().replace('\\', '/'), folder=True, size=0))
        for item in folder.files.values():
            rows.append(dict(name=item.original_name, path=item.get_full_path().replace('\\', '/'), folder=False, size=item.size))
        rows.sort(key=lambda x: (not x['folder'], x['name'].casefold()))
        return rows

    def search(self, query: str, max_results=250) -> list[dict]:
        if len(query.strip()) < 2:
            raise ValueError('Enter at least 2 characters to search.')
        needle = query.strip().lower()
        stream = self.streams[self.primary]
        results = []
        for file in stream.iter_files():
            if needle not in file.get_full_path().lower():
                continue
            results.append(dict(name=file.original_name, path=file.get_full_path().replace('\\', '/'), folder=False, size=file.size))
            if len(results) >= max_results:
                break
        return results


@dataclass
class PreparedAsset:
    source_path: Path
    data_root: Path
    workspace: Path
    selected_entry: str
    meshes: dict[str, str | None] = field(default_factory=dict)  # ambiguous repeated names -> None
    sources: dict[str, Path] = field(default_factory=dict) # entry -> source archive
    missing_optional: list[str] = field(default_factory=list)
    map_root: Path | None = None


def prepare_asset(session: ArchiveSession, selected: str, *, include_animations=False, include_objects=False, base_dir=None) -> PreparedAsset:
    """Extract selected BSR and referenced files to a disposable Data tree.

    No full PK2 extraction. Caller is responsible for cleaning workspace
    when no longer needed; loaded Blender images may refer to DDS files there.
    """
    selected = normalize_path(selected)
    ext = Path(selected).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise InvalidAsset(f'This file type cannot be opened as a 3D model: {ext}')
    content, archive = session.get(selected)
    if content is None:
        raise FileNotFoundError(f'Entry not found in PK2: {selected}')
    if content[:12] != SIGNATURES[ext]:
        raise InvalidAsset(f'Invalid {ext} signature: {selected}')
    folder = Path(tempfile.mkdtemp(prefix='Silkroad_PK2_', dir=base_dir))
    root = folder / 'Data'
    prepared = PreparedAsset(root / selected, root, folder, selected)
    prepared.map_root = folder / 'Map'
    prepared.map_root.mkdir()
    seen = set()

    def extract_one(inner: str, *, required: bool = False, map_file=False) -> bytes | None:
        inner = normalize_path(inner)
        output_root = prepared.map_root if map_file else root
        key = (inner, map_file)
        if key in seen:
            output = safe_local_path(output_root, inner)
            if required and not output.is_file():
                raise FileNotFoundError(f'Required dependency missing: {inner}')
            return output.read_bytes() if output.is_file() else None
        seen.add(key)
        data, origin = session.get(inner)
        if data is None:
            if required:
                raise FileNotFoundError(f'Required model dependency was not found in PK2 archives: {inner}')
            prepared.missing_optional.append(inner)
            return None
        file_path = safe_local_path(output_root, inner)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        prepared.sources[inner] = origin
        if inner.endswith('.bms'):
            name = decode_bms_name(data)
            prepared.meshes[name] = None if name in prepared.meshes else inner
        return data

    resources = set()

    def extract_resource(inner):
        inner = normalize_path(inner)
        if inner in resources:
            return
        resources.add(inner)
        contents = extract_one(inner, required=True)
        if contents[:12] == b'JMXVCPD 0101':
            reader = Reader(contents)
            reader.skip(16)
            offset = reader.uint()
            reader.pos = offset
            for _ in range(reader.uint()):
                extract_resource(reader.string())
        elif contents[:12] == SIGNATURES['.bsr']:
            refs = parse_bsr(safe_local_path(root, inner))
            for inner in refs.meshes:
                extract_one(inner, required=True)
            if refs.skeleton:
                extract_one(refs.skeleton, required=False)
            for inner in refs.materials:
                contents = extract_one(inner, required=False)
                if contents is None:
                    continue
                try:
                    texture_paths = parse_bmt_textures(contents, inner)
                except (InvalidAsset, struct.error) as exc:
                    prepared.missing_optional.append(f'BMT parse {inner}: {exc}')
                    texture_paths = []
                for texture in texture_paths:
                    extract_one(texture, required=False)
            if include_animations:
                for inner in refs.animations:
                    extract_one(inner, required=False)
        else:
            raise InvalidAsset(f'Expected BSR/CPD resource: {inner}')

    try:
        extract_one(selected, required=True)
        if ext == '.bsr':
            extract_resource(selected)
        elif ext == '.dof':
            data = parse_dof(content)
            for block in data['blocks']:
                extract_resource(block['path'])
                if include_objects:
                    for obj in block['objects']:
                        extract_resource(obj['path'])
        elif ext == '.nvm':
            data = parse_nvm(content)
            tiles = {f['tile_id'] for f in data['heightmap_faces']}
            tile_ifo = extract_one('tile2d.ifo', map_file=True)
            if tile_ifo:
                lines = tile_ifo.decode('cp1252').splitlines()
                if not lines or lines[0].strip() != 'JMXV2DTI1001':
                    raise InvalidAsset('Invalid tile2d.ifo signature')
                for line in lines[2:]:
                    match = re.match(r'^\s*(\d+)\s+\S+\s+"[^"]*"\s+"([^"]+)"', line)
                    if match and int(match[1]) in tiles:
                        extract_one('tile2d/' + match[2], map_file=True)
            if include_objects and data['objects']:
                ifo = extract_one('navmesh/object.ifo', required=True)
                ids = {o['asset_id'] for o in data['objects']}
                lines = ifo.decode('cp1252').splitlines()
                if not lines or lines[0].strip() != 'JMXVOBJI1000':
                    raise InvalidAsset('Invalid object.ifo signature')
                found = set()
                for line in lines[2:]:
                    match = re.match(r'^\s*(\d+)\s+\S+\s+"([^"]+)"', line)
                    if match and int(match[1]) in ids:
                        found.add(int(match[1]))
                        extract_resource(match[2])
                if ids - found:
                    raise InvalidAsset(f'object.ifo missing asset IDs: {sorted(ids - found)}')
        return prepared
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def unique_backup_path(archive: Path) -> Path:
    suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
    candidate = archive.with_name(archive.name + '.' + suffix + '.bak')
    index = 2
    while candidate.exists():
        candidate = archive.with_name(archive.name + '.' + suffix + f'_{index}.bak')
        index += 1
    return candidate


def replace_pk2_entry_safely(archive: str | Path, inner: str, data: bytes, key: str = '169841', *, backend=None):
    """Replace one existing asset, backup + staging + read-back check.

    Full backup is obligatory. Copy to a new archive on same drive, update the
    copy, verify exact bytes, copy source into backup, then atomically replace.
    The operation never calls remove_file or repacks unrelated asset types.
    """
    archive = Path(archive).resolve()
    inner = normalize_path(inner)
    if Path(inner).suffix.lower() != '.bms' or data[:12] != SIGNATURES['.bms']:
        raise InvalidAsset('PK2 write-back currently supports valid BMS meshes only')
    if backend is None:
        from pk2api import Pk2Stream
        backend = Pk2Stream
    if not archive.is_file():
        raise FileNotFoundError(str(archive))
    if not os.access(archive, os.W_OK):
        raise PermissionError('No permission to write PK2 archive')
    with backend(str(archive), key, read_only=True) as original:
        target = original.get_file(inner)
        if target is None:
            raise FileNotFoundError(f'Original BMS not found in PK2: {inner}')
        old = target.get_content()
        if not old.startswith(SIGNATURES['.bms']):
            raise InvalidAsset('The archive entry is not a valid BMS file')
    stat = shutil.disk_usage(archive.parent)
    # Full copy + separate backup: approximately double the existing archive size.
    estimated = 2 * archive.stat().st_size + len(data) + (64 * 1024 * 1024)
    if stat.free < estimated:
        raise OSError('Not enough disk space: approximately 2x PK2 size is required for staging and backup')
    stage_fd, stage_name = tempfile.mkstemp(prefix=archive.name + '.stage_', suffix='.pk2', dir=archive.parent)
    os.close(stage_fd)
    stage = Path(stage_name)
    backup = unique_backup_path(archive)
    try:
        shutil.copy2(archive, stage)
        with backend(str(stage), key, read_only=False) as changed:
            result = changed.add_file(inner, data)
            if result is False:
                raise OSError('PK2API add_file failed')
        with backend(str(stage), key, read_only=True) as reopened:
            entry = reopened.get_file(inner)
            if entry is None or entry.get_content() != data:
                raise OSError('PK2 BMS verification failed after writing')
        # Make backup before swap. Never overwrite an existing backup.
        with open(archive, 'rb') as source, open(backup, 'xb') as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        os.replace(stage, archive)
        return backup
    finally:
        if stage.exists():
            stage.unlink()
