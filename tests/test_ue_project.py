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
    def get(self,path):return self.files[path],'Data.pk2'

class TestUEProject(unittest.TestCase):
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
