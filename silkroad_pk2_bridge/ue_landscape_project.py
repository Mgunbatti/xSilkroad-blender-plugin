# SPDX-License-Identifier: GPL-3.0-or-later
"""Full environment project with native Landscape instead of tile mesh terrain."""
from pathlib import Path
from collections import Counter
import json,re,shutil,subprocess,tempfile
from .ue_blender import UEProjectJob
from .ue_landscape import export_landscape,tile_classes
from .map_data import parse_nvm
from .fbx_texture_export import isolated_png_scene,_write_png

GROUND_LAYERS=('Soil','Grass','DryGrass','WetSoil','Rock','Paving')

def ground_layer(path, base_class, color):
    name=path.lower();r,g,b=color
    if any(k in name for k in ('marble','paving','brick','cobble')):return 'Paving'
    if any(k in name for k in ('straw','drygrass','dry_grass','deadgrass','yellowgrass')):return 'DryGrass'
    if base_class==1:
        return 'DryGrass' if g>.01 and r>=g*1.08 and b<g*.85 else 'Grass'
    if base_class==2:return 'Rock'
    if any(k in name for k in ('swmp','swamp','marsh','wet')):return 'WetSoil'
    return 'Soil'

def ground_profile(bpy,session,regions):
    import numpy as np
    base=tile_classes(session);counts=Counter();paths={};colors={};classes={}
    for rid in regions:
        raw,_=session.get(f'navmesh/nv_{rid:04x}.nvm')
        counts.update(f['tile_id'] for f in parse_nvm(raw)['heightmap_faces'])
    raw,_=session.get('tile2d.ifo')
    for line in raw.decode('cp1252').splitlines()[2:]:
        match=re.match(r'\s*(\d+)\s+\S+\s+"([^"]*)"\s+"([^"]*)"',line)
        if match:paths[int(match[1])]='tile2d/'+match[3].replace('\\','/')
    with tempfile.TemporaryDirectory(prefix='Silkroad_GroundProfile_') as temp:
        for tile in counts:
            entry=paths[tile];data,_=session.get(entry)
            if not data:raise FileNotFoundError(entry)
            dds=data if data.startswith(b'DDS ') else data[20:]
            if not dds.startswith(b'DDS '):raise ValueError('Invalid ground DDJ: '+entry)
            file=Path(temp)/'texture.dds';file.write_bytes(dds)
            image=bpy.data.images.load(str(file),check_existing=False)
            try:
                pixels=np.array(image.pixels[:],dtype=np.float32).reshape(-1,4)[::137]
                visible=pixels[pixels[:,3]>.2]
                color=tuple(float(v) for v in (visible if len(visible) else pixels)[:,:3].mean(axis=0))
            finally:bpy.data.images.remove(image)
            colors[tile]=color;classes[tile]=GROUND_LAYERS.index(ground_layer(entry,base[tile],color))
    names=tuple(n for i,n in enumerate(GROUND_LAYERS) if i in classes.values())
    remap={i:names.index(n) for i,n in enumerate(GROUND_LAYERS) if n in names}
    return {'classes':{tile:remap[kind] for tile,kind in classes.items()},'names':names,
            'counts':counts,'paths':paths,'colors':colors}


def bridge_matches(editor, plugin):
    engine_file=Path(editor).parent/'UnrealEditor.modules'
    plugin_file=Path(plugin)/'Binaries/Win64/UnrealEditor.modules'
    if not engine_file.is_file() or not plugin_file.is_file():return False
    engine=json.loads(engine_file.read_text());module=json.loads(plugin_file.read_text())
    return (engine.get('BuildId')==module.get('BuildId') and
            (plugin_file.parent/module.get('Modules',{}).get('SilkroadLandscapeBridge','missing')).is_file())


def choose_ground_tile(kind, counts, classes, paths):
    candidates=[i for i in counts if classes[i]==kind]
    if kind==0:
        natural=[i for i in candidates if any(word in paths[i].lower() for word in
                                            ('dust','dirt','mud','sand','soil','ground','road'))]
        if natural:candidates=natural
    if not candidates:raise ValueError('No source texture found for ground layer '+str(kind))
    return max(candidates,key=lambda i:(counts[i],-i))


def export_ground_textures(bpy, session, manifest, folder, profile=None):
    if profile is not None:
        classes=profile['classes'];counts=profile['counts'];paths=profile['paths'];names=profile['names']
    else:
        raise ValueError('A source ground profile is required')
    folder.mkdir();sources={}
    with tempfile.TemporaryDirectory(prefix='Silkroad_Ground_') as temp,isolated_png_scene(bpy) as scene:
        for kind,name in enumerate(names):
            candidates=[i for i in counts if classes[i]==kind]
            if name=='DryGrass':
                # Prefer the straw/yellow source variant, rather than a green-leaved soil variant.
                tile=max(candidates,key=lambda i:(profile['colors'][i][0]-profile['colors'][i][1],counts[i],-i))
            else:tile=max(candidates,key=lambda i:(counts[i],-i))
            entry=paths[tile]
            data,_=session.get(entry);dds=data if data.startswith(b'DDS ') else data[20:]
            file=Path(temp)/(name+'.dds');file.write_bytes(dds);image=bpy.data.images.load(str(file),check_existing=False)
            try:_write_png(image,folder/(name+'_BaseColor.png'),scene)
            finally:bpy.data.images.remove(image)
            sources[name]={'tile_id':tile,'source':entry,'file':name+'_BaseColor.png','average_rgb':profile['colors'][tile]}
    (folder/'SourceTextures.json').write_text(json.dumps(sources,indent=2))
class UELandscapeProjectJob(UEProjectJob):
    def __init__(self,bpy,addon,filepath,editor='',run_unreal=True):
        super().__init__(bpy,addon,filepath,editor,run_unreal,terrain_mode='LANDSCAPE')
        self.landscape_prepared=False;self.bridge_process=None;self.bridge_log=None;self.bridge_package=None

    def prepare_landscape(self):
        bundle=self.source/'Landscape'
        profile=ground_profile(self.bpy,self.addon._session,self.manifest['regions'])
        landscape=export_landscape(self.addon._session,bundle,'JANGAN',layer_classes=profile['classes'],layer_names=profile['names'])
        export_ground_textures(self.bpy,self.addon._session,landscape,bundle/'Textures',profile)
        (bundle/'GroundProfile.json').write_text(json.dumps({'layer_names':profile['names'],
            'tiles':{str(t):{'layer':profile['names'][k],'source':profile['paths'][t],'average_rgb':profile['colors'][t],
                            'source_cells':profile['counts'][t]} for t,k in profile['classes'].items()}},indent=2))
        plugin=self.root/'Plugins/SilkroadLandscapeBridge'
        shutil.copytree(Path(__file__).with_name('landscape_bridge'),plugin)
        descriptor=json.loads(self.project.read_text())
        descriptor['Plugins'].append({'Name':'SilkroadLandscapeBridge','Enabled':True})
        self.project.write_text(json.dumps(descriptor,indent=2))
        self.manifest['landscape_manifest']='SourceAssets/Landscape/Landscape.json'
        self.manifest['plugin_version']='2.7.0';self.save_manifest();self.landscape_prepared=True
        if self.editor and not bridge_matches(self.editor,plugin):
            shutil.rmtree(plugin/'Binaries',ignore_errors=True)
            uat=self.editor.parents[2]/'Build/BatchFiles/RunUAT.bat'
            if not uat.is_file():raise FileNotFoundError('Unreal build tools missing: '+str(uat))
            self.bridge_package=Path(tempfile.mkdtemp(prefix='Silkroad_BridgeBuild_'))/'Package'
            self.bridge_log=(self.root/'LandscapeBridgeBuild.log').open('w',encoding='utf-8')
            args=[str(uat),'BuildPlugin','-Plugin='+str(plugin/'SilkroadLandscapeBridge.uplugin'),
                  '-Package='+str(self.bridge_package),'-TargetPlatforms=Win64','-NoUBA','-NoP4','-Unattended']
            self.bridge_process=subprocess.Popen(args,stdout=self.bridge_log,stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def step(self,context):
        if not self.landscape_prepared:
            self.prepare_landscape();return False,'Full Jangan Landscape height, layers and textures prepared'
        if self.bridge_process:
            if self.bridge_process.poll() is None:return False,'Building the Landscape editor bridge; see LandscapeBridgeBuild.log'
            self.bridge_log.close();self.bridge_log=None
            if self.bridge_process.returncode!=0:raise RuntimeError('Landscape bridge build failed. Install Unreal C++ build tools; see LandscapeBridgeBuild.log')
            plugin=self.root/'Plugins/SilkroadLandscapeBridge'
            shutil.copytree(self.bridge_package/'Binaries',plugin/'Binaries',dirs_exist_ok=True)
            if not bridge_matches(self.editor,plugin):raise RuntimeError('Built Landscape bridge does not match the selected Unreal editor')
            self.bridge_process=None
        return super().step(context)

    def close(self,cancel=False):
        if cancel and self.bridge_process and self.bridge_process.poll() is None:self.bridge_process.terminate()
        if self.bridge_log:self.bridge_log.close();self.bridge_log=None
        if self.bridge_package:shutil.rmtree(self.bridge_package.parent,ignore_errors=True)
        super().close(cancel)
