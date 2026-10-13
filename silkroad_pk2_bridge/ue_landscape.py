# SPDX-License-Identifier: GPL-3.0-or-later
"""Jangan-only loss-bounded Landscape height/paint export; no PK2 writes."""
from pathlib import Path
import json, math, re, shutil, struct, zlib
import numpy as np
from .map_data import parse_nvm
from .ue_project import JANGAN_REGIONS

from .jangan_scope import JANGAN_ALLOWED
BANDIT_REGIONS = (0x5b9f, 0x5ba0, 0x5c9f, 0x5ca0)
SCOPES = {'CITY': JANGAN_REGIONS, 'JANGAN': tuple(sorted(JANGAN_ALLOWED)), 'BANDIT': BANDIT_REGIONS}

def png(path, array, depth=8):
    a=np.asarray(array);h,w=a.shape
    dtype='>u2' if depth==16 else 'u1'
    rows=a.astype(dtype).tobytes();stride=w*(depth//8)
    raw=b''.join(b'\0'+rows[y*stride:(y+1)*stride] for y in range(h))
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,depth,0,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def tile_classes(session):
    raw,_=session.get('tile2d.ifo')
    if not raw:raise ValueError('Map.pk2 tile2d.ifo is required for landscape layers')
    lines=raw.decode('cp1252').splitlines()
    if not lines or lines[0].strip()!='JMXV2DTI1001':raise ValueError('Invalid tile2d.ifo')
    result={}
    for line in lines[2:]:
        m=re.match(r'\s*(\d+)\s+\S+\s+"([^"]*)"\s+"([^"]*)"',line)
        if m:
            name=m[3].lower();result[int(m[1])]=1 if 'grass' in name else 2 if any(k in name for k in ('stone','rock','cliff')) else 0
    if len(result)!=int(lines[1]):raise ValueError('tile2d.ifo count mismatch')
    return result

def smooth(a):
    for axis in (0,1):
        pads=[(0,0)]*a.ndim;pads[axis]=(2,2);p=np.pad(a,pads,mode='edge');n=a.shape[axis]
        a=sum(weight*np.take(p,range(i,i+n),axis=axis) for i,weight in enumerate((1,4,6,4,1)))/16
    return a

def export_landscape(session, destination, scope='CITY', regions=None, layer_classes=None, layer_names=None):
    regions=tuple(regions if regions is not None else SCOPES[scope])
    if not regions or len(set(regions))!=len(regions) or any(r not in JANGAN_ALLOWED for r in regions):
        raise ValueError('This feature exports Jangan regions only')
    dest=Path(destination).resolve()
    if dest.exists():raise FileExistsError('Choose a new Landscape output folder')
    classes=layer_classes if layer_classes is not None else tile_classes(session)
    layer_names=tuple(layer_names or ('Soil','Grass','Rock'))
    if not layer_names or any(not re.fullmatch(r'[A-Za-z]+',n) for n in layer_names) or any(v<0 or v>=len(layer_names) for v in classes.values()):
        raise ValueError('Invalid Landscape layer profile')
    rx0=min(r&255 for r in regions);rx1=max(r&255 for r in regions);ry0=min(r>>8 for r in regions);ry1=max(r>>8 for r in regions)
    nx=(rx1-rx0+1)*96;ny=(ry1-ry0+1)*96
    sums=np.zeros((ny+1,nx+1),np.float64);counts=np.zeros_like(sums);low=np.full_like(sums,np.inf);high=np.full_like(sums,-np.inf)
    faces=np.full((ny,nx),-1,np.int8);provenance=[]
    for rid in regions:
        entry=f'navmesh/nv_{rid:04x}.nvm';raw,archive=session.get(entry)
        if raw is None:raise FileNotFoundError(entry+' required for selected Jangan scope')
        data=parse_nvm(raw);h=np.array([v[2]*10 for v in data['heightmap_vertices']],np.float64).reshape(97,97)
        if not np.isfinite(h).all():raise ValueError('Non-finite terrain heights: '+entry)
        x=((rid&255)-rx0)*96;y=(ry1-(rid>>8))*96;sl=np.s_[y:y+97,x:x+97];h=h[::-1]
        sums[sl]+=h;counts[sl]+=1;low[sl]=np.minimum(low[sl],h);high[sl]=np.maximum(high[sl],h)
        ids=[f['tile_id'] for f in data['heightmap_faces']]
        unknown=set(ids)-classes.keys()
        if unknown:raise ValueError('Unmapped terrain tile IDs: '+str(sorted(unknown)))
        faces[y:y+96,x:x+96]=np.array([classes[i] for i in ids],np.int8).reshape(96,96)[::-1]
        provenance.append({'region':rid,'entry':entry,'archive':Path(archive).name if archive else None})
    valid=counts>0;h=np.divide(sums,counts,out=np.zeros_like(sums),where=valid)
    seam=float(np.max((high-low)[counts>1])) if np.any(counts>1) else 0
    if seam>2:raise ValueError(f'Source region seams disagree by {seam:.3f} cm; refusing an inaccurate Landscape')
    lo=float(h[valid].min());hi=float(h[valid].max());center=(lo+hi)/2;zs=max(1,math.ceil((hi-lo)/511.98));h[~valid]=center
    encoded=np.rint((h-center)*128/zs+32768).astype('<u2')
    error=float(np.max(np.abs((encoded.astype(float)-32768)*zs/128+center-h)[valid]))
    # Padding, never resampling: every original 2m sample keeps its world location.
    quads=63;px=math.ceil(nx/quads)*quads;py=math.ceil(ny/quads)*quads
    heights=np.pad(encoded,((0,py-ny),(0,px-nx)),mode='edge')
    weights=[]
    for kind in range(len(layer_names)):
        f=(faces==kind).astype(np.float32);v=np.zeros_like(h,dtype=np.float32)
        v[:-1,:-1]+=f;v[1:,:-1]+=f;v[:-1,1:]+=f;v[1:,1:]+=f;weights.append(smooth(v))
    w=np.stack(weights,axis=2);total=w.sum(axis=2,keepdims=True);w=np.divide(w,total,out=np.zeros_like(w),where=total>0)
    w=np.rint(w*255).astype(np.int16);yy,xx=np.indices(w.shape[:2]);largest=np.argmax(w,axis=2);w[yy,xx,largest]+=255-w.sum(axis=2);w=np.clip(w,0,255).astype(np.uint8)
    # Hole corners exclude missing regions and padded quads, including collision.
    visible=np.zeros_like(h,dtype=bool)
    for rid in regions:
        x=((rid&255)-rx0)*96;y=(ry1-(rid>>8))*96;visible[y:y+97,x:x+97]=True
    visibility=np.pad(np.where(visible,0,255).astype(np.uint8),((0,py-ny),(0,px-nx)),constant_values=255)
    dest.mkdir(parents=True);heights.tofile(dest/'Height.r16');png(dest/'Height.png',heights,16)
    layers=[]
    for i,name in enumerate(layer_names):
        layer=np.pad(w[:,:,i],((0,py-ny),(0,px-nx)),mode='edge');layer.tofile(dest/(name+'.r8'));png(dest/(name+'.png'),layer);layers.append({'name':name,'file':name+'.r8'})
    visibility.tofile(dest/'Visibility.r8');png(dest/'Visibility.png',visibility);layers.append({'name':'Visibility','file':'Visibility.r8'})
    manifest={'format':'silkroad-jangan-landscape-1','scope':'Jangan','selection':scope,'regions':list(regions),'width':px+1,'height':py+1,'source_width':nx+1,'source_height':ny+1,'subsection_quads':63,'height_file':'Height.r16','layers':layers,'origin_cm':[(rx0-168)*19200,-((ry1+1-97)*19200),center],'scale':[200,200,zs],'quantization_error_cm':error,'source_seam_difference_cm':seam,'seam_average_error_cm':seam/2,'sources':provenance,'orientation':'row 0 is minimum Unreal world Y','padding':'height edge padded; absent and padded cells hidden with Visibility layer','requires_unreal':'5.8','plugin_version':'2.6.0'}
    (dest/'Landscape.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    native=Path(__file__).with_name('landscape_bridge');shutil.copytree(native,dest/'UnrealPlugin/SilkroadLandscapeBridge')
    shutil.copy2(Path(__file__).with_name('ue_landscape_import.py'),dest/'ImportLandscape.py')
    (dest/'README.txt').write_text('Jangan Landscape export (Unreal 5.8).\nCopy UnrealPlugin/SilkroadLandscapeBridge into your project Plugins folder. Build the editor plugin with the Unreal C++ toolchain, then enable it.\nRun ImportLandscape.py in Unreal Python with SILKROAD_LANDSCAPE_MANIFEST set to Landscape.json. It imports into the CURRENT level and never removes existing objects. Use an empty or duplicated level.\nThe raw 16-bit Height.r16 and 16-bit Height.png also support manual Landscape import. Resolution, exact location, scale, layer masks and measurement errors are recorded in Landscape.json.\nUnreal padding is hidden by Visibility. Layer names: Soil, Grass, Rock. Replace material texture parameters with your preferred ground textures. Original PK2 archives are not modified. This feature supports Jangan only.\n',encoding='utf-8')
    return manifest
