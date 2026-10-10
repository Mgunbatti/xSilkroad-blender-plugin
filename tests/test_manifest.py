"""Static addon/package checks without bpy, for regression coverage."""
from pathlib import Path
import ast
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'

class TestAddon(unittest.TestCase):
    def test_manifest_and_registration(self):
        manifest = tomllib.loads((ROOT / 'blender_manifest.toml').read_text(encoding='utf-8'))
        self.assertEqual(manifest['id'], 'silkroad_pk2_bridge')
        self.assertEqual(manifest['version'], '2.4.2')
        source = (ROOT / '__init__.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        self.assertTrue({'SILKROAD_PT_Editor', 'SILKROAD_OT_OpenArchive',
                         'SILKROAD_OT_ImportFromPk2', 'SILKROAD_OT_SaveBmsToPk2'} <= names)
        self.assertIn('from . import JellyBMS', source)

    def test_all_jelly_importers_are_bundled(self):
        for name in ('JellyBMS','JellyBSR','JellyBSK','JellyBAN','JellyDOF','JellyNVM'):
            self.assertTrue((ROOT / (name + '.py')).is_file())

if __name__ == '__main__':
    unittest.main()
