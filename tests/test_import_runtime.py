"""Behavioral operator contract tests, including false-success detection."""
import ast, io, tempfile, traceback, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from test_pk2_core import core
from silkroad_pk2_bridge.bridge_core import validate_asset, SIGNATURES

class Texts(dict):
    def new(self,name): self[name]=io.StringIO(); return self[name]

def item(kind,ident=1):
    return NS(name='test',type=kind,mode='OBJECT',as_pointer=lambda:ident,
              data=NS(vertices=[1,2,3],bones=[1]),select_set=lambda value:None)

class RuntimeContracts(unittest.TestCase):
    def run_import(self,ext,behavior):
        fake=NS(data=NS(objects=[],actions=[],texts=Texts()),
                ops=NS(object=NS(select_all=lambda **kw:None,mode_set=lambda **kw:None)))
        rig=item('ARMATURE') if ext=='.ban' else None
        context=NS(object=rig,view_layer=NS(objects=NS(active=rig),active_layer_collection=object()))
        reports=[]; calls=[]
        def load(*args):
            calls.append(args)
            if behavior=='raise': raise ValueError('bad binary payload')
            if behavior=='false': return False
            if behavior=='empty': return True
            if ext=='.ban': fake.data.actions.append(item('ACTION'))
            else: fake.data.objects.append(item('ARMATURE' if ext=='.bsk' else 'MESH'))
            return True
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/('a'+ext); file.write_bytes(SIGNATURES[ext])
            operator=NS(directory=tmp,files=[NS(name=file.name)],LoadFile=load,
                        report=lambda level,message:reports.append(message),setting_material_filepath='')
            src=(Path(__file__).resolve().parents[1]/'silkroad_pk2_bridge/import_runtime.py').read_text()
            tree=ast.parse(src)
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_import')
            ns=dict(bpy=fake,Path=Path,io=io,datetime=datetime,timezone=timezone,
                    redirect_stdout=redirect_stdout,redirect_stderr=redirect_stderr,
                    traceback=traceback,validate_asset=validate_asset)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'runtime','exec'),ns)
            with redirect_stdout(io.StringIO()):
                result=ns['execute_import'](operator,context,ext)
        return result,reports,calls,fake.data.texts['Silkroad import '+ext.upper()].getvalue()

    def test_all_six_success_contracts_and_loadfile_signatures(self):
        for ext in SIGNATURES:
            with self.subTest(ext=ext):
                result,reports,calls,log=self.run_import(ext,'ok')
                self.assertEqual(result,{'FINISHED'})
                self.assertFalse(reports)
                self.assertEqual(len(calls[0]),3 if ext in ('.bms','.dof') else 2)
                self.assertIn('RESULT',log)

    def test_all_six_false_successes_are_cancelled(self):
        for ext in SIGNATURES:
            with self.subTest(ext=ext):
                result,reports,_,log=self.run_import(ext,'empty')
                self.assertEqual(result,{'CANCELLED'})
                self.assertIn('produced no',reports[0])
                self.assertIn('Traceback',log)

    def test_all_six_loadfile_false_is_reported(self):
        for ext in SIGNATURES:
            with self.subTest(ext=ext):
                result,reports,_,log=self.run_import(ext,'false')
                self.assertEqual(result,{'CANCELLED'})
                self.assertIn('LoadFile failed',reports[0])

    def test_all_six_keep_real_error_detail(self):
        for ext in SIGNATURES:
            with self.subTest(ext=ext):
                result,reports,_,log=self.run_import(ext,'raise')
                self.assertEqual(result,{'CANCELLED'})
                self.assertIn('bad binary payload',reports[0])
                self.assertIn('ValueError',log)
