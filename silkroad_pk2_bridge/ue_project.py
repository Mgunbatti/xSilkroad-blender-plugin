# SPDX-License-Identifier: GPL-3.0-or-later
"""Source map selection and portable Unreal project metadata."""
from pathlib import Path
import hashlib
import json
import math
import re
import struct
from .asset_binary import BinaryReader
from .map_data import parse_nvm
from .jangan_scope import JANGAN_FULL_REGIONS

JANGAN_REGIONS = tuple((y << 8) | x for y in range(96, 100) for x in range(166, 170))


def region_position_cm(region, local=(0, 0, 0)):
    x, y = region & 255, region >> 8
    if len(local) != 3 or not all(math.isfinite(v) for v in local):
        raise ValueError('Invalid source map position')
    return [(x - 168) * 19200 + local[0] * 10,
            (y - 97) * 19200 + local[1] * 10, local[2] * 10]


def object_table(contents):
    lines = contents.decode('cp1252').splitlines()
    if len(lines) < 2 or lines[0].strip() != 'JMXVOBJI1000':
        raise ValueError('Invalid object.ifo signature')
    result = {}
    for line in lines[2:]:
        match = re.match(r'^\s*(\d+)\s+\S+\s+"([^"]+)"', line)
        if match:
            result[int(match[1])] = match[2].replace('\\', '/')
    if len(result) != int(lines[1]):
        raise ValueError('object.ifo count mismatch')
    return result


class StaticEffectOnly(ValueError):
    pass


def resource_paths(session, path, stack=()):
    path = path.replace('\\', '/').lower()
    if path in stack or len(stack) > 32:
        raise ValueError('Compound resource cycle: ' + path)
    raw, _ = session.get(path)
    if raw is None:raise FileNotFoundError('Missing map resource: '+path)
    if raw.startswith(b'JMXVEFF '):raise StaticEffectOnly('Particle resource: '+path)
    if raw[:12] == b'JMXVRES 0109':
        return [path]
    if raw[:12] != b'JMXVCPD 0101':
        raise ValueError('Unsupported map resource: ' + path)
    reader = BinaryReader(raw)
    reader.SeekRead(16)
    reader.SeekRead(reader.ReadUInt())
    count = reader.ReadUInt()
    return [p for _ in range(count) for p in resource_paths(
        session, reader.ReadAscii(reader.ReadUInt()), stack + (path,))]


def parse_map_objects(contents):
    if contents[:12] != b'JMXVMAPO1001':
        raise ValueError('Invalid .o2 signature')
    offset, records = 12, {}
    for block in range(36):
        for lod in range(4):
            if offset + 2 > len(contents):raise ValueError('Truncated .o2 count')
            count = struct.unpack_from('<H', contents, offset)[0];offset += 2
            if offset + count * 30 > len(contents):raise ValueError('Truncated .o2 entries')
            for _ in range(count):
                aid,x,z,y,kind,yaw,uid,unused,big,struct_flag,rid = struct.unpack_from('<IfffhfHhBBH', contents, offset)
                offset += 30
                if not all(math.isfinite(v) for v in (x,y,z,yaw)):raise ValueError('Non-finite .o2 placement')
                record = {'asset_id':aid,'local_position':[x,y,z],'yaw':yaw,'local_uid':uid,'RID':rid}
                key = (rid,uid,aid)
                if key in records and records[key] != record:raise ValueError('Conflicting .o2 duplicate')
                records[key] = record
    if offset != len(contents):raise ValueError('Unparsed .o2 trailing bytes')
    return list(records.values())


def build_manifest(session, regions=JANGAN_FULL_REGIONS):
    regions = tuple(regions)
    if not regions or len(set(regions)) != len(regions) or any(r not in JANGAN_FULL_REGIONS for r in regions):
        raise ValueError('Choose regions inside the fixed Jangan boundary')
    raw, _ = session.get('navmesh/object.ifo')
    table = object_table(raw)
    visual_raw, _ = session.get('object.ifo')
    visual_table = object_table(visual_raw) if visual_raw else None
    manifest = {'status': 'exporting', 'tiles': [], 'assets': {}, 'placements': [],
                'errors': [], 'repairs': [], 'skipped_effects': [], 'placement_sources': {}, 'unit': '1 source unit = 10 UE centimeters',
                'plugin_version': '2.7.0', 'data_processing': 'Silkroad PK2 Editor',
                'scope': 'Jangan and surrounding outdoor regions', 'regions': list(regions)}
    cache = {}
    seen = set()
    for region in regions:
        entry = f'navmesh/nv_{region:04x}.nvm'
        raw, _ = session.get(entry)
        if raw is None:
            raise FileNotFoundError('Required Jangan terrain missing: ' + entry)
        data = parse_nvm(raw)
        name = Path(entry).stem
        manifest['tiles'].append({'name': name, 'entry': entry, 'fbx': name + '.fbx',
                                 'position_cm': region_position_cm(region),
                                 'vertices': len(data['heightmap_vertices'])})
        visual_entry = f'{region >> 8}/{region & 255}.o2'
        visual, _ = session.get(visual_entry)
        objects = parse_map_objects(visual) if visual is not None else data['objects']
        active_table = visual_table if visual is not None else table
        if active_table is None:raise ValueError('Map object.ifo required for .o2')
        manifest['placement_sources'][name] = visual_entry if visual is not None else entry
        for obj in objects:
            if obj['RID'] != region:
                continue
            identity = (region, obj['local_uid'], obj['asset_id'])
            if identity in seen:
                raise ValueError(f'Duplicate map object: {identity}')
            seen.add(identity)
            path = active_table.get(obj['asset_id'])
            if not path:
                raise ValueError(f'object.ifo missing asset ID: {obj["asset_id"]}')
            if path not in cache:
                try:cache[path] = resource_paths(session, path)
                except StaticEffectOnly as exc:
                    cache[path] = []
            if not cache[path]:
                manifest['skipped_effects'].append({'source':path,'region':name,'uid':obj['local_uid'],'reason':'Particle effect has no static BSR mesh'})
            for resource in cache[path]:
                key = 'A_' + hashlib.sha1(resource.encode()).hexdigest()[:12]
                manifest['assets'][key] = {'source': resource, 'fbx': key + '.fbx'}
                manifest['placements'].append({'asset': key, 'region': name,
                    'uid': obj['local_uid'], 'source': resource,
                    'position_cm': region_position_cm(region, obj['local_position']),
                    'yaw_deg': math.degrees(obj['yaw'])})
    return manifest


def initialize_project(filepath, engine_version='5.8'):
    path = Path(filepath).expanduser().resolve()
    if path.suffix.lower() != '.uproject':
        raise ValueError('Choose a .uproject filename')
    name = path.stem
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,47}', name):
        raise ValueError('Project name must start with a letter and use letters, numbers or underscores')
    if len(name) > 20:
        raise ValueError('Unreal project name must be 20 characters or fewer')
    root = path.parent / name
    if root.exists() and any(root.iterdir()):
        raise ValueError('Choose a new project folder; destination is not empty: ' + str(root))
    (root / 'SourceAssets').mkdir(parents=True, exist_ok=True)
    (root / 'Config').mkdir(exist_ok=True)
    (root / 'Tools').mkdir(exist_ok=True)
    project = root / (name + '.uproject')
    project.write_text(json.dumps({'FileVersion': 3, 'EngineAssociation': engine_version,
        'Description': 'Jangan map imported with Silkroad PK2 Editor',
        'Plugins': [{'Name': 'PythonScriptPlugin', 'Enabled': True},
                    {'Name': 'EditorScriptingUtilities', 'Enabled': True}]}, indent=2), encoding='utf-8')
    (root / 'Config' / 'DefaultEngine.ini').write_text(
        '[ConsoleVariables]\nInterchange.FeatureFlags.Import.FBX=0\n\n'
        '[/Script/EngineSettings.GameMapsSettings]\n'
        'EditorStartupMap=/Game/Jangan/Maps/Jangan\nGameDefaultMap=/Game/Jangan/Maps/Jangan\n\n'
        '[/Script/Engine.RendererSettings]\nr.AllowStaticLighting=False\n'
        'r.DefaultFeature.AutoExposure=False\nr.DefaultFeature.MotionBlur=False\n'
        'r.DynamicGlobalIlluminationMethod=1\nr.ReflectionMethod=1\n', encoding='utf-8')
    template = Path(__file__).parent / 'ue_import_template.py'
    (root / 'Tools' / 'import_jangan.py').write_bytes(template.read_bytes())
    return project
