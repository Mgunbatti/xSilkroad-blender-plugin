# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected BSR export into an existing Unreal project's separate asset folder."""
from pathlib import Path
import json,math,re,subprocess,os,hashlib
from .ue_blender import UEProjectJob,find_unreal_editor
from .fbx_texture_export import export_fbx_with_textures


def character_name(entry):
    if Path(entry).suffix.lower()!='.bsr':raise ValueError('Select a BSR mob or character in the PK2 list')
    stem=re.sub(r'[^A-Za-z0-9_]', '_',Path(entry).stem).strip('_') or 'Character'
    return 'C_'+stem[:48]+'_'+hashlib.sha1(entry.lower().encode()).hexdigest()[:8]


def validate_target(filepath):
    project=Path(filepath).expanduser().resolve()
    if project.suffix.lower()!='.uproject' or not project.is_file():raise ValueError('Choose an existing Unreal .uproject file')
    info=json.loads(project.read_text(encoding='utf-8-sig'))
    plugins={p['Name']:p.get('Enabled',False) for p in info.get('Plugins',[])}
    if not plugins.get('PythonScriptPlugin'):raise ValueError('Enable Python Editor Script Plugin in the target Unreal project first')
    return project


def project_is_open(project):
    if os.name!='nt':return False
    command="[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'\" | Select-Object -ExpandProperty CommandLine | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError('Could not check whether the Unreal project is open; disable automatic import')
    lines=json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(lines,str):lines=[lines]
    name=str(project).replace('\\','/').casefold()
    return any(name in (line or '').replace('\\','/').casefold() or project.name.casefold() in (line or '').casefold() for line in lines)


class UECharacterJob(UEProjectJob):
    def __init__(self,bpy,addon,filepath,entry,editor='',run_unreal=True):
        if addon._session is None:raise ValueError('Open the game PK2 archive first')
        key=character_name(entry);project=validate_target(filepath)
        self.bpy,self.addon=bpy,addon;self.project=project;self.entry=entry
        self.editor=Path(editor or find_unreal_editor()) if run_unreal else None
        if self.editor:
            if self.editor.name=='UnrealEditor.exe':self.editor=self.editor.with_name('UnrealEditor-Cmd.exe')
            if not self.editor.is_file() or self.editor.name!='UnrealEditor-Cmd.exe':raise ValueError('Choose the installed UnrealEditor-Cmd.exe')
            if project_is_open(project):raise ValueError('Close the target Unreal project before automatic import, or disable automatic import and run the prepared script in its editor')
        bundle=project.parent/'SourceAssets'/'SilkroadCharacters'/key;number=1
        while bundle.exists():
            number+=1;bundle=bundle.with_name(key+'_'+str(number))
        self.root=bundle;self.source=bundle;self.source.mkdir(parents=True)
        self.manifest={'status':'exporting','source':entry,'name':bundle.name,'content_path':'/Game/Silkroad/Characters/'+bundle.name,'mesh':'Mesh.fbx','animations':[],'materials':[],'errors':[],'repairs':[]}
        self.scene=bpy.data.scenes.new('Silkroad_UE_Character');self.process=None;self.log=None;self.closed=False;self.workspaces=[];self.index=0
        self.save_manifest()

    def save_manifest(self):
        (self.source/'manifest.json').write_text(json.dumps(self.manifest,indent=2),encoding='utf-8')

    def export_sources(self,context):
        bpy=self.bpy
        with self.stage(context):
            props=self.scene.silkroad_editor;props.archive=str(self.addon._session.primary);props.load_animations=True;props.load_map_objects=False
            row=props.entries.add();row.path=self.entry;row.name=Path(self.entry).name;row.is_folder=False
            old_count=len(self.addon._last_workspaces)
            try:
                with self.addon._viewport_operator_context(context):result=bpy.ops.silkroad_editor.import_selected(entry_index=0)
            finally:self.workspaces.extend(self.addon._last_workspaces[old_count:])
            if result!={'FINISHED'}:raise RuntimeError(props.message)
            objects=list(self.scene.objects);rigs=[o for o in objects if o.type=='ARMATURE'];meshes=[o for o in objects if o.type=='MESH']
            if len(rigs)!=1 or not meshes:raise ValueError('BSR must contain meshes and exactly one skeleton')
            rig=rigs[0];ad=rig.animation_data
            clips=[];seen=set()
            for track in ad.nla_tracks if ad else ():
                track.mute=True
                for strip in track.strips:
                    if strip.action and strip.action.as_pointer() not in seen:
                        seen.add(strip.action.as_pointer());clips.append((strip.action,getattr(strip,'action_slot',None),track.name))
            if ad:ad.action=None
            for obj in objects:
                if not obj.parent:obj.scale=tuple(v*.1 for v in obj.scale);obj.location*=.1
                obj.select_set(obj.type in {'ARMATURE','MESH'})
            context.view_layer.objects.active=rig
            for mesh in meshes:
                if not any(mod.type=='ARMATURE' and mod.object==rig for mod in mesh.modifiers):raise ValueError('Mesh is not bound to the imported skeleton: '+mesh.name)
                if any(not all(math.isfinite(v) for v in vertex.co) for vertex in mesh.data.vertices):raise ValueError('Non-finite mesh geometry: '+mesh.name)
                repaired=0
                for layer in mesh.data.uv_layers:
                    for loop in layer.data:
                        if not all(math.isfinite(v) for v in loop.uv):loop.uv=(0,0);repaired+=1
                if repaired:self.manifest['repairs'].append({'mesh':mesh.name,'invalid_uv_loops':repaired})
            rig.data.pose_position='REST';context.view_layer.update()
            descriptors=self.describe(meshes)
            with self.addon._viewport_operator_context(context):summary=export_fbx_with_textures(bpy,self.source/'Mesh.fbx',objects,animation=False)
            if summary.missing:raise ValueError('Missing character textures: '+str(summary.missing))
            for desc in descriptors:
                desc['textures']=[str((summary.texture_folder/p).relative_to(self.source)) for p in desc['textures']]
                desc['alpha']=False
                if desc['textures']:
                    image=bpy.data.images.load(str(self.source/desc['textures'][-1]),check_existing=False)
                    alpha=image.pixels[3::4];desc['alpha']=bool(alpha) and min(alpha)<.5 and max(alpha)>.5
                    bpy.data.images.remove(image)
            self.manifest['materials']=descriptors;self.manifest['bones']=len(rig.data.bones);self.manifest['vertices']=sum(len(o.data.vertices) for o in meshes)
            self.manifest['bone_names']=[b.name for b in rig.data.bones]
            rig.data.pose_position='POSE'
            for number,(action,slot,label) in enumerate(clips,1):
                ad.action=action
                if slot is not None:ad.action_slot=slot
                elif hasattr(action,'slots') and len(action.slots)==1:ad.action_slot=action.slots[0]
                start,end=action.frame_range
                if not math.isfinite(start) or not math.isfinite(end) or end<=start:raise ValueError('Empty animation: '+label)
                fps=action.get('silkroad_fps',self.scene.render.fps)
                if not isinstance(fps,(int,float)) or fps<1 or fps>240:raise ValueError('Invalid animation FPS: '+label)
                self.scene.render.fps=int(fps);self.scene.render.fps_base=1.0;self.scene.frame_start=math.floor(start);self.scene.frame_end=math.ceil(end);self.scene.frame_set(self.scene.frame_start)
                name='A_'+str(number).zfill(3)+'_'+re.sub(r'[^A-Za-z0-9_]','_',label)[:60]
                with self.addon._viewport_operator_context(context):export_fbx_with_textures(bpy,self.source/(name+'.fbx'),objects,textures=False,animation=True)
                self.manifest['animations'].append({'name':name,'label':label,'fbx':name+'.fbx','fps':int(fps),'start':math.floor(start),'end':math.ceil(end),'cyclic':bool(action.use_cyclic)})
                print('[Silkroad character]',number,'/',len(clips),label,flush=True)
            self.manifest['status']='exported';self.save_manifest()
        template=Path(__file__).with_name('ue_character_import_template.py');(self.source/'import_character.py').write_bytes(template.read_bytes())
        if self.editor:
            self.log=(self.root/'UnrealImport.log').open('w',encoding='utf-8')
            self.process=subprocess.Popen([str(self.editor),str(self.project),'-run=pythonscript','-script='+str(self.source/'import_character.py'),'-unattended','-NullRHI','-nosplash','-stdout','-FullStdOutLogOutput'],stdout=self.log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def step(self,context):
        if not self.index:
            self.export_sources(context);self.index=1
            if not self.editor:return True,'Character sources ready: '+str(self.source)
        if self.process.poll() is None:return False,'Unreal skeletal import is running; see UnrealImport.log'
        path=self.root/'ImportReport.json';report=json.loads(path.read_text()) if path.exists() else {}
        if self.process.returncode!=0 or report.get('status')!='complete' or len(report.get('animations',[]))!=len(self.manifest['animations']):raise RuntimeError('Character import failed; see UnrealImport.log and ImportReport.json')
        return True,'UE character ready: '+self.manifest['content_path']
