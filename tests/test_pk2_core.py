"""Offline tests using synthetic archive and Joymax resource binary fixtures.

No actual Silkroad copyrighted assets or Blender required.
"""
from pathlib import Path
import importlib.util
import pickle
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'
sys.modules['silkroad_pk2_bridge'] = types.ModuleType('silkroad_pk2_bridge')
sys.modules['silkroad_pk2_bridge'].__path__ = [str(ROOT)]
for name in ('bridge_core', 'pk2_core'):
    spec = importlib.util.spec_from_file_location(f'silkroad_pk2_bridge.{name}', ROOT / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from silkroad_pk2_bridge import pk2_core as core


def u32(n):
    return struct.pack('<I', n)


def st(value):
    raw = value.encode('cp1252')
    return u32(len(raw)) + raw


def bms(name):
    return b'JMXVBMS 0110' + b'\x00' * 40 + b'\x00' * 20 + st(name) + b'\x00' * 64


def bsr():
    data = b'JMXVRES 0109' + b'\0' * 32 + u32(1) + b'\0' * 16
    data += b'\0' * 4 + st('My Monster') + b'\0' * 48
    data += u32(0) + b'\0' * 48 + u32(0)
    data += u32(1) + u32(0) + st(r'prim\mtrl\monster.bmt')
    data += u32(1) + st(r'prim\mesh\monster.bms') + b'\0' * 4
    data += b'\0' * 8 + u32(1) + st(r'prim\anim\monster.ban')
    data += u32(1) + st(r'prim\bone\monster.bsk')
    return data


def bmt():
    return (b'JMXVBMT 0102' + u32(1) + st('Monster Mat') + b'\0' * 68 + u32(0)
            + st(r'prim\texture\monster.ddj') + b'\0' * 6 + b'\x01')


class FakeEntry:
    def __init__(self, files, path):
        self.files, self.path = files, path
        self.name = path.rsplit('/', 1)[-1]
        self.original_name = self.name
        self.size = len(files[path])

    def get_content(self):
        return self.files[self.path]

    def get_full_path(self):
        return self.path


class FakeFolder:
    def __init__(self, files, path):
        self.original_name = path.rsplit('/', 1)[-1] if path else ''
        self.path = path
        prefix = f'{path}/' if path else ''
        subfolders = {}
        self.files = {}
        for filepath in files:
            if not filepath.startswith(prefix):
                continue
            tail = filepath[len(prefix):]
            if '/' not in tail:
                self.files[tail] = FakeEntry(files, filepath)
            else:
                subfolder = tail.split('/')[0]
                subfolders[subfolder] = prefix + subfolder
        self.folders = {k: FakeFolder(files, path) for k, path in subfolders.items()}

    def get_full_path(self):
        return self.path


class FakePk2Stream:
    def __init__(self, path, key, read_only=False):
        self.path = Path(path)
        self.read_only = read_only
        self.files = pickle.loads(self.path.read_bytes())
        self.closed = False

    def get_file(self, inner):
        inner = inner.strip('/').lower()
        return FakeEntry(self.files, inner) if inner in self.files else None

    def get_folder(self, inner):
        inner = inner.strip('/').lower()
        if inner and not any(key.startswith(inner + '/') for key in self.files):
            return None
        return FakeFolder(self.files, inner)

    def iter_files(self):
        for path in sorted(self.files):
            yield FakeEntry(self.files, path)

    def add_file(self, inner, data):
        if self.read_only:
            raise PermissionError
        self.files[inner.lower()] = data
        return True

    def __enter__(self):
        return self

    def close(self):
        if not self.closed and not self.read_only:
            self.path.write_bytes(pickle.dumps(self.files))
        self.closed = True

    def __exit__(self, *args):
        self.close()


def archive(path, contents):
    path.write_bytes(pickle.dumps(contents))


class TestCore(unittest.TestCase):
    def test_paths_and_bms_header(self):
        self.assertEqual(core.normalize_path(r'prim\mesh\MONSTER.bms'), 'prim/mesh/monster.bms')
        self.assertEqual(core.decode_bms_name(bms('monster_body')), 'monster_body')
        for path in ('../bad', 'prim/../../bad', 'C:/absolute', 'a//b', 'a/./b', '/absolute'):
            with self.subTest(path=path), self.assertRaises(core.InvalidAsset):
                core.normalize_path(path)

    def test_bmt_texture_paths(self):
        self.assertEqual(core.parse_bmt_textures(bmt(), 'prim/mtrl/monster.bmt'),
                         ['prim/texture/monster.ddj'])
        self.assertEqual(core.parse_bmt_textures(b'BAD', 'prim/mtrl/test.bmt'), [])


    def test_legacy_pk2api_does_not_accept_progress(self):
        # The actual installed pk2api 1.5.0 can raise exactly this TypeError.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Data.pk2'
            archive(path, {'mesh/test.bms': bms('test')})
            calls = []
            with core.ArchiveSession(path, backend=FakePk2Stream,
                                     progress=lambda *args: calls.append(args)) as sess:
                self.assertEqual(sess.get('mesh/test.bms')[0], bms('test'))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1:], (None, None))

    def test_unrelated_constructor_typeerror_is_not_masked(self):
        class BadPk2:
            def __init__(self, path, key, read_only=True, progress=None):
                raise TypeError('internal corrupted PK2 parsing error')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Data.pk2'
            path.write_bytes(b'x')
            with self.assertRaisesRegex(TypeError, 'internal corrupted'):
                core.ArchiveSession(path, backend=BadPk2, progress=lambda *x: None)

    def test_archive_search_and_browse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root / 'Media.pk2'
            archive(media, {'prim/a.bsr': bsr(), 'prim/mesh/bms.bms': bms('mesh1'), 'info.txt': b'hello'})
            with core.ArchiveSession(media, backend=FakePk2Stream) as session:
                self.assertEqual([x['name'] for x in session.list_folder('')], ['prim', 'info.txt'])
                self.assertEqual(session.search('BMS')[0]['path'], 'prim/mesh/bms.bms')
                self.assertEqual(session.get('prim/a.bsr')[0], bsr())

    def test_bsr_dependencies_from_multiple_pk2(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root / 'Media.pk2'
            data = root / 'Data.pk2'
            archive(media, {'prim/model/monster.bsr': bsr(), 'prim/mesh/monster.bms': bms('monster_body'),
                            'prim/bone/monster.bsk': b'JMXVBSK 0101' + b'\0'*50})
            archive(data, {'prim/mtrl/monster.bmt': bmt(),
                           'prim/texture/monster.ddj': b'\x00'*20 + b'DDS ' + b'\0'*36})
            with core.ArchiveSession(media, backend=FakePk2Stream) as session:
                prepared = core.prepare_asset(session, 'prim/model/monster.bsr', base_dir=folder)
                self.assertTrue((prepared.data_root / 'prim/mesh/monster.bms').is_file())
                self.assertTrue((prepared.data_root / 'prim/bone/monster.bsk').is_file())
                self.assertTrue((prepared.data_root / 'prim/texture/monster.ddj').is_file())
                self.assertEqual(prepared.meshes, {'monster_body': 'prim/mesh/monster.bms'})
                self.assertEqual(prepared.sources['prim/texture/monster.ddj'].name, 'Data.pk2')
                self.assertEqual(prepared.missing_optional, [])

    def test_missing_required_mesh_stops_import(self):
        with tempfile.TemporaryDirectory() as folder:
            media = Path(folder) / 'Media.pk2'
            archive(media, {'prim/model/monster.bsr': bsr()})
            with core.ArchiveSession(media, backend=FakePk2Stream) as session:
                with self.assertRaises(FileNotFoundError):
                    core.prepare_asset(session, 'prim/model/monster.bsr', base_dir=folder)

    def test_direct_pk2_write_is_verified_and_backed_up(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Media.pk2'
            old = bms('old_mesh')
            new = bms('edited_mesh')
            contents = {'prim/mesh/monster.bms': old, 'other/test.txt': b'unmodified'}
            archive(path, contents)
            backup = core.replace_pk2_entry_safely(path, 'prim/mesh/monster.bms', new,
                                                   backend=FakePk2Stream)
            self.assertEqual(pickle.loads(backup.read_bytes()), contents)
            self.assertEqual(pickle.loads(path.read_bytes())['prim/mesh/monster.bms'], new)
            self.assertEqual(pickle.loads(path.read_bytes())['other/test.txt'], b'unmodified')
            self.assertTrue(backup.name.endswith('.bak'))

    def test_refuse_non_bms_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Media.pk2'
            archive(path, {'x.bms': bms('a')})
            with self.assertRaises(core.InvalidAsset):
                core.replace_pk2_entry_safely(path, 'monster.bsr', b'JMXVRES 0109', backend=FakePk2Stream)


if __name__ == '__main__':
    unittest.main()
