import ast,math,types,unittest
from pathlib import Path
class TestUnrealRotation(unittest.TestCase):
 def setUp(self):
  path=Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge/ue_import_template.py'
  tree=ast.parse(path.read_text(encoding='utf-8'))
  functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('placement_rotation','verify_placement_rotation')]
  # UE 5.8 positional order is roll,pitch,yaw: the original call tipped buildings.
  def rotator(roll=0.0,pitch=0.0,yaw=0.0):return types.SimpleNamespace(roll=roll,pitch=pitch,yaw=yaw)
  self.ns={'u':types.SimpleNamespace(Rotator=rotator),'math':math}
  exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),self.ns)
 def actor(self,r):return types.SimpleNamespace(get_actor_rotation=lambda:r,get_actor_label=lambda:'building')
 def test_nonzero_yaw_stays_upright(self):
  for yaw in (90,-90,180,270,450,30.5545):
   r=self.ns['placement_rotation'](yaw)
   self.assertEqual((r.pitch,r.roll,r.yaw),(0,0,yaw))
   self.ns['verify_placement_rotation'](self.actor(r),yaw)
 def test_old_positional_rotation_rejected(self):
  old=self.ns['u'].Rotator(0,90,0)
  with self.assertRaises(RuntimeError):self.ns['verify_placement_rotation'](self.actor(old),90)
 def test_wrapped_yaw_accepted(self):
  self.ns['verify_placement_rotation'](self.actor(self.ns['placement_rotation'](-90)),270)
 def test_nonfinite_yaw_rejected(self):
  for yaw in (float('nan'),float('inf')):
   with self.assertRaises(ValueError):self.ns['placement_rotation'](yaw)
 def test_nonfinite_result_rejected(self):
  r=self.ns['placement_rotation'](0);r.roll=float('nan')
  with self.assertRaises(RuntimeError):self.ns['verify_placement_rotation'](self.actor(r),0)
