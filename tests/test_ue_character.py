import importlib,sys,types,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge'
if 'silkroad_pk2_bridge' not in sys.modules:
    package=types.ModuleType('silkroad_pk2_bridge');package.__path__=[str(ROOT)];sys.modules['silkroad_pk2_bridge']=package
ue=importlib.import_module('silkroad_pk2_bridge.ue_character')

class TestCharacterTarget(unittest.TestCase):
    def test_requires_existing_project(self):
        with self.assertRaises(ValueError):ue.validate_target('not_existing.uproject')
    def test_disabled_python_plugin_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'Test.uproject';p.write_text(json.dumps({'Plugins':[{'Name':'PythonScriptPlugin','Enabled':False}]}))
            with self.assertRaises(ValueError):ue.validate_target(p)
    def test_target_is_validated_without_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'Test.uproject';raw=json.dumps({'Plugins':[{'Name':'PythonScriptPlugin','Enabled':True}],'Description':'Preserve this project'}).encode();p.write_bytes(raw)
            self.assertEqual(ue.validate_target(p),p.resolve());self.assertEqual(p.read_bytes(),raw)
    def test_rejects_non_bsr(self):
        for path in ('wolf.ban','wolf.bsk','wolf.bms'):
            with self.assertRaises(ValueError):ue.character_name(path)
    def test_same_basename_in_different_folders_is_distinct(self):
        self.assertNotEqual(ue.character_name('res/a/wolf.bsr'),ue.character_name('res/b/wolf.bsr'))
    def test_character_names_are_safe(self):
        self.assertRegex(ue.character_name('res/mob/some name (1).BSR'),r'^C_[A-Za-z0-9_]+$')

if __name__=='__main__':unittest.main()
