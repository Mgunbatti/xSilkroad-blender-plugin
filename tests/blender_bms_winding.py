# SPDX-License-Identifier: GPL-3.0-or-later
import bpy,sys,struct,json,math
from pathlib import Path
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base))
import silkroad_pk2_bridge as addon
addon.register()
args=sys.argv[sys.argv.index('--')+1:];source=Path(args[0]);output=Path(args[1]);output.mkdir(parents=True,exist_ok=True)
b=source.read_bytes();vo,go,fo=struct.unpack_from('<III',b,12);count=struct.unpack_from('<I',b,vo)[0]
flag=struct.unpack_from('<I',b,64)[0];stride=44+(8 if flag&0x400 else 0)+(40 if flag&0x800 else 0)
rawnormals=[struct.unpack_from('<fff',b,vo+4+i*stride+12) for i in range(count)]
result=bpy.ops.silkroad_import.jmxvbms_0110(directory=str(source.parent),files=[{'name':source.name}],setting_bounding_box=False,setting_navmesh=False)
assert result=={'FINISHED'}
obj=next(o for o in bpy.context.selected_objects if o.type=='MESH');mesh=obj.data
positive=negative=0
for f in mesh.polygons:
 n=[sum(rawnormals[i][j] for i in f.vertices) for j in (0,2,1)]
 dot=sum(f.normal[j]*n[j] for j in range(3))
 if dot>1e-6:positive+=1
 elif dot< -1e-6:negative+=1
assert positive>0 and negative==0,(positive,negative)
out=output/'roundtrip';out.mkdir(exist_ok=True)
result=bpy.ops.silkroad_export.jmxvbms_0110(directory=str(out),setting_overwrite=True,setting_navmesh=False)
assert result=={'FINISHED'}
new=(out/(obj.name+'.bms')).read_bytes();newfo=struct.unpack_from('<I',new,20)[0];fc=struct.unpack_from('<I',b,fo)[0]
assert struct.unpack_from('<I',new,newfo)[0]==fc
assert b[fo+4:fo+4+fc*6]==new[newfo+4:newfo+4+fc*6],'Source face indices changed'
(output/'bms_winding_real_result.json').write_text(json.dumps({'passed':True,'mesh':source.name,'source_normal_alignment':positive,'inverted_faces':negative,'source_faces_roundtrip_preserved':True},indent=2))
print('REAL_BMS_WINDING_ROUNDTRIP_PASSED',positive,flush=True)
