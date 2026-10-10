# SPDX-License-Identifier: GPL-3.0-or-later
"""Real transfer: blender --background --python this.py -- GAME_DIR OUTPUT_DIR UE_CMD ENGINE_DIR."""
import bpy,sys,json
from pathlib import Path
base=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
game,destination,editor=map(Path,args[:3])
sys.path[:0]=[str(Path(args[3]) if len(args)>3 else base/'engine'),str(base)]
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import ArchiveSession
addon.register()
scene=bpy.context.scene
sentinel=bpy.context.object
material=bpy.data.materials.new('CJ_pub03_al');material.diffuse_color=(.123,.234,.345,1)
sentinel.data.materials.append(material)
original=(scene.as_pointer(),sentinel.as_pointer(),material.name,tuple(material.diffuse_color),len(bpy.data.objects),len(bpy.data.materials))
props=scene.silkroad_editor;props.archive=str(game/'Data.pk2')
props.language='TR';props.search_query='sentinel';props.load_animations=True
addon._session=ArchiveSession(props.archive)
print('PLUGIN_FULL_TRANSFER_START',flush=True)
result=bpy.ops.silkroad_editor.export_ue_project(filepath=str(destination/'xSilkroadJangan_Plugin.uproject'),
    unreal_editor=str(editor),run_unreal=True)
after=(bpy.context.scene.as_pointer(),sentinel.as_pointer(),material.name,tuple(material.diffuse_color),len(bpy.data.objects),len(bpy.data.materials))
assert result=={'FINISHED'},str(result)
assert original==after,(original,after)
assert props.language=='TR' and props.search_query=='sentinel' and props.load_animations
assert not props.ue_transfer_running
assert not any(s.name=='Silkroad_UE_Transfer' for s in bpy.data.scenes)
root=destination/'xSilkroadJangan_Plugin'
report=json.loads((root/'ImportReport.json').read_text(encoding='utf-8'))
manifest=json.loads((root/'SourceAssets/manifest.json').read_text(encoding='utf-8'))
placements=len(manifest['placements']);tiles=len(manifest['tiles']);assets=len(manifest['assets'])+tiles
assert report['rotation_checks']==placements
assert report['status']=='complete' and report['actors']==placements+tiles and len(report['assets'])==assets
if all(path.endswith('.o2') for path in manifest.get('placement_sources',{}).values()):
    assert any('cj_pal_main_buil.bsr' in p['source'] for p in manifest['placements'])
    assert any('cj_jang_gate_dragon.bsr' in p['source'] for p in manifest['placements'])
(root/'PluginTestReport.json').write_text(json.dumps({'result':'passed','operator':'silkroad_editor.export_ue_project',
    'original_scene_preserved':original==after,'original_material_preserved':True,'panel_settings_preserved':True,
    'assets':assets,'placements':placements,'terrain_tiles':tiles,'ue_errors':report['errors'],'engine':report['engine']},indent=2),encoding='utf-8')
print('PLUGIN_FULL_TRANSFER_PASSED',flush=True)
