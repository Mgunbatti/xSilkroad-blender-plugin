# SPDX-License-Identifier: GPL-3.0-or-later
import unreal as u,json,traceback,math,re,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent.parent
source=root/'SourceAssets'
m=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
texture_index=json.loads((source/'texture_index.json').read_text(encoding='utf-8'))
report={'rotation_checks':0,'skipped_effects':m.get('skipped_effects',[]),'status':'importing','engine':u.SystemLibrary.get_engine_version(),'errors':[],'assets':{},'actors':0}
def checkpoint():(root/'ImportReport.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

def placement_rotation(yaw_deg):
    if not math.isfinite(yaw_deg):raise ValueError('Non-finite placement yaw')
    return u.Rotator(pitch=0.0,yaw=yaw_deg,roll=0.0)

def verify_placement_rotation(actor,yaw_deg):
    actual=actor.get_actor_rotation()
    delta=abs((actual.yaw-yaw_deg+180.0)%360.0-180.0)
    if not all(math.isfinite(v) for v in (actual.pitch,actual.yaw,actual.roll)) or abs(actual.pitch)>.001 or abs(actual.roll)>.001 or delta>.001:
        raise RuntimeError('Placement rotation mismatch: '+actor.get_actor_label()+' / '+str(actual))

tools=u.AssetToolsHelpers.get_asset_tools();sub=u.get_editor_subsystem(u.EditorAssetSubsystem)
def import_fbx(name,folder,materials=True):
    if sub.does_asset_exist(folder+'/'+name):return sub.load_asset(folder+'/'+name)
    task=u.AssetImportTask();task.filename=str(source/(name+'.fbx'));task.destination_path=folder
    task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_as_skeletal=False
    opts.import_materials=materials;opts.import_textures=materials
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.generate_lightmap_u_vs=False
    data.auto_generate_collision=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options=opts;task.factory=u.FbxFactory();tools.import_asset_tasks([task])
    loaded=[sub.load_asset(p) for p in task.imported_object_paths]
    mesh=next((a for a in loaded if isinstance(a,u.StaticMesh)),None)
    if not mesh:raise RuntimeError('No imported static mesh: '+name)
    body=mesh.get_editor_property('body_setup')
    if body:body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    sub.save_loaded_asset(mesh);return mesh
checkpoint()
textures={}
for relative,meta in texture_index.items():
    key=meta['key']
    if key in textures:continue
    task=u.AssetImportTask();task.filename=str(root/relative);task.destination_path='/Game/Jangan/Textures'
    task.destination_name=key;task.automated=True;task.save=True;task.replace_existing=True
    tools.import_asset_tasks([task]);paths=task.imported_object_paths
    if not paths:raise RuntimeError('Texture import failed: '+relative)
    textures[key]=sub.load_asset(paths[0])
material_cache={}
def build_material(desc):
    relative=desc['textures'][-1] if desc['textures'] else None
    info=texture_index.get(relative)
    key='M_'+hashlib.sha1((desc['name']+'|'+str(info)).encode()).hexdigest()[:16]
    if key in material_cache:return material_cache[key]
    mat_path='/Game/Jangan/Materials/'+key
    mat=sub.load_asset(mat_path) if sub.does_asset_exist(mat_path) else tools.create_asset(key,'/Game/Jangan/Materials',u.Material,u.MaterialFactoryNew())
    lib=u.MaterialEditingLibrary
    lib.delete_all_material_expressions(mat)
    if info:
        node=lib.create_material_expression(mat,u.MaterialExpressionTextureSample,-450,0)
        node.set_editor_property('texture',textures[info['key']])
        lib.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        if info['alpha']:
            mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
            mat.set_editor_property('two_sided',True)
            lib.connect_material_property(node,'A',u.MaterialProperty.MP_OPACITY_MASK)
    else:
        node=lib.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-450,0)
        color=desc['color'];node.set_editor_property('constant',u.LinearColor(*color))
        lib.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(mat,u.MaterialExpressionConstant,-200,600);rough.set_editor_property('r',.85)
    lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat);sub.save_loaded_asset(mat);material_cache[key]=mat;return mat
calib=import_fbx('Calibration','/Game/Jangan/Validation',False)
b=calib.get_bounds();c=b.origin;e=b.box_extent
report['calibration']={'center_cm':[c.x,c.y,c.z],'extent_cm':[e.x,e.y,e.z]}
# Exported calibration geometry has Blender center (2,5,7) meters.
if abs(c.x-200)<2 and abs(c.y+500)<2:
    def position(p):return u.Vector(p[0],-p[1],p[2])
    def yaw(v):return -v
elif abs(c.x-500)<2 and abs(c.y-200)<2:
    def position(p):return u.Vector(p[1],p[0],p[2])
    def yaw(v):return -v
elif abs(c.x+500)<2 and abs(c.y-200)<2:
    def position(p):return u.Vector(-p[1],p[0],p[2])
    def yaw(v):return -v
else:
    raise RuntimeError('Unrecognized FBX coordinate conversion: '+str(report['calibration']))
checkpoint()
meshes={}
for name,record in list(m['assets'].items())+[(t['name'],t) for t in m['tiles']]:
    print('IMPORT',name,flush=True)
    try:
        mesh=import_fbx(name,'/Game/Jangan/'+('Terrain' if name.startswith('nv_') else 'Meshes'),False)
        meshes[name]=mesh;slots=mesh.get_editor_property('static_materials')
        slot_textures=[]
        for slot in slots:
            slot_name=str(slot.material_slot_name)
            normalized_slot=re.sub(r'[^a-zA-Z0-9_]','_',slot_name)
            candidates=[d for d in record['materials'] if normalized_slot.startswith(re.sub(r'[^a-zA-Z0-9_]','_',d['name']))]
            if not candidates:raise RuntimeError('Material slot not matched: '+slot_name+' / '+str(record['materials']))
            desc=max(candidates,key=lambda d:len(d['name']))
            mat=build_material(desc);mesh.set_material(len(slot_textures),mat)
            slot_textures.append(desc['textures'][-1] if desc['textures'] else '(untextured)')
        sub.save_loaded_asset(mesh)
        report['assets'][name]={'asset':mesh.get_path_name(),'slots':len(slots),'textures':sorted(set(slot_textures))}
    except Exception:report['errors'].append({'name':name,'error':traceback.format_exc()})
    checkpoint()
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if sub.does_asset_exist('/Game/Jangan/Maps/Jangan'):
    if not level.load_level('/Game/Jangan/Maps/Jangan'):raise RuntimeError('Map load failed')
else:
    if not level.new_level('/Game/Jangan/Maps/Jangan'):raise RuntimeError('Map creation failed')
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
actors.destroy_actors(list(actors.get_all_level_actors()))
for tile in m['tiles']:
    if tile['name'] not in meshes:continue
    a=actors.spawn_actor_from_class(u.StaticMeshActor,position(tile['position_cm']))
    a.static_mesh_component.set_static_mesh(meshes[tile['name']]);a.set_actor_label(tile['name'])
    a.set_folder_path('Terrain');report['actors']+=1
for p in m['placements']:
    mesh=meshes.get(p['asset'])
    if mesh is None:report['errors'].append({'missing_placement_asset':p['asset']});continue
    a=actors.spawn_actor_from_class(u.StaticMeshActor,position(p['position_cm']),placement_rotation(yaw(p['yaw_deg'])))
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_label(Path(p['source']).stem+'_'+p['region']+'_'+str(p['uid']))
    a.set_folder_path('City/'+p['region']);report['actors']+=1
    try:verify_placement_rotation(a,yaw(p['yaw_deg']))
    except Exception:
        report['errors'].append({'placement':a.get_actor_label(),'error':traceback.format_exc()});checkpoint();raise
    report['rotation_checks']+=1
sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,30000),u.Rotator(pitch=-40.0,yaw=-35.0,roll=0.0))
sun.set_actor_label('Jangan Sun');sun.light_component.set_editor_property('intensity',4.0)
sun.light_component.set_editor_property('mobility',u.ComponentMobility.MOVABLE)
sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,20000));sky.light_component.set_editor_property('mobility',u.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property('real_time_capture',True)
actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0))
actors.spawn_actor_from_class(u.PlayerStart,u.Vector(8606,6500,300))
level.set_level_viewport_camera_info(u.Vector(65000,-85000,65000),u.Rotator(pitch=-28.0,yaw=135.0,roll=0.0),'')
if not level.save_current_level():raise RuntimeError('Map save failed')
sub.save_directory('/Game/Jangan',only_if_is_dirty=False,recursive=True)
report['status']='complete' if not report['errors'] else 'incomplete';report['source_errors']=m['errors'];report['map']='/Game/Jangan/Maps/Jangan'
report['source_placements']=len(m['placements']);report['tiles']=len(m['tiles'])
checkpoint();print('JANGAN_IMPORT_COMPLETE',report['actors'],len(report['errors']),flush=True)
if report['errors']:raise RuntimeError('Import has unresolved errors; see ImportReport.json')
