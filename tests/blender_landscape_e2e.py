import bpy,sys,json
from pathlib import Path
base=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:];sys.path[:0]=[str(base),args[0]]
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import ArchiveSession
addon.register();assert addon.bl_info['version']==(2,6,0);assert not bpy.ops.silkroad_editor.export_jangan_landscape.poll()
props=bpy.context.scene.silkroad_editor;sentinel=bpy.context.object;state=(bpy.context.scene.as_pointer(),sentinel.as_pointer(),len(bpy.data.objects),len(bpy.data.materials));props.language='TR'
addon._session=ArchiveSession('C:/Users/slyva/Downloads/Silkroad/Holigan/Data.pk2');assert bpy.ops.silkroad_editor.export_jangan_landscape.poll()
result=bpy.ops.silkroad_editor.export_jangan_landscape(filepath=args[1],landscape_scope='BANDIT');assert result=={'FINISHED'},props.message
assert state==(bpy.context.scene.as_pointer(),sentinel.as_pointer(),len(bpy.data.objects),len(bpy.data.materials));assert not props.ue_transfer_running;assert props.language=='TR'
m=json.loads(Path(args[1]).with_suffix('').joinpath('Landscape.json').read_text());assert m['regions']==[0x5b9f,0x5ba0,0x5c9f,0x5ca0];assert m['quantization_error_cm']<.1
addon._session.close();addon._session=None;addon.unregister();print('BLENDER_JANGAN_LANDSCAPE_E2E_PASSED',flush=True)
