"""Synthetic dependency extraction regressions; no copyrighted assets."""
import unittest, struct, tempfile, shutil
from pathlib import Path
from unittest.mock import patch
from test_pk2_core import core, bsr, bms, bmt, u32, st
from silkroad_pk2_bridge.map_data import parse_nvm, parse_dof
from silkroad_pk2_bridge.asset_binary import BinaryReader

def nvm():
    return (b'JMXVNVM 1000'+b'\0'*2+u32(0)*4+
            (u32(0)+struct.pack('<HH',0,7))*9216+b'\0'*(9409*4))

def dof(resource='res/block.bsr'):
    block=st(resource)+st('room')+b'\0'*4+b'\0'*16+u32(0)+b'\0'*24
    block+=b'\0'*20+b'\0'*2+u32(0)+b'\0'*8+u32(0)*2+u32(0)+b'\0'*4+u32(0)
    return b'JMXVDOF 0101'+u32(16)+u32(1)+block

class Session:
    def __init__(self,files): self.files=files
    def get(self,path): return self.files.get(path),Path('Data.pk2')

class MapPipeline(unittest.TestCase):
    def prepare(self,files,path,**kw):
        prepared=core.prepare_asset(Session(files),path,**kw)
        self.addCleanup(shutil.rmtree,prepared.workspace)
        return prepared

    def test_nvm_actual_layout_and_map_roots(self):
        data=parse_nvm(nvm())
        self.assertEqual(len(data['heightmap_vertices']),9409)
        files={'navmesh/nv_1234.nvm':nvm(),'tile2d.ifo':b'JMXV2DTI1001\n1\n7 0 "grass" "grass.ddj"\n',
               'tile2d/grass.ddj':b'DDJ'+bytes(50)}
        p=self.prepare(files,'navmesh/nv_1234.nvm')
        self.assertNotEqual(p.data_root,p.map_root)
        self.assertTrue((p.map_root/'tile2d/grass.ddj').is_file())

    def test_nvm_absent_map_keeps_geometry_and_reports(self):
        p=self.prepare({'a.nvm':nvm()},'a.nvm')
        self.assertIn('tile2d.ifo',p.missing_optional)

    def test_dof_actual_layout_recursive_bsr_mesh_material_texture(self):
        self.assertEqual(parse_dof(dof())['blocks'][0]['path'],'res/block.bsr')
        files={'a.dof':dof(),'res/block.bsr':bsr(),'prim/mesh/monster.bms':bms('body'),
               'prim/mtrl/monster.bmt':bmt(),'prim/texture/monster.ddj':b'dds'}
        p=self.prepare(files,'a.dof')
        self.assertTrue((p.data_root/'prim/mesh/monster.bms').is_file())
        self.assertTrue((p.data_root/'prim/texture/monster.ddj').is_file())

    def test_missing_dof_resource_fails(self):
        with self.assertRaises(FileNotFoundError): self.prepare({'a.dof':dof()},'a.dof')

    def test_dof_traversal_rejected(self):
        with self.assertRaises(core.InvalidAsset): self.prepare({'a.dof':dof('../bad.bsr')},'a.dof')

    def test_nvm_object_resource_chain(self):
        files={'a.nvm':nvm(),'navmesh/object.ifo':b'JMXVOBJI1000\n1\n3 0 "res/block.bsr"\n',
               'res/block.bsr':bsr(),'prim/mesh/monster.bms':bms('body')}
        with patch.object(core,'parse_nvm',return_value={'heightmap_faces':[],'objects':[{'asset_id':3}]}):
            p=self.prepare(files,'a.nvm',include_objects=True)
        self.assertTrue((p.data_root/'res/block.bsr').is_file())

    def test_nvm_missing_object_id_reports(self):
        files={'a.nvm':nvm(),'navmesh/object.ifo':b'JMXVOBJI1000\n0\n'}
        with patch.object(core,'parse_nvm',return_value={'heightmap_faces':[],'objects':[{'asset_id':3}]}):
            with self.assertRaisesRegex(core.InvalidAsset,'asset IDs'): self.prepare(files,'a.nvm',include_objects=True)

    def test_truncated_and_out_of_bounds_binary_rejected(self):
        for parse,data in ((parse_nvm,nvm()),(parse_dof,dof())):
            with self.assertRaises(ValueError): parse(data[:15])
        with self.assertRaises(ValueError): BinaryReader(b'123').SeekRead(-1)
        with self.assertRaises(ValueError): BinaryReader(b'123').ReadBytes(4)

if __name__=='__main__': unittest.main()
