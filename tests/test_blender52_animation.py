"""Blender 5.2 slotted-action compatibility without requiring bpy installation."""
import ast
from pathlib import Path
import sys
import types
import unittest

BASE = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'


def get_class():
    src = (BASE / 'JellyBAN.py').read_text()
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Import_JMXVBAN_0102')
    methods = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in ('ActionFCurve',)]
    m = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='Importer', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[]))
    ns = {}
    exec(compile(m, '<JellyBAN methods>', 'exec'), ns)
    return ns['Importer']


class Curves:
    def __init__(self):
        self.all = {}
        self.created = 0
    def new(self, path, *, index):
        self.created += 1
        curve = types.SimpleNamespace(keyframe_points=types.SimpleNamespace(insert=lambda f,v,options: types.SimpleNamespace(interpolation='BEZIER')))
        self.all[path,index] = curve
        return curve
    def find(self, path, *, index):
        return self.all.get((path,index))


class ModernAction:
    def __init__(self):
        self.curves = Curves()
        self.created = 0
    def fcurve_ensure_for_datablock(self, obj, path, *, index):
        assert obj.name == 'TestRig'
        self.created += 1
        return self.curves.find(path,index=index) or self.curves.new(path,index=index)


class TestBlender52Animation(unittest.TestCase):
    def test_modern_api_no_action_fcurves_and_cache(self):
        importer = get_class()()
        importer._fcurve_cache = {}
        importer.setting_interpolation_constant = False
        action = ModernAction()
        rig = types.SimpleNamespace(name='TestRig')
        for frame in range(100):
            importer.ActionFCurve(action, rig, 'pose.bones["Wolf"].location', frame, float(frame), 0)
        self.assertEqual(action.created, 1)
        self.assertEqual(action.curves.created, 1)
        self.assertEqual(len(importer._fcurve_cache), 1)

    def test_legacy_blender42_path(self):
        importer = get_class()()
        importer._fcurve_cache = {}
        importer.setting_interpolation_constant = True
        legacy = types.SimpleNamespace(fcurves=Curves())
        importer.ActionFCurve(legacy, types.SimpleNamespace(name='TestRig'), 'location', 1, 2, 0)
        self.assertEqual(legacy.fcurves.created, 1)

    def test_import_slot_is_created_before_nla_strip(self):
        src = (BASE / 'JellyBAN.py').read_text()
        start = src.index('action = bpy.data.actions.new(data[\'name\'])')
        part = src[start:src.index('self.ActionFCurve', start)]
        self.assertLess(part.index('action.slots.new'),part.index('nla_track.strips.new'))
        self.assertIn('obj.animation_data.action_slot = slot', part)

    def test_export_reads_modern_channelbag(self):
        src = (BASE / 'JellyBAN.py').read_text()
        self.assertIn('anim_utils.action_get_channelbag_for_slot',src)
        self.assertIn('keyframes = self.GetKeyframeSets(Action,Obj.animation_data.action_slot',src)

if __name__ == '__main__': unittest.main()
