# SPDX-License-Identifier: GPL-3.0-or-later
"""Source map selection and portable Unreal project metadata."""
from pathlib import Path
import hashlib
import json
import math
import re
from .asset_binary import BinaryReader
from .map_data import parse_nvm

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


def resource_paths(session, path, stack=()):
    path = path.replace('\\', '/').lower()
    if path in stack or len(stack) > 32:
        raise ValueError('Compound resource cycle: ' + path)
    raw, _ = session.get(path)
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


def build_manifest(session, regions=JANGAN_REGIONS):
    raw, _ = session.get('navmesh/object.ifo')
    table = object_table(raw)
    manifest = {'status': 'exporting', 'tiles': [], 'assets': {}, 'placements': [],
                'errors': [], 'repairs': [], 'unit': '1 source unit = 10 UE centimeters',
                'plugin_version': '2.4.0', 'data_processing': 'Silkroad PK2 Editor'}
    cache = {}
    seen = set()
    for region in regions:
        entry = f'navmesh/nv_{region:04x}.nvm'
        raw, _ = session.get(entry)
        data = parse_nvm(raw)
        name = Path(entry).stem
        manifest['tiles'].append({'name': name, 'entry': entry, 'fbx': name + '.fbx',
                                 'position_cm': region_position_cm(region),
                                 'vertices': len(data['heightmap_vertices'])})
        for obj in data['objects']:
            if obj['RID'] != region:
                continue
            identity = (region, obj['local_uid'])
            if identity in seen:
                raise ValueError(f'Duplicate map object: {identity}')
            seen.add(identity)
            path = table.get(obj['asset_id'])
            if not path:
                raise ValueError(f'object.ifo missing asset ID: {obj["asset_id"]}')
            if path not in cache:
                cache[path] = resource_paths(session, path)
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
