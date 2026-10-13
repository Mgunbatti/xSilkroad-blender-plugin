import importlib,sys,types,struct,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge'
if 'silkroad_pk2_bridge' not in sys.modules:
    package=types.ModuleType('silkroad_pk2_bridge');package.__path__=[str(ROOT)]
    sys.modules['silkroad_pk2_bridge']=package
ue=importlib.import_module('silkroad_pk2_bridge.ue_project')

class Session:
    def __init__(self,files):self.files=files
    def get(self,path):return self.files.get(path),'Data.pk2'

class TestUEProject(unittest.TestCase):
    def test_default_exports_full_jangan_boundary(self):
        files={'navmesh/object.ifo':b'JMXVOBJI1000\n0\n'}
        files.update({f'navmesh/nv_{r:04x}.nvm':b'terrain' for r in ue.JANGAN_FULL_REGIONS})
        with patch.object(ue,'parse_nvm',return_value={'objects':[],'heightmap_vertices':[]}):
            manifest=ue.build_manifest(Session(files))
        self.assertEqual(len(manifest['tiles']),174)
        self.assertEqual(manifest['regions'],list(ue.JANGAN_FULL_REGIONS))
        self.assertTrue(set(ue.JANGAN_REGIONS)<=set(manifest['regions']))
        self.assertIn(0x5b9f,manifest['regions'])
        self.assertIn(0x66ac,manifest['regions'])

    def test_full_scope_does_not_silently_skip_missing_terrain(self):
        with self.assertRaisesRegex(FileNotFoundError,'Required Jangan terrain missing'):
            ue.build_manifest(Session({'navmesh/object.ifo':b'JMXVOBJI1000\n0\n'}))

    def test_foreign_export_scope_rejected(self):
        with self.assertRaises(ValueError):ue.build_manifest(Session({}),[0x1234])

    def test_long_project_name_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'20 characters'):
                ue.initialize_project(Path(temp)/('J'*21+'.uproject'))
            self.assertEqual(list(Path(temp).iterdir()),[])

    def test_region_origin_and_units(self):
        self.assertEqual(ue.region_position_cm(0x61a8),( [0,0,0]))
        self.assertEqual(ue.region_position_cm(0x62a9,[12,34,56]),[19320,19540,560])
        self.assertEqual(len(ue.JANGAN_REGIONS),16)
    def test_nonfinite_placement_rejected(self):
        with self.assertRaises(ValueError):ue.region_position_cm(0x61a8,[0,float('nan'),0])
    def test_invalid_ifo_count_rejected(self):
        with self.assertRaises(ValueError):ue.object_table(b'JMXVOBJI1000\n2\n1 0 "res/a.bsr"\n')
    def test_compound_cycle_rejected(self):
        path=b'res/a.cpd';raw=b'JMXVCPD 0101'+struct.pack('<III',0,20,1)+struct.pack('<I',len(path))+path
        with self.assertRaises(ValueError):ue.resource_paths(Session({'res/a.cpd':raw}),'res/a.cpd')
    def test_foreign_region_records_not_duplicated(self):
        obj={'RID':0x61a8,'asset_id':1,'local_uid':7,'local_position':[10,20,30],'yaw':0}
        data={'objects':[obj,dict(obj,RID=0x61a7)],'heightmap_vertices':[0]*9409}
        files={'navmesh/object.ifo':b'JMXVOBJI1000\n1\n1 0 "res/a.bsr"\n',
               'navmesh/nv_61a8.nvm':b'', 'res/a.bsr':b'JMXVRES 0109'}
        with patch.object(ue,'parse_nvm',return_value=data):m=ue.build_manifest(Session(files),[0x61a8])
        self.assertEqual(len(m['placements']),1);self.assertEqual(len(m['assets']),1)
        self.assertEqual(m['placements'][0]['position_cm'],[100,200,300])
    def test_duplicate_uid_rejected(self):
        obj={'RID':0x61a8,'asset_id':1,'local_uid':7,'local_position':[0,0,0],'yaw':0}
        files={'navmesh/object.ifo':b'JMXVOBJI1000\n1\n1 0 "res/a.bsr"\n',
               'navmesh/nv_61a8.nvm':b'', 'res/a.bsr':b'JMXVRES 0109'}
        with patch.object(ue,'parse_nvm',return_value={'objects':[obj,obj],'heightmap_vertices':[]}),self.assertRaises(ValueError):
            ue.build_manifest(Session(files),[0x61a8])
    def test_existing_project_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);existing=root/'City';existing.mkdir();(existing/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):ue.initialize_project(root/'City.uproject')
            self.assertEqual((existing/'keep.txt').read_text(),'keep')
    def test_project_is_portable(self):
        with tempfile.TemporaryDirectory() as temp:
            project=ue.initialize_project(Path(temp)/'City.uproject')
            self.assertTrue(project.is_file())
            self.assertEqual(json.loads(project.read_text())['EngineAssociation'],'5.8')
            template=(project.parent/'Tools/import_jangan.py').read_text()
            self.assertNotIn('C:/Users/',template)
            self.assertIn('Path(__file__).resolve().parent.parent',template)
    def test_project_name_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):ue.initialize_project(Path(temp)/'Bad Name.uproject')

    def test_map_visual_objects_deduplicated(self):
        row=struct.pack('<IfffhfHhBBH',80,1,2,3,-1,.5,42,0,0,1,0x62a8)
        raw=b'JMXVMAPO1001'+struct.pack('<H',2)+row+row+b'\x00\x00'*143
        parsed=ue.parse_map_objects(raw)
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0]['local_position'],[1,3,2])
    def test_map_visual_truncation_rejected(self):
        with self.assertRaises(ValueError):ue.parse_map_objects(b'JMXVMAPO1001'+struct.pack('<H',1))
    def test_map_visual_placements_supersede_navigation(self):
        row=struct.pack('<IfffhfHhBBH',80,1,2,3,-1,.5,42,0,0,1,0x62a8)
        raw=b'JMXVMAPO1001'+struct.pack('<H',1)+row+b'\x00\x00'*143
        files={'navmesh/object.ifo':b'JMXVOBJI1000\n0\n','object.ifo':b'JMXVOBJI1000\n1\n80 0 "res/palace.bsr"\n',
               'navmesh/nv_62a8.nvm':b'', '98/168.o2':raw,'res/palace.bsr':b'JMXVRES 0109'}
        with patch.object(ue,'parse_nvm',return_value={'objects':[],'heightmap_vertices':[]}):m=ue.build_manifest(Session(files),[0x62a8])
        self.assertEqual(len(m['placements']),1)
        self.assertEqual(m['placements'][0]['source'],'res/palace.bsr')
        self.assertEqual(m['placement_sources']['nv_62a8'],'98/168.o2')

    def test_map_visual_conflicting_duplicate_rejected(self):
        a=struct.pack('<IfffhfHhBBH',80,1,2,3,-1,.5,42,0,0,1,0x62a8)
        b=struct.pack('<IfffhfHhBBH',80,9,2,3,-1,.5,42,0,0,1,0x62a8)
        with self.assertRaises(ValueError):ue.parse_map_objects(b'JMXVMAPO1001'+struct.pack('<H',2)+a+b+b'\x00\x00'*143)
    def test_map_visual_nonfinite_rejected(self):
        row=struct.pack('<IfffhfHhBBH',80,float('nan'),2,3,-1,.5,42,0,0,1,0x62a8)
        with self.assertRaises(ValueError):ue.parse_map_objects(b'JMXVMAPO1001'+struct.pack('<H',1)+row+b'\x00\x00'*143)
    def test_map_visual_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):ue.parse_map_objects(b'JMXVMAPO1001'+b'\x00\x00'*144+b'bad')
