"""Malformed real-world BMT metadata must not abort BSR mesh imports.

Offline synthetic fixtures; does not claim to validate Harrison's original data.
"""
import ast
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'
spec = importlib.util.spec_from_file_location('bmt_safe', ROOT / 'bmt_safe.py')
from sys import modules
module = importlib.util.module_from_spec(spec)
modules[spec.name] = module
spec.loader.exec_module(module)
parse_bmt_safe = module.parse_bmt_safe


def u(n):
    return struct.pack('<I', n)


def st(value):
    data = value.encode('cp1252')
    return u(len(data)) + data


def record(name, path, relative=1, flags=0, normal=b''):
    payload = st(name) + bytes(68) + u(flags) + st(path) + bytes(6) + bytes([relative])
    if flags & 0x2000:
        payload += u(len(normal)) + normal + bytes(4)
    return payload


class TestBmtSafe(unittest.TestCase):
    def test_valid_material(self):
        content = b'JMXVBMT 0102' + u(1) + record('Armor', 'prim\\texture\\armor.ddj')
        result, warning = parse_bmt_safe(content)
        self.assertIsNone(warning)
        self.assertEqual([(x.name, x.texture_path, x.relative_to_data) for x in result],
                         [('Armor', 'prim\\texture\\armor.ddj', True)])

    def test_normal_flag(self):
        content = b'JMXVBMT 0102' + u(1) + record('A', 'foo.dds', 0, 0x2000, b'normal.dds')
        result, warning = parse_bmt_safe(content)
        self.assertIsNone(warning)
        self.assertEqual(result[0].name, 'A')
        self.assertFalse(result[0].relative_to_data)

    def test_giant_string_length_at_offset_146_in_232_byte_bmt(self):
        # Reproduces the dangerous length reported by a user's Harrison error:
        # >1 billion bytes requested when only 232 bytes exist.
        prefix = b'JMXVBMT 0102' + u(2) + record('A' * 31, 'path.dds')
        buf = bytearray(prefix + bytes(max(0, 146 - len(prefix))))
        # 146 is the data offset *after* the four-byte length.
        buf[142:146] = u(1_058_449_951)
        buf += bytes(max(0, 232 - len(buf)))
        results, warning = parse_bmt_safe(bytes(buf))
        self.assertEqual(len(results), 1)
        self.assertIn('implausible', warning)

    def test_bad_count_rejected(self):
        content = b'JMXVBMT 0102' + u(0xffff_ffff) + bytes(216)
        result, warning = parse_bmt_safe(content)
        self.assertEqual(result, [])
        self.assertIn('material count', warning)

    def test_truncated_string_keeps_prior_records(self):
        content = (b'JMXVBMT 0102' + u(2) + record('OK','okay.dds')
                   + u(5000) + bytes(90))
        result, warning = parse_bmt_safe(content)
        self.assertEqual(result[0].name, 'OK')
        self.assertIn('exceeds file', warning)

    def test_unsupported_signature_returns_warning(self):
        result, warning = parse_bmt_safe(b'BADFILE' + bytes(230))
        self.assertEqual(result, [])
        self.assertIn('signature', warning)

    def test_jellybms_calls_guarded_reader_and_continues(self):
        text = (ROOT / 'JellyBMS.py').read_text()
        ast.parse(text)
        self.assertIn('parse_bmt_safe(f.read())', text)
        self.assertIn('Continuing without invalid material entries', text)
        self.assertIn('if not data[\'material_filepath\']:', text)


if __name__ == '__main__':
    unittest.main()
