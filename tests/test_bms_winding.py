import ast,types,struct,unittest
from pathlib import Path
class TestBMSWinding(unittest.TestCase):
 def test_reader_reverses_reflected_face_and_writer_restores_it(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge/JellyBMS.py').read_text(encoding='utf-8'))
  load=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Import_JMXVBMS_0110' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='LoadData')
  append=next(n for n in ast.walk(load) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='faces' and n.value.func.attr=='append')
  ns={'faces':[],'a':0,'b':1,'c':2};exec(compile(ast.Module(body=[append],type_ignores=[]),'reader','exec'),ns)
  self.assertEqual(ns['faces'],[[0,2,1]])
  write=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Export_JMXVBMS_0110' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='SaveData')
  call=next(n for n in ast.walk(write) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='WriteUShort' and isinstance(n.value.args[0],ast.Subscript) and isinstance(n.value.args[0].value,ast.Attribute) and n.value.args[0].value.attr=='vertices')
  out=[];ns.update(f=types.SimpleNamespace(vertices=ns['faces'][0]),bw=types.SimpleNamespace(WriteUShort=out.append))
  for i in range(3):ns['i']=i;exec(compile(ast.Module(body=[call],type_ignores=[]),'writer','exec'),ns)
  self.assertEqual(out,[0,1,2])
