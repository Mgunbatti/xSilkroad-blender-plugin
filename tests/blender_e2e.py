"""Opt-in Blender 5.2 integration test against user's read-only PK2 archives.

blender --background --factory-startup --python tests/blender_e2e.py -- GAME_DIR
Game assets/exports stay in work/ and are never shipped with source packages.
"""
from pathlib import Path
import sys, json, traceback, shutil, struct
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base)); sys.path.insert(0,str(base/'engine'))
import bpy
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import ArchiveSession, prepare_asset
from silkroad_pk2_bridge.bridge_core import parse_bsr
from silkroad_pk2_bridge.map_data import parse_dof, parse_nvm

game=Path(sys.argv[sys.argv.index('--')+1])
output=base/'real_test_output'; output.mkdir(exist_ok=True)
records=[]
addon.register()
props=bpy.context.scene.silkroad_editor
props.archive=str(game/'Data.pk2')
print('Opening real archives',flush=True)
addon._session=ArchiveSession(props.archive)
print('Archives ready',addon._session.errors,flush=True)
samples=json.loads((base/'real_assets.json').read_text())
# Choose one self-contained animated character resource and derive matching rig/BAN.
character=None
stream=addon._session.streams[addon._session.primary]
for f in stream.iter_files():
    path=f.get_full_path().replace('\\','/')
    if path.lower().startswith('res/mob/') and path.lower().endswith('.bsr'):
        try:
            p=output/'candidate.bsr'; p.write_bytes(f.get_content()); refs=parse_bsr(p)
            if refs.skeleton and refs.animations and refs.meshes:
                character=(path,refs); break
        except Exception:
            continue
if character:
    samples['.bsr']=[character[0]]
    samples['.bms']=[character[1].meshes[0]]
    samples['.bsk']=[character[1].skeleton]
    samples['.ban']=[character[1].animations[0]]
# Select populated maps/dungeons so the object toggle is actually exercised.
for f in stream.iter_files():
    path=f.get_full_path().replace('\\','/')
    if path.lower().endswith('.nvm'):
        content=f.get_content()
        if len(content)<14 or struct.unpack_from('<H',content,12)[0]==0: continue
        try:
            data=parse_nvm(content)
        except Exception as exc:
            print('SAMPLE_SELECTION_WARNING',path,str(exc),flush=True)
            continue
        if any(o['RID']==int(Path(path).stem[-4:],16) for o in data['objects']):
            samples['.nvm']=[path]; break
for f in stream.iter_files():
    path=f.get_full_path().replace('\\','/')
    if path.lower().endswith('.dof'):
        data=parse_dof(f.get_content())
        if any(b['objects'] for b in data['blocks']):
            samples['.dof']=[path]; break

def clear():
    if bpy.context.object and bpy.context.object.mode!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)

def run(ext,entry,objects=False,animations=False):
    if ext!='.ban': clear()
    props.entries.clear(); row=props.entries.add(); row.name=Path(entry).name; row.path=entry; row.is_folder=False
    props.selected_index=0; props.load_animations=animations; props.load_map_objects=objects
    record=dict(format=ext,entry=entry,objects_enabled=objects,animations_enabled=animations)
    before_actions=len(bpy.data.actions)
    try:
        area=next(a for a in bpy.context.window.screen.areas if a.type=='VIEW_3D')
        region=next(r for r in area.regions if r.type=='UI')
        with bpy.context.temp_override(area=area,region=region):
            result=bpy.ops.silkroad_editor.import_selected(entry_index=0)
        record.update(result=sorted(result),objects=len(bpy.data.objects),
                      vertices=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),
                      bones=sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE'),
                      actions=len(bpy.data.actions),images=len(bpy.data.images),status=props.message)
        record['actions_added']=len(bpy.data.actions)-before_actions
        if result!={'FINISHED'}: raise RuntimeError(str(result))
        if ext=='.nvm':
            terrain=next(o for o in bpy.data.objects if o.name.endswith('.NavMesh'))
            if not any(any(uv.uv) for uv in terrain.data.uv_layers.active.data):
                raise RuntimeError('Terrain UV coordinates were not populated')
        if ext in ('.ban','.bsr'):
            from bpy_extras import anim_utils
            rigs=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.animation_data]
            keys=0
            for rig in rigs:
                for track in rig.animation_data.nla_tracks:
                    for strip in track.strips:
                        bag=anim_utils.action_get_channelbag_for_slot(strip.action,strip.action_slot)
                        if bag: keys+=sum(len(c.keyframe_points) for c in bag.fcurves)
            record['keyframes']=keys
            if animations or ext=='.ban':
                if not keys: raise RuntimeError('No NLA keyframes bound to rig')
        record['passed']=True
    except Exception:
        record.update(passed=False,error=traceback.format_exc())
    records.append(record)
    print('E2E',json.dumps(record),flush=True)
    (output/'results.json').write_text(json.dumps(records,indent=2))

for ext in ('.bms','.bsk','.ban','.bsr','.nvm','.dof'):
    run(ext,samples[ext][0],animations=(ext=='.bsr'))
    if ext=='.bsr' and records[-1]['passed']:
        try:
            from silkroad_pk2_bridge.fbx_texture_export import export_fbx_with_textures
            objs=list(bpy.context.scene.objects)
            with addon._viewport_operator_context(bpy.context):
                bpy.ops.object.select_all(action='DESELECT')
                for obj in objs: obj.select_set(True)
                bpy.context.view_layer.objects.active=objs[0]
                summary=export_fbx_with_textures(bpy,output/'real_character.fbx',objs)
            records.append(dict(format='FBX+PNG',passed=True,converted=summary.converted,missing=summary.missing))
            clear()
            bpy.ops.import_scene.fbx(filepath=str(summary.fbx))
            pngs=[i for i in bpy.data.images if i.filepath.lower().endswith('.png')]
            if not pngs or not all(i.has_data for i in pngs): raise RuntimeError('FBX PNG roundtrip failed')
            if not any(o.type=='ARMATURE' for o in bpy.data.objects): raise RuntimeError('FBX rig roundtrip failed')
            records.append(dict(format='FBX roundtrip',passed=True,pngs=len(pngs),objects=len(bpy.data.objects)))
        except Exception:
            records.append(dict(format='FBX+PNG',passed=False,error=traceback.format_exc()))
run('.nvm',samples['.nvm'][0],objects=True)
run('.dof',samples['.dof'][0],objects=True)
for text in bpy.data.texts:
    if text.name.startswith('Silkroad'): (output/(text.name.replace('.','_')+'.txt')).write_text(text.as_string())
(output/'results.json').write_text(json.dumps(records,indent=2))
addon._close_session(); addon.unregister()
print('REAL_E2E_COMPLETE',flush=True)
if not all(r['passed'] for r in records): raise RuntimeError('Some real integration tests failed; see results.json')
