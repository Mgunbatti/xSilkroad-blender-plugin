"""Lightweight UI layout test without importing Blender."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

MOD = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge' / '__init__.py'

class FakeLayout:
    def __init__(self, calls): self.calls = calls
    def box(self): return FakeLayout(self.calls)
    def row(self, **kw): return FakeLayout(self.calls)
    def column(self, **kw): return FakeLayout(self.calls)
    def label(self, **kw): self.calls.append(('label', kw))
    def progress(self, **kw): self.calls.append(('progress', kw))
    def operator(self, name, **kw):
        self.calls.append(('operator', {'name':name, **kw}))
        return SimpleNamespace(action=None)
    def prop(self, *args, **kw): self.calls.append(('prop', kw))
    def template_list(self, *args, **kw): self.calls.append(('list', kw))
    def __setattr__(self,key,val): object.__setattr__(self,key,val)

class Settings:
    def __init__(self):
        self.archive='C:/Data.pk2'
        self.language='EN'
        self.key='169841'
        self.scan_state='LOADING'
        self.scan_visual=0.62
        self.scan_archive='Data.pk2'
        self.scan_blocks=1200
        self.scan_has_counter=True
        self.loading=True
        self.current_folder=''
        self.message='some status'
        self.search_mode=False
        self.entries=[]
        self.selected_index=-1
        self.search_query=''
        self.load_animations=False

class TestProgressUi(unittest.TestCase):
    def setUp(self):
        tree=ast.parse(MOD.read_text(encoding='utf-8'))
        panel=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == 'SILKROAD_PT_Editor')
        method=next(n for n in panel.body if isinstance(n,ast.FunctionDef) and n.name=='draw')
        helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_draw_green_progress')
        fn=ast.FunctionDef(name='panel_draw',args=method.args,body=method.body,
                           decorator_list=[],returns=None,type_comment=None)
        ns={'_activate_engine':lambda:True,'_session':None,'_progress_previews':None,
            '_t':lambda message, props=None, **kw:message.format(**kw) if kw else message, 'Path':Path,
            'SUPPORTED_EXTS':{'.bsr','.bms'},'os':__import__('os')}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,fn],type_ignores=[])),'ui','exec'),ns)
        self.draw=ns['panel_draw']
        self.props=Settings()
        self.calls=[]

    def render(self):
        context=SimpleNamespace(scene=SimpleNamespace(silkroad_editor=self.props),active_object=None)
        panel=SimpleNamespace(layout=FakeLayout(self.calls))
        self.draw(panel,context)
        return self.calls

    def test_progress_bar_is_at_top_before_archive_picker(self):
        calls=self.render()
        bar_index=next(i for i,c in enumerate(calls) if c[0]=='progress')
        picker_index=next(i for i,c in enumerate(calls) if c[0]=='operator'
                          and c[1]['name']=='silkroad_editor.open_archive')
        self.assertLess(bar_index,picker_index)
        self.assertEqual(calls[bar_index][1]['factor'],0.62)
        self.assertIn('Scanning',calls[bar_index][1]['text'])
        self.assertTrue(any('1200 PK2 blocks' in call[1].get('text','')
                            for call in calls if call[0]=='label'))
        self.assertTrue(any(c[1].get('name')=='silkroad_editor.cancel_scan'
                            for c in calls if c[0]=='operator'))

    def test_green_previews_render_segments_before_archive_picker(self):
        # Image previews produce truly green segments regardless of Blender theme.
        # Preview IDs represent fixed PNG assets; no actual bpy runtime necessary.
        self.draw.__globals__['_progress_previews'] = {
            'green':SimpleNamespace(icon_id=701),
            'dim':SimpleNamespace(icon_id=702),
        }
        calls=self.render()
        icons=[c[1]['icon_value'] for c in calls if c[0]=='label' and 'icon_value' in c[1]]
        self.assertEqual(len(icons),10)
        self.assertIn(701,icons)
        self.assertIn(702,icons)
        first_icon=next(i for i,c in enumerate(calls) if c[0]=='label' and 'icon_value' in c[1])
        picker=next(i for i,c in enumerate(calls) if c[0]=='operator' and c[1]['name']=='silkroad_editor.open_archive')
        self.assertLess(first_icon,picker)

    def test_turkish_panel_switches_labels_without_changing_archive(self):
        from importlib.util import spec_from_file_location, module_from_spec
        module_path = MOD.parent / 'i18n.py'
        spec = spec_from_file_location('i18n_ui_test', module_path)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.draw.__globals__['_t'] = lambda key, props=None, **kw: mod.translate(
            key, getattr(props, 'language', 'EN'), **kw)
        self.props.language = 'TR'
        old_archive = self.props.archive
        calls = self.render()
        labels = [data.get('text', '') for typ, data in calls if typ == 'label']
        buttons = [data.get('text', '') for typ, data in calls if typ == 'operator']
        self.assertIn('PK2 Yükleme Durumu', labels)
        self.assertIn('1. PK2 Arşivini Aç', labels)
        self.assertIn('Klasöre Gir', buttons)
        self.assertIn('.fbx + PNG Aktar', buttons)
        self.assertEqual(self.props.archive, old_archive)

    def test_ready_fills_bar(self):
        self.props.loading=False
        self.props.scan_state='READY'
        self.props.scan_visual=1.0
        calls=self.render()
        progress=[value for name,value in calls if name=='progress']
        self.assertEqual(progress[0]['factor'],1.0)
        self.assertFalse(any(c[1].get('name')=='silkroad_editor.cancel_scan'
                             for c in calls if c[0]=='operator'))

    def test_legacy_status_without_fake_percentage(self):
        self.props.scan_has_counter=False
        calls=self.render()
        self.assertTrue(any('engine has no block counter' in c[1].get('text','')
                            for c in calls if c[0]=='label'))
        self.assertFalse(any('%' in c[1].get('text','') for c in calls if c[0]=='label'))

if __name__=='__main__': unittest.main()
