"""Offline export regression tests. These do not prove Blender 5.2/UE import."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge' / 'fbx_texture_export.py'
spec = importlib.util.spec_from_file_location('texture_bridge_test', MODULE_PATH)
import sys
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)


class FakeImage:
    _next_id = 100

    def __init__(self, name, filepath, *, missing=False, source='FILE'):
        self.name, self.filepath = name, filepath
        self.file_format = ''  # Blender 5.2 reports an empty enum for loaded DDS
        self.source = source
        self.library = None
        self.colorspace_settings = SimpleNamespace(name='sRGB')
        self.missing = missing
        self.id = FakeImage._next_id
        FakeImage._next_id += 1

    def as_pointer(self):
        return self.id

    def save_render(self, filepath, *, scene=None):
        assert scene is not None
        assert scene.render.image_settings.file_format == 'PNG'
        assert scene.render.image_settings.color_mode == 'RGBA'
        assert scene.render.image_settings.color_depth == '8'
        assert self.file_format == ''  # Source DDS enum must never be mutated.
        self.last_view_transform = scene.view_settings.view_transform
        if self.missing:
            raise IOError('DDS missing or unsupported')
        Path(filepath).write_bytes(bridge.PNG_SIGNATURE + bytes(64))


class FakeNode:
    def __init__(self, image=None, *, node_type='TEX_IMAGE'):
        self.image = image
        self.type = node_type
        self.name = 'Image Texture'


class FakeMaterial:
    _next_id = 10

    def __init__(self, name, nodes):
        self.name = name
        self.use_nodes = True
        self.node_tree = SimpleNamespace(nodes=nodes)
        self.id = FakeMaterial._next_id
        FakeMaterial._next_id += 1

    def as_pointer(self):
        return self.id

    def copy(self):
        return FakeMaterial(self.name + '_copy',
                            [FakeNode(n.image, node_type=n.type) for n in self.node_tree.nodes])


class FakeCollection:
    def __init__(self, kind):
        self.kind = kind
        self.loaded = []
        self.removed = []

    def load(self, filepath, check_existing=False):
        assert Path(filepath).is_file()
        image = FakeImage(Path(filepath).stem, filepath)
        self.loaded.append(image)
        return image

    def remove(self, obj, do_unlink=True):
        assert do_unlink is True
        self.removed.append(obj)


class FakeScenes:
    def __init__(self):
        self.created = []
        self.removed = []

    def new(self, name):
        settings = SimpleNamespace(file_format='JPEG', color_mode='RGB', color_depth='16', compression=5)
        scene = SimpleNamespace(
            name=name,
            render=SimpleNamespace(image_settings=settings),
            display_settings=SimpleNamespace(display_device='sRGB'),
            view_settings=SimpleNamespace(exposure=1.0, gamma=2.0,
                                          look='High Contrast', view_transform='AgX'),
        )
        self.created.append(scene)
        return scene

    def remove(self, scene):
        self.removed.append(scene)


class FakeExporter:
    def __init__(self, fake_bpy, *, outcome='FINISHED'):
        self.fake_bpy = fake_bpy
        self.outcome = outcome
        self.calls = []

    def __call__(self, how, **params):
        assert how == 'EXEC_DEFAULT'
        self.calls.append(params)
        selected = self.fake_bpy.selected
        self.image_paths_seen = [
            n.image.filepath if n.image else None
            for o in selected if o.type == 'MESH'
            for s in o.material_slots if s.material
            for n in s.material.node_tree.nodes if n.type == 'TEX_IMAGE'
        ]
        if self.outcome == 'ERROR':
            raise ValueError('Blender exporter crashed')
        if self.outcome == 'CANCELLED':
            return {'CANCELLED'}
        Path(params['filepath']).write_bytes(b'FBXTestSampleData')
        return {'FINISHED'}


class TestFBXTextureExport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.image = FakeImage('bonelord.dds', r'C:\PK2\bonelord.dds')
        self.original_mat = FakeMaterial('bonelord1', [FakeNode(self.image)])
        self.mesh = SimpleNamespace(type='MESH', material_slots=[SimpleNamespace(material=self.original_mat)])
        self.rig = SimpleNamespace(type='ARMATURE', material_slots=[])
        self.bpy = SimpleNamespace()
        self.bpy.selected = [self.mesh, self.rig]
        self.bpy.data = SimpleNamespace(materials=FakeCollection('materials'), images=FakeCollection('images'),
                                        scenes=FakeScenes())
        self.exporter = FakeExporter(self.bpy)
        self.bpy.ops = SimpleNamespace(export_scene=SimpleNamespace(fbx=self.exporter))

    def test_png_replaces_dds_only_during_export(self):
        target = self.out / 'Bonelord_Attack01.fbx'
        result = bridge.export_fbx_with_textures(self.bpy, target, self.bpy.selected)
        self.assertEqual(result.converted, 1)
        self.assertEqual(result.missing, [])
        self.assertTrue(target.is_file())
        self.assertEqual(self.image.file_format, '')
        self.assertIs(self.mesh.material_slots[0].material, self.original_mat)
        self.assertIs(self.original_mat.node_tree.nodes[0].image, self.image)
        self.assertEqual(len(self.bpy.data.images.removed), 1)
        self.assertEqual(len(self.bpy.data.materials.removed), 1)
        self.assertEqual(self.bpy.data.scenes.created, self.bpy.data.scenes.removed)
        self.assertEqual(self.image.last_view_transform, 'Standard')
        self.assertEqual(len(self.exporter.image_paths_seen), 1)
        png = Path(self.exporter.image_paths_seen[0])
        self.assertEqual(png.suffix, '.png')
        self.assertTrue((result.texture_folder / png.name).is_file())
        self.assertIn('bonelord.dds', result.report.read_text(encoding='utf-8'))
        params = self.exporter.calls[0]
        self.assertEqual(params['path_mode'], 'RELATIVE')
        self.assertFalse(params['embed_textures'])
        self.assertFalse(params['add_leaf_bones'])
        self.assertFalse(params['bake_anim_use_nla_strips'])
        self.assertFalse(params['bake_anim_use_all_actions'])

    def test_non_color_texture_is_written_using_raw_transform(self):
        self.image.colorspace_settings.name = 'Non-Color'
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'Normal.fbx', self.bpy.selected)
        self.assertEqual(result.converted, 1)
        self.assertEqual(self.image.last_view_transform, 'Raw')
        self.assertEqual(self.image.file_format, '')
        self.assertEqual(self.bpy.data.scenes.created, self.bpy.data.scenes.removed)

    def test_png_failure_removes_temporary_scene(self):
        self.image.missing = True
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'FailedTexture.fbx', self.bpy.selected)
        self.assertEqual(result.converted, 0)
        self.assertEqual(self.bpy.data.scenes.created, self.bpy.data.scenes.removed)
        self.assertEqual(self.image.file_format, '')
        self.assertEqual(len(result.missing), 1)

    def test_when_textures_disabled_no_temporary_scene_created(self):
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'MeshOnly.fbx',
                                                 self.bpy.selected, textures=False)
        self.assertTrue(result.fbx.is_file())
        self.assertEqual(self.bpy.data.scenes.created, [])

    def test_broken_image_reported_without_unsafe_dds_reference(self):
        self.image.missing = True
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'Broken.fbx', self.bpy.selected)
        self.assertEqual(result.converted, 0)
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(self.exporter.image_paths_seen, [None])
        self.assertIn('DDS missing', result.report.read_text(encoding='utf-8'))
        self.assertIs(self.mesh.material_slots[0].material, self.original_mat)

    def test_failure_rolls_back_without_touching_existing_fbx(self):
        target = self.out / 'Old.fbx'
        target.write_bytes(b'ORIGINAL')
        self.exporter.outcome = 'ERROR'
        with self.assertRaisesRegex(ValueError, 'crashed'):
            bridge.export_fbx_with_textures(self.bpy, target, self.bpy.selected)
        self.assertEqual(target.read_bytes(), b'ORIGINAL')
        self.assertIs(self.mesh.material_slots[0].material, self.original_mat)
        self.assertEqual(self.image.file_format, '')
        self.assertFalse((self.out / 'Old_textures').exists())
        self.assertEqual(list(self.out.glob('.silkroad_fbx_*')), [])

    def test_reexport_keeps_previous_sidecar(self):
        name = self.out / 'Reexport.fbx'
        first = bridge.export_fbx_with_textures(self.bpy, name, self.bpy.selected)
        second = bridge.export_fbx_with_textures(self.bpy, name, self.bpy.selected)
        self.assertNotEqual(first.texture_folder, second.texture_folder)
        self.assertTrue(first.texture_folder.exists())
        self.assertTrue(second.texture_folder.exists())
        self.assertEqual(len(list(self.out.glob('*.fbx'))), 1)

    def test_shared_material_converted_once(self):
        mesh2 = SimpleNamespace(type='MESH', material_slots=[SimpleNamespace(material=self.original_mat)])
        self.bpy.selected.insert(1, mesh2)
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'Shared.fbx', self.bpy.selected)
        self.assertEqual(result.converted, 1)
        self.assertIs(mesh2.material_slots[0].material, self.original_mat)
        self.assertEqual(len(self.bpy.data.materials.removed), 1)

    def test_static_mesh_can_export_without_rig(self):
        result = bridge.export_fbx_with_textures(self.bpy, self.out / 'Static.fbx', [self.mesh])
        self.assertEqual(len(result.missing), 1)
        self.assertIn('No armature', result.report.read_text(encoding='utf-8'))

    def test_invalid_selection_and_suffix_do_nothing(self):
        with self.assertRaisesRegex(ValueError, 'Mesh'):
            bridge.export_fbx_with_textures(self.bpy, self.out / 'foo.fbx', [self.rig])
        with self.assertRaisesRegex(ValueError, '.fbx'):
            bridge.export_fbx_with_textures(self.bpy, self.out / 'foo.blend', self.bpy.selected)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_filename_normalization(self):
        self.assertFalse(any(c in bridge.clean_filename('../bad:<texture>?') for c in '/\\:*?'))
        self.assertEqual(bridge.clean_filename('CON'), 'texture')
        self.assertTrue(bridge.texture_filename(self.image).endswith('.png'))


if __name__ == '__main__':
    unittest.main()
