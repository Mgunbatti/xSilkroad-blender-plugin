# SPDX-License-Identifier: GPL-3.0-or-later
import unreal as u,json,re,traceback,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
m=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
folder=m['content_path']
if not re.fullmatch(r'/Game/Silkroad/Characters/[A-Za-z0-9_]+',folder):raise ValueError('Invalid character destination')
sub=u.get_editor_subsystem(u.EditorAssetSubsystem);tools=u.AssetToolsHelpers.get_asset_tools()
report={'status':'importing','errors':[],'animations':[],'source':m['source'],'engine':u.SystemLibrary.get_engine_version()}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
interchange=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
def checkpoint():(root/'ImportReport.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def task(filename,path,name,options=None):
    t=u.AssetImportTask();t.filename=str(root/filename);t.destination_path=path;t.destination_name=name;t.automated=True;t.save=True;t.replace_existing=False
    if options:t.options=options;t.factory=u.FbxFactory()
    tools.import_asset_tasks([t]);loaded=[sub.load_asset(p) for p in t.imported_object_paths]
    if not loaded:raise RuntimeError('Import produced no assets: '+filename)
    return loaded
try:
    checkpoint()
    if sub.does_directory_exist(folder):raise ValueError('Character folder already exists; export to a new bundle instead of overwriting assets')
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=next((a for a in task(m['mesh'],folder,'SK_'+m['name'],options) if isinstance(a,u.SkeletalMesh)),None)
    if mesh is None:raise RuntimeError('No skeletal mesh imported')
    skeleton=mesh.get_editor_property('skeleton')
    if skeleton is None:raise RuntimeError('Skeletal mesh has no skeleton')
    textures={};materials={};slots=mesh.get_editor_property('materials')
    for index,slot in enumerate(slots):
        name=re.sub(r'[^A-Za-z0-9_]','_',str(slot.material_slot_name))
        candidates=[d for d in m['materials'] if name.startswith(re.sub(r'[^A-Za-z0-9_]','_',d['name']))]
        if not candidates:raise RuntimeError('Unmatched skeletal material slot: '+name)
        desc=max(candidates,key=lambda d:len(d['name']));key='M_'+hashlib.sha1(desc['name'].encode()).hexdigest()[:12]
        if key not in materials:
            mat=tools.create_asset(key,folder+'/Materials',u.Material,u.MaterialFactoryNew());lib=u.MaterialEditingLibrary
            if desc['textures']:
                path=desc['textures'][-1]
                if path not in textures:
                    texname='T_'+hashlib.sha1(path.encode()).hexdigest()[:12];tex=next((a for a in task(path,folder+'/Textures',texname) if isinstance(a,u.Texture2D)),None)
                    if not tex:raise RuntimeError('No imported texture: '+path)
                    textures[path]=tex
                node=lib.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,0);node.set_editor_property('texture',textures[path]);lib.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
                if desc.get('alpha'):
                    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);mat.set_editor_property('two_sided',True);lib.connect_material_property(node,'A',u.MaterialProperty.MP_OPACITY_MASK)
            else:
                node=lib.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-400,0);node.set_editor_property('constant',u.LinearColor(*desc['color']));lib.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
            rough=lib.create_material_expression(mat,u.MaterialExpressionConstant,-200,300);rough.set_editor_property('r',.8);lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
            lib.recompile_material(mat);sub.save_loaded_asset(mat);materials[key]=mat
        slot.material_interface=materials[key]
    mesh.set_editor_property('materials',slots)
    sub.save_loaded_asset(mesh);report['mesh']=mesh.get_path_name();report['skeleton']=skeleton.get_path_name();report['materials']=len(materials)
    for clip in m['animations']:
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data;data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',clip['fps'])
        anim=next((a for a in task(clip['fbx'],folder+'/Animations',clip['name'],options) if isinstance(a,u.AnimSequence)),None)
        if anim is None or anim.get_editor_property('skeleton')!=skeleton:raise RuntimeError('Missing animation or incompatible skeleton: '+clip['label'])
        tracks=u.AnimationLibrary.get_animation_track_names(anim);keys=anim.get_editor_property('number_of_sampled_keys')
        if not tracks or keys<2:raise RuntimeError('Animation has no sampled bone tracks: '+clip['label'])
        duration=anim.get_editor_property('sequence_length');expected=(clip['end']-clip['start'])/clip['fps']
        if duration<=0 or abs(duration-expected)>2/clip['fps']:raise RuntimeError('Animation duration mismatch: '+clip['label'])
        report['animations'].append({'asset':anim.get_path_name(),'label':clip['label'],'seconds':duration,'fps':clip['fps'],'sampled_keys':keys,'bone_tracks':len(tracks)});checkpoint()
    sub.save_directory(folder,only_if_is_dirty=False,recursive=True);report['status']='complete';checkpoint();print('CHARACTER_IMPORT_COMPLETE',report['mesh'],len(report['animations']),flush=True)
except Exception:
    report['status']='failed';report['errors'].append(traceback.format_exc());checkpoint();raise
finally:
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX '+str(int(interchange)))
