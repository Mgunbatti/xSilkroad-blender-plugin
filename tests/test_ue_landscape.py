import importlib,sys,types,tempfile,unittest,json,struct
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge'
if 'silkroad_pk2_bridge' not in sys.modules:
    p=types.ModuleType('silkroad_pk2_bridge');p.__path__=[str(ROOT)];sys.modules[p.__name__]=p
ls=importlib.import_module('silkroad_pk2_bridge.ue_landscape')
class Session:
    def get(self,p):
        if p=='tile2d.ifo':return b'JMXV2DTI1001\n3\n0 0 "soil" "c_dust.ddj"\n1 0 "grass" "c_grass.ddj"\n2 0 "rock" "c_stone.ddj"\n','Map.pk2'
        return bytes.fromhex(Path(p).stem[3:]),'Map.pk2'
def grid(raw):
    rid=int.from_bytes(raw,'big');rx=rid&255;ry=rid>>8
    return {'heightmap_vertices':[[x*20,y*20,(((rx-168)*19200+x*200)*.001-((ry-97)*19200+y*200)*.002)/10] for y in range(97) for x in range(97)],'heightmap_faces':[{'tile_id':(x//12)%3} for y in range(96) for x in range(96)]}
class TestLandscape(unittest.TestCase):
    @patch.object(ls,'parse_nvm',side_effect=grid)
    def test_extended_layer_masks_preserve_dry_grass_and_normalize(self,_):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'export';names=('Soil','Grass','DryGrass','WetSoil','Rock','Paving')
            m=ls.export_landscape(Session(),p,'BANDIT',layer_classes={0:0,1:2,2:4},layer_names=names)
            self.assertEqual([x['name'] for x in m['layers']],list(names)+['Visibility'])
            masks=[np.fromfile(p/(name+'.r8'),dtype=np.uint8).astype(np.int16) for name in names]
            visible=np.fromfile(p/'Visibility.r8',dtype=np.uint8)==0
            self.assertTrue(np.all(np.sum(masks,axis=0)[visible]==255))
            self.assertGreater(np.max(masks[2]),0)
            self.assertEqual(np.max(masks[1]),0)

    def test_scope_rejects_foreign_and_duplicate_regions_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            for rs in [(0x0101,), (0x61a8,0x61a8), ()]:
                target=Path(d)/'export'
                with self.assertRaises(ValueError):ls.export_landscape(Session(),target,regions=rs)
                self.assertFalse(target.exists())
    @patch.object(ls,'parse_nvm',side_effect=grid)
    def test_geometry_orientation_quantization_and_normalized_layers(self,_):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'export';m=ls.export_landscape(Session(),p,'BANDIT')
            self.assertEqual(m['source_seam_difference_cm'],0);self.assertLess(m['quantization_error_cm'],.5)
            self.assertEqual(m['origin_cm'][:2],[-172800,76800]);self.assertEqual((m['width']-1)%63,0)
            h=np.fromfile(p/'Height.r16',dtype='<u2').reshape(m['height'],m['width']);z=(h.astype(float)-32768)*m['scale'][2]/128+m['origin_cm'][2]
            self.assertAlmostEqual(z[0,0],-172800*.001+76800*.002,delta=.5)
            self.assertAlmostEqual(z[192,192],-134400*.001+115200*.002,delta=.5)
            layers=sum(np.fromfile(p/(k+'.r8'),dtype=np.uint8).astype(int) for k in ('Soil','Grass','Rock'));self.assertTrue(np.all(layers==255))
            vis=np.fromfile(p/'Visibility.r8',dtype=np.uint8).reshape(h.shape);self.assertEqual(vis[96,96],0);self.assertEqual(vis[-1,-1],255)
            header=(p/'Height.png').read_bytes();self.assertEqual(header[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(header[24],16)
            self.assertTrue((p/'UnrealPlugin/SilkroadLandscapeBridge/SilkroadLandscapeBridge.uplugin').is_file())
            with self.assertRaises(FileExistsError):ls.export_landscape(Session(),p,'BANDIT')
    def test_bad_source_seam_is_not_silently_changed(self):
        def bad(raw):
            d=grid(raw)
            if int.from_bytes(raw,'big')==0x5ba0:d['heightmap_vertices'][0][2]+=1
            return d
        with tempfile.TemporaryDirectory() as d,patch.object(ls,'parse_nvm',side_effect=bad):
            p=Path(d)/'out'
            with self.assertRaisesRegex(ValueError,'seams disagree'):ls.export_landscape(Session(),p,'BANDIT')
            self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
