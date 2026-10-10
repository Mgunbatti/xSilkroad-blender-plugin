"""Internationalization regression tests without Blender installed."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

BASE = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'
spec = importlib.util.spec_from_file_location('silkroad_lang_test', BASE / 'i18n.py')
localization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localization)


class LocalizeTests(unittest.TestCase):
    def test_default_language_is_english(self):
        tree = ast.parse((BASE / '__init__.py').read_text(encoding='utf-8'))
        field = next(n for n in ast.walk(tree) if isinstance(n, ast.AnnAssign)
                     and isinstance(n.target, ast.Name) and n.target.id == 'language')
        self.assertIn("default='EN'", ast.unparse(field))
        self.assertIn("('TR', 'Türkçe'", ast.unparse(field))
        self.assertEqual(localization.translate('PK2 Loading Status'), 'PK2 Loading Status')

    def test_all_ui_labels_are_translated(self):
        tree = ast.parse((BASE / '__init__.py').read_text(encoding='utf-8'))
        keys = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'_t','_status','_status_silent'}:
                i = 0 if n.func.id == '_t' else 1
                if len(n.args) > i and isinstance(n.args[i], ast.Constant) and isinstance(n.args[i].value, str):
                    keys.add(n.args[i].value)
        # Unknown computed labels are excluded; all hardcoded UI phrases should be localizable.
        missing = keys - localization.TURKISH.keys()
        self.assertEqual(missing, set(), f'Missing Turkish translations: {sorted(missing)}')
        self.assertGreater(len(keys), 60)

    def test_translations_preserve_placeholder_names(self):
        import string
        formatter = string.Formatter()
        for key, value in localization.TURKISH.items():
            vars_en = {k for _, k, _, _ in formatter.parse(key) if k}
            vars_tr = {k for _, k, _, _ in formatter.parse(value) if k}
            self.assertEqual(vars_en, vars_tr, msg=key)

    def test_language_switch_updates_status_without_touching_archive(self):
        tree = ast.parse((BASE / '__init__.py').read_text(encoding='utf-8'))
        needed = {'_on_language_change', '_status', '_t', '_status_silent'}
        methods = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
        props = SimpleNamespace(language='EN', archive='C:/Silkroad/Data.pk2',
                                selected_index=15, status_source='', status_values='', message='')
        redraws = []
        ns = {'bpy':SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(silkroad_editor=props))),
              'translate':localization.translate, '_redraw_pk2_panels':lambda:redraws.append('called')}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])),'<lang>','exec'),ns)
        ns['_status'](props, 'Imported into Blender: {path} | {count} objects{issues}',
                      path='res/mob/wolf.bsr', count=4, issues='')
        self.assertIn('Imported into Blender:', props.message)
        props.language='TR'
        ns['_on_language_change'](props,None)
        self.assertIn('Blender’a aktarıldı:',props.message)
        self.assertIn('wolf.bsr',props.message)
        self.assertEqual(props.selected_index,15)
        self.assertEqual(props.archive,'C:/Silkroad/Data.pk2')
        props.language='EN'
        ns['_on_language_change'](props,None)
        self.assertIn('Imported into Blender:', props.message)
        self.assertEqual(len(redraws),2)

    def test_fbx_export_is_still_functionally_integrated(self):
        source = (BASE / '__init__.py').read_text(encoding='utf-8')
        self.assertIn('export_fbx_with_textures(', source)
        self.assertIn("bl_idname = 'silkroad_editor.export_fbx'",source)
        self.assertIn("props, 'language', text='', expand=True", source)
        self.assertIn("'export_png_textures'", source)
        self.assertIn("'export_animation'", source)

    def test_turkish_diagnostics_and_formatting(self):
        tr = localization.translate('Could not open PK2: {error}', 'TR', error='File missing')
        self.assertEqual(tr, 'PK2 açılamadı: File missing')
        self.assertEqual(localization.translate_error('PK2 archive not found: C:/Data.pk2', 'TR'),
                         'PK2 arşivi bulunamadı: C:/Data.pk2')
        self.assertEqual(localization.translate_error('PK2 archive not found: C:/Data.pk2', 'EN'),
                         'PK2 archive not found: C:/Data.pk2')

    def test_error_status_translates_when_language_changes(self):
        tree = ast.parse((BASE / '__init__.py').read_text(encoding='utf-8'))
        needed = {'_on_language_change', '_status', '_t'}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
        props = SimpleNamespace(language='EN', status_source='', status_values='', message='')
        ns = {'bpy':SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(silkroad_editor=props))),
              'translate':localization.translate, 'translate_error':localization.translate_error,
              '_redraw_pk2_panels':lambda:None}
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),'<lang>','exec'),ns)
        ns['_status'](props, 'Error: {error}', error='PK2 archive not found: C:/Data.pk2')
        self.assertIn('Error:', props.message)
        props.language='TR'
        ns['_on_language_change'](props,None)
        self.assertIn('Hata: PK2 arşivi bulunamadı:', props.message)
        props.language='EN'
        ns['_on_language_change'](props,None)
        self.assertIn('Error: PK2 archive not found:', props.message)

    def test_ui_strings_are_english_first(self):
        source = (BASE / '__init__.py').read_text(encoding='utf-8')
        self.assertIn("bl_label = 'Import Selected Model'", source)
        self.assertIn("bl_label = 'Export UE5 FBX + PNG'", source)
        self.assertIn("Error: {error}", localization.TURKISH)


if __name__ == '__main__': unittest.main()
