import importlib,sys,types,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge'
if 'silkroad_pk2_bridge' not in sys.modules:
    pkg=types.ModuleType('silkroad_pk2_bridge');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
job=importlib.import_module('silkroad_pk2_bridge.ue_blender')
land=importlib.import_module('silkroad_pk2_bridge.ue_landscape_project')

class TestLandscapeProject(unittest.TestCase):
    def test_dry_grass_and_soil_families_are_preserved(self):
        self.assertEqual(land.ground_layer('c_grass.ddj',1,(.12,.3,.07)),'Grass')
        self.assertEqual(land.ground_layer('c_grass_hmfld_04.ddj',1,(.4,.3,.09)),'DryGrass')
        self.assertEqual(land.ground_layer('c_grass_fld_04.ddj',1,(.306,.304,.088)),'Grass')
        self.assertEqual(land.ground_layer('c_dust_swmp.ddj',0,(.1,.09,.08)),'WetSoil')
        self.assertEqual(land.ground_layer('c_dust_hmfld.ddj',0,(.3,.2,.1)),'Soil')
        self.assertEqual(land.ground_layer('c_marble_jang.ddj',0,(.2,.2,.2)),'Paving')

    def test_soil_uses_dirt_instead_of_city_pavement(self):
        selected=land.choose_ground_tile(0,{51:1000,3:100,7:2000},{51:0,3:0,7:1},
                                       {51:'c_marble_jang.ddj',3:'c_dust.ddj',7:'c_grass.ddj'})
        self.assertEqual(selected,3)
    def test_two_functions_export_different_ground(self):
        bpy=types.SimpleNamespace(data=types.SimpleNamespace(scenes=types.SimpleNamespace(new=lambda name:object())))
        addon=types.SimpleNamespace(_session=object())
        def manifest(session):return {'tiles':[{'name':'nv_61a8'},{'name':'nv_62a8'}],
                                      'assets':{'Tree':{}},'placements':[],'errors':[]}
        with tempfile.TemporaryDirectory() as d,patch.object(job,'build_manifest',side_effect=manifest):
            tile=job.UEProjectJob(bpy,addon,Path(d)/'Tiles.uproject',run_unreal=False)
            landscape=land.UELandscapeProjectJob(bpy,addon,Path(d)/'Landscape.uproject',run_unreal=False)
            self.assertEqual([kind for kind,_,_ in tile.queue],['terrain','terrain','asset'])
            self.assertEqual([kind for kind,_,_ in landscape.queue],['asset'])
            self.assertEqual(tile.manifest['terrain_mode'],'TILE')
            self.assertEqual(landscape.manifest['terrain_mode'],'LANDSCAPE')

    def test_binary_compatibility_requires_build_id_and_real_dll(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);editor=root/'Engine/Win64/UnrealEditor-Cmd.exe';editor.parent.mkdir(parents=True)
            (editor.parent/'UnrealEditor.modules').write_text(json.dumps({'BuildId':'engine'}))
            plugin=root/'Plugin';binary=plugin/'Binaries/Win64';binary.mkdir(parents=True)
            (binary/'UnrealEditor.modules').write_text(json.dumps({'BuildId':'other','Modules':{'SilkroadLandscapeBridge':'bridge.dll'}}))
            (binary/'bridge.dll').write_bytes(b'test')
            self.assertFalse(land.bridge_matches(editor,plugin))
            (binary/'UnrealEditor.modules').write_text(json.dumps({'BuildId':'engine','Modules':{'SilkroadLandscapeBridge':'bridge.dll'}}))
            self.assertTrue(land.bridge_matches(editor,plugin))
            (binary/'bridge.dll').unlink()
            self.assertFalse(land.bridge_matches(editor,plugin))
