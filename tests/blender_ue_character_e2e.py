# SPDX-License-Identifier: GPL-3.0-or-later
"""Run in Blender with -- GAME_DIRECTORY EXISTING_UPROJECT [BSR_ENTRY]."""
import bpy,sys,json
from pathlib import Path
base=Path(__file__).resolve().parents[1];sys.path[:0]=[str(base/'engine'),str(base)]
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import ArchiveSession
args=sys.argv[sys.argv.index('--')+1:];game=Path(args[0]);project=Path(args[1]);entry=args[2] if len(args)>2 else 'res/mob/europe/wolf.bsr'
addon.register();addon._session=ArchiveSession(game/'Data.pk2')
assert bpy.ops.silkroad_editor.export_ue_character.get_rna_type()
scene=bpy.context.scene;original=list(scene.objects);fps=scene.render.fps
mat=bpy.data.materials.new('wolf');mat.diffuse_color=(.2,.3,.4,1);color=tuple(mat.diffuse_color)
props=scene.silkroad_editor;row=props.entries.add();row.path=entry;row.name=Path(entry).name;row.is_folder=False;props.selected_index=0
project_bytes=project.read_bytes()
result=bpy.ops.silkroad_editor.export_ue_character(filepath=str(project),run_unreal=True)
assert result=={'FINISHED'},props.message
assert bpy.context.scene==scene and list(scene.objects)==original and scene.render.fps==fps
assert mat.name=='wolf' and tuple(mat.diffuse_color)==color
assert project.read_bytes()==project_bytes
assert not any(s.name.startswith('Silkroad_UE_Character') for s in bpy.data.scenes)
bundle=max((project.parent/'SourceAssets/SilkroadCharacters').iterdir(),key=lambda p:p.stat().st_mtime)
report=json.loads((bundle/'ImportReport.json').read_text());manifest=json.loads((bundle/'manifest.json').read_text())
assert report['status']=='complete' and not report['errors'] and report['skeleton']
assert len(report['animations'])==len(manifest['animations']) and len(report['animations'])>0
evidence={'passed':True,'operator':'silkroad_editor.export_ue_character','source':entry,'animations':len(report['animations']),'bones':manifest['bones'],'vertices':manifest['vertices'],'original_scene_preserved':True,'original_material_preserved':True,'target_project_descriptor_preserved':True,'engine':report['engine'],'bundle':bundle.name}
(project.parent/'CharacterTestReport.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print('CHARACTER_REAL_OPERATOR_PASSED',evidence,flush=True)
