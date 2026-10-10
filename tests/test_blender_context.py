"""Regression tests for Blender 5.2 context.poll import failure.

Execute the two small helpers with a bpy test double (real Blender is not installed).
"""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import ast
import unittest

BASE = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'


def helper_namespace(bpy):
    tree = ast.parse((BASE / '__init__.py').read_text())
    fn_names = {'_viewport_operator_context', '_ensure_object_mode'}
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in fn_names]
    assert len(nodes) == 2
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    ns = {'bpy': bpy, 'contextmanager': contextmanager, '_t':lambda x,*a,**kw:x}
    exec(compile(module, '<helpers>', 'exec'), ns)
    return ns


class ContextMock:
    def __init__(self, old_mode='POSE'):
        self.viewport_region = SimpleNamespace(type='WINDOW')
        self.panel_region = SimpleNamespace(type='UI')
        self.viewport = SimpleNamespace(type='VIEW_3D', regions=[self.panel_region, self.viewport_region])
        self.screen = SimpleNamespace(areas=[self.viewport])
        self.window = SimpleNamespace(screen=self.screen)
        self.invoke_context = SimpleNamespace(window=self.window, area=self.viewport, region=self.panel_region)
        self.active_region = self.panel_region
        self.object = SimpleNamespace(mode=old_mode)
        self.last_transition = []
        self.bpy = SimpleNamespace()
        self.bpy.context = SimpleNamespace(object=self.object, temp_override=self._temp_override)
        def mode_set(*, mode):
            return self._mode_set(mode=mode)
        mode_set.poll = lambda: self.active_region is self.viewport_region
        self.bpy.ops = SimpleNamespace(object=SimpleNamespace(mode_set=mode_set))

    @contextmanager
    def _temp_override(self, *, window, area, region):
        assert window == self.window
        assert area == self.viewport
        previous = self.active_region
        self.active_region = region
        try:
            yield
        finally:
            self.active_region = previous

    def _mode_set(self, *, mode):
        if self.active_region is not self.viewport_region:
            raise RuntimeError('poll failed, context is incorrect')
        self.last_transition.append(mode)
        self.object.mode = mode
        return {'FINISHED'}


class TestBlenderViewportContext(unittest.TestCase):
    def test_from_n_panel_pose_mode_import_goes_to_viewport_object_mode(self):
        fake = ContextMock()
        ns = helper_namespace(fake.bpy)
        with ns['_viewport_operator_context'](fake.invoke_context):
            self.assertIs(fake.active_region, fake.viewport_region)
            ns['_ensure_object_mode']()
            self.assertEqual(fake.object.mode, 'OBJECT')
        self.assertIs(fake.active_region, fake.panel_region)
        self.assertEqual(fake.last_transition, ['OBJECT'])

    def test_from_object_mode_does_not_switch(self):
        fake = ContextMock('OBJECT')
        ns = helper_namespace(fake.bpy)
        with ns['_viewport_operator_context'](fake.invoke_context):
            ns['_ensure_object_mode']()
        self.assertEqual(fake.last_transition, [])

    def test_missing_viewport_gives_helpful_error(self):
        fake = ContextMock()
        fake.viewport.type = 'PROPERTIES'
        ns = helper_namespace(fake.bpy)
        with self.assertRaisesRegex(RuntimeError, '3D Viewport'):
            with ns['_viewport_operator_context'](fake.invoke_context):
                pass

    def test_bsr_switches_to_object_mode_before_deselect(self):
        source = (BASE / 'JellyBSR.py').read_text()
        process = source[source.index('\tdef ProcessData('):]
        self.assertLess(process.index("BlenderSetMode('OBJECT')"),
                        process.index("bpy.ops.object.select_all(action='DESELECT')"))

    def test_import_and_export_both_have_viewport_override(self):
        source = (BASE / '__init__.py').read_text()
        self.assertIn('with _viewport_operator_context(context):\n                _ensure_object_mode()\n                result = operation(**bsc)', source)
        self.assertIn('with _viewport_operator_context(context):\n                _ensure_object_mode()\n                data = _export_bms(obj)', source)


if __name__ == '__main__':
    unittest.main()
