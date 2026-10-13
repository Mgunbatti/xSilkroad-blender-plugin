"""Run: blender --background --factory-startup --python this.py -- GAME_DIR OUTPUT_DIR UE_CMD ENGINE_DIR."""
import bpy,sys,json
from pathlib import Path
base=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:]
game,dest,editor=map(Path,args[:3]);sys.path[:0]=[str(base),str(Path(args[3]) if len(args)>3 else base/'engine')]
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import ArchiveSession
addon.register();addon._session=ArchiveSession(game/'Data.pk2')
before={k:len(getattr(bpy.data,k)) for k in ('scenes','objects','meshes','materials','images','actions')}
result=bpy.ops.silkroad_editor.export_ue_landscape_project(filepath=str(dest/'JanganLandscape.uproject'),unreal_editor=str(editor),run_unreal=True)
assert result=={'FINISHED'},bpy.context.scene.silkroad_editor.message
root=dest/'JanganLandscape';m=json.loads((root/'SourceAssets/manifest.json').read_text());r=json.loads((root/'ImportReport.json').read_text())
assert m['terrain_mode']==r['terrain_mode']=='LANDSCAPE' and len(m['tiles'])==174
assert r['status']=='complete' and not r['errors'] and r['actors']==len(m['placements'])+1
assert not list((root/'SourceAssets').glob('nv_*.fbx'))
assert {'DryGrass','Soil','WetSoil','Paving'}<=set(r['landscape']['validation']['allocated_layers'])
assert r['landscape']['validation']['all_hit'] and r['landscape']['validation']['padding_collision_removed']
assert before=={k:len(getattr(bpy.data,k)) for k in before}
print('LANDSCAPE_PROJECT_E2E_PASSED',flush=True);addon._session.close()
