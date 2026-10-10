"""Real bpy failure contracts for all six operators; uses synthetic bad files."""
from pathlib import Path
import sys, tempfile, json
base=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(base))
import bpy
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.bridge_core import SIGNATURES
addon.register()
routes={'.ban':'jmxvban_0102','.bms':'jmxvbms_0110','.bsk':'jmxvbsk_0110',
        '.bsr':'jmxvres_0109','.dof':'jmxvdof_0101','.nvm':'jmxvnvm_1000'}
results=[]
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for ext,name in routes.items():
        file=root/('broken'+ext); file.write_bytes(SIGNATURES[ext])
        before={o.as_pointer() for o in bpy.data.objects}
        try:
            with addon._viewport_operator_context(bpy.context):
                result=getattr(bpy.ops.silkroad_import,name)(directory=temp,files=[{'name':file.name}])
            assert result=={'CANCELLED'},(ext,result)
        except RuntimeError as exc:
            assert 'import' in str(exc).lower(),str(exc)
        assert before=={o.as_pointer() for o in bpy.data.objects},ext
        assert 'Traceback' in bpy.data.texts['Silkroad import '+ext.upper()].as_string(),ext
        results.append(dict(format=ext,passed=True,check='truncated signature-only file rejected and logged'))
        wrong=root/'wrong.txt'; wrong.write_bytes(SIGNATURES[ext])
        try:
            with addon._viewport_operator_context(bpy.context):
                result=getattr(bpy.ops.silkroad_import,name)(directory=temp,files=[{'name':wrong.name}])
            assert result=={'CANCELLED'}
        except RuntimeError: pass
        results.append(dict(format=ext,passed=True,check='wrong suffix rejected'))
out=base/'real_test_output'; out.mkdir(exist_ok=True)
(out/'failure_results.json').write_text(json.dumps(results,indent=2))
addon.unregister()
print('FAILURE_CONTRACTS_OK',len(results))
