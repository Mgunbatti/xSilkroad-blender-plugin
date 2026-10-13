# SPDX-License-Identifier: GPL-3.0-or-later
"""Incremental Blender-to-Unreal transfer using the installed PK2 operators."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import math
import os
import shutil
import subprocess
import traceback
from .fbx_texture_export import export_fbx_with_textures, texture_filename
from .ue_project import build_manifest, initialize_project


def find_unreal_editor():
    base = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Epic Games'
    candidates = list(base.glob('UE_5.*/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'))
    def version(path):
        return tuple(int(n) for n in path.parents[3].name.removeprefix('UE_').split('.') if n.isdigit())
    return str(max(candidates, key=version)) if candidates else ''


class UEProjectJob:
    def __init__(self, bpy, addon, filepath, editor='', run_unreal=True, terrain_mode='TILE'):
        if addon._session is None:
            raise ValueError('Open the game PK2 archive first')
        self.bpy, self.addon = bpy, addon
        self.editor = Path(editor or find_unreal_editor()) if run_unreal else None
        if run_unreal:
            if self.editor.name == 'UnrealEditor.exe':
                self.editor = self.editor.with_name('UnrealEditor-Cmd.exe')
            if not self.editor.is_file() or self.editor.name != 'UnrealEditor-Cmd.exe':
                raise ValueError('Choose the installed UnrealEditor-Cmd.exe')
        # Validate game dependencies before creating an output project.
        self.manifest = build_manifest(addon._session)
        if terrain_mode not in ('TILE', 'LANDSCAPE'):
            raise ValueError('Unknown terrain mode')
        self.manifest['terrain_mode'] = terrain_mode
        version = self.editor.parents[3].name.removeprefix('UE_') if self.editor else '5.8'
        self.project = initialize_project(filepath, version)
        self.root, self.source = self.project.parent, self.project.parent / 'SourceAssets'
        self.queue = [('terrain', t['name'], t) for t in self.manifest['tiles']] if terrain_mode == 'TILE' else []
        self.queue += [('asset', key, a) for key, a in self.manifest['assets'].items()]
        self.index = 0
        self.scene = bpy.data.scenes.new('Silkroad_UE_Transfer')
        self.process = None
        self.log = None
        self.closed = False
        self.workspaces = []
        self.save_manifest()

    def save_manifest(self):
        (self.source / 'manifest.json').write_text(json.dumps(self.manifest, indent=2), encoding='utf-8')

    @contextmanager
    def stage(self, context):
        bpy = self.bpy
        original_scene = context.window.scene
        kinds = ('objects', 'collections', 'meshes', 'armatures', 'materials', 'images', 'actions')
        before = {k: set(getattr(bpy.data, k)) for k in kinds}
        material_names = [(mat, mat.name) for mat in bpy.data.materials]
        try:
            for mat, name in material_names:
                mat.name = '__Silkroad_UE_original_' + name
            context.window.scene = self.scene
            context.view_layer.active_layer_collection = context.view_layer.layer_collection
            yield
        finally:
            context.window.scene = original_scene
            for kind in kinds:
                collection = getattr(bpy.data, kind)
                for block in set(collection) - before[kind]:
                    collection.remove(block, do_unlink=True)
            for mat, name in material_names:
                mat.name = name

    def import_entry(self, context, entry):
        props = self.scene.silkroad_editor
        props.archive = str(self.addon._session.primary)
        props.load_animations = False
        props.load_map_objects = False
        props.entries.clear()
        row = props.entries.add()
        row.path, row.name, row.is_folder = entry, Path(entry).name, False
        old_count = len(self.addon._last_workspaces)
        with self.addon._viewport_operator_context(context):
            result = self.bpy.ops.silkroad_editor.import_selected(entry_index=0)
        self.workspaces.extend(self.addon._last_workspaces[old_count:])
        if result != {'FINISHED'}:
            raise RuntimeError(props.message)

    def describe(self, objects):
        descriptors = {}
        for obj in objects:
            for mat in obj.data.materials:
                if not mat:
                    continue
                textures = []
                for node in mat.node_tree.nodes if mat.use_nodes else ():
                    if node.type == 'BSDF_PRINCIPLED':
                        for link in node.inputs['Base Color'].links:
                            image = getattr(link.from_node, 'image', None)
                            if image:
                                textures.append(texture_filename(image))
                descriptors[mat.name] = {'name': mat.name, 'textures': textures,
                                         'color': list(mat.diffuse_color)}
        return list(descriptors.values())

    def export_next(self, context):
        bpy = self.bpy
        kind, key, record = self.queue[self.index]
        with self.stage(context):
            self.import_entry(context, record['entry'] if kind == 'terrain' else record['source'])
            objects = list(self.scene.objects)
            if kind == 'terrain':
                for obj in objects:
                    obj.location = (0, 0, 0)
                    obj.scale = tuple(v * 10 for v in obj.scale)
            else:
                for obj in objects:
                    if not obj.parent:
                        obj.scale = tuple(v * .1 for v in obj.scale)
                        obj.location *= .1
                context.view_layer.update()
                depsgraph = context.evaluated_depsgraph_get()
                baked = []
                for obj in objects:
                    if obj.type != 'MESH':
                        continue
                    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),
                        preserve_all_data_layers=True, depsgraph=depsgraph)
                    repaired = 0
                    for layer in mesh.uv_layers:
                        for loop in layer.data:
                            if not all(math.isfinite(v) for v in loop.uv):
                                loop.uv = (0, 0)
                                repaired += 1
                    if repaired:
                        self.manifest['repairs'].append({'asset': key, 'mesh': obj.name,
                                                         'invalid_uv_loops': repaired})
                    if any(not all(math.isfinite(v) for v in vertex.co) for vertex in mesh.vertices):
                        raise ValueError('Non-finite geometry: ' + obj.name)
                    clone = bpy.data.objects.new(obj.name + '_Static', mesh)
                    self.scene.collection.objects.link(clone)
                    clone.matrix_world = obj.matrix_world.copy()
                    baked.append(clone)
                for obj in objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                objects = baked
            if not objects or not any(o.type == 'MESH' for o in objects):
                raise ValueError('No mesh imported: ' + key)
            descriptors = self.describe(objects)
            for obj in self.scene.objects:
                obj.select_set(obj in objects)
            context.view_layer.objects.active = objects[0]
            with self.addon._viewport_operator_context(context):
                summary = export_fbx_with_textures(bpy, self.source / record['fbx'], objects, animation=False)
            if summary.missing:
                raise ValueError('Missing export textures: ' + str(summary.missing))
            for desc in descriptors:
                desc['textures'] = [str((summary.texture_folder / p).relative_to(self.root)) for p in desc['textures']]
            record['materials'] = descriptors
            record['static_meshes'] = sum(o.type == 'MESH' for o in objects)
            record['static_vertices'] = sum(len(o.data.vertices) for o in objects if o.type == 'MESH')
        self.index += 1
        self.save_manifest()
        return f'{self.index}/{len(self.queue)}: {key}'

    def finish_sources(self, context):
        bpy = self.bpy
        with self.stage(context):
            with self.addon._viewport_operator_context(context):
                bpy.ops.mesh.primitive_cube_add(size=1)
            obj = context.object
            for vertex in obj.data.vertices:
                vertex.co.x = vertex.co.x * 2 + 2
                vertex.co.y = vertex.co.y * 4 + 5
                vertex.co.z = vertex.co.z * 6 + 7
            export_fbx_with_textures(bpy, self.source / 'Calibration.fbx', [obj], textures=False, animation=False)
            texture_index, by_hash = {}, {}
            for _, _, record in self.queue:
                for desc in record['materials']:
                    for relative in desc['textures']:
                        path = self.root / relative
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:20]
                        if digest not in by_hash:
                            image = bpy.data.images.load(str(path), check_existing=False)
                            alpha = image.pixels[3::4]
                            by_hash[digest] = {'key': 'T_' + digest,
                                'alpha': bool(alpha) and min(alpha) < .5 and max(alpha) > .5}
                            bpy.data.images.remove(image)
                        texture_index[relative] = by_hash[digest]
            (self.source / 'texture_index.json').write_text(json.dumps(texture_index, indent=2), encoding='utf-8')
        self.manifest['status'] = 'exported_static'
        self.manifest['plugin_asset_ratio'] = {'processed': len(self.queue), 'total': len(self.queue), 'percent': 100}
        self.save_manifest()
        (self.root / 'KULLANIM_TR.md').write_text(
            '# Jangan UE projesi\n\n.uproject dosyasını Unreal Engine ile aç. Başlangıç haritası '
            f'/Game/Jangan/Maps/Jangan. Sahne, Jangan ve çevresindeki {len(self.manifest["tiles"])} NVM parçasıdır.\n\n'
            'Kaynak geometriler ve PNG dokular SourceAssets klasöründe, nesne yerleşimleri manifest.json dosyasındadır. '
            'ImportReport.json UE aktarımının sonucunu gösterir. Aktarım statik çevre içindir; NPC, görev, '
            'oyun mantığı ve hareketli su sistemi eklemez.\n\n'
            'Ağaç iskeletleri mevcut pozlarıyla sabit modele dönüştürülür. Geçersiz UV düzeltmeleri '
            'manifest.json içindeki repairs listesine yazılır.\n', encoding='utf-8')
        if self.editor:
            self.log = (self.root / 'UnrealImport.log').open('w', encoding='utf-8')
            self.process = subprocess.Popen([str(self.editor), str(self.project), '-run=pythonscript',
                '-script=' + str(self.root / 'Tools' / 'import_jangan.py'), '-unattended', '-NullRHI',
                '-nosplash', '-stdout', '-FullStdOutLogOutput'], stdout=self.log,
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def step(self, context):
        if self.index < len(self.queue):
            return False, self.export_next(context)
        if self.manifest['status'] == 'exporting':
            self.finish_sources(context)
            if not self.editor:
                return True, 'UE source project prepared: ' + str(self.project)
        if self.process and self.process.poll() is None:
            return False, 'Unreal import is running; see UnrealImport.log'
        report_path = self.root / 'ImportReport.json'
        report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
        if not self.process or self.process.returncode != 0 or report.get('status') != 'complete':
            raise RuntimeError('Unreal import failed; see UnrealImport.log and ImportReport.json')
        expected = len(self.manifest['placements']) + (len(self.manifest['tiles']) if self.manifest['terrain_mode']=='TILE' else 1)
        if report.get('actors') != expected or len(report.get('assets', {})) != len(self.queue):
            raise RuntimeError('Unreal import result count mismatch')
        return True, 'UE project ready: ' + str(self.project)

    def fail(self, error):
        self.manifest['status'] = 'failed'
        self.manifest['errors'].append({'error': str(error), 'traceback': traceback.format_exc()})
        self.save_manifest()

    def close(self, cancel=False):
        if self.closed:
            return
        if cancel and self.process and self.process.poll() is None:
            self.process.terminate()
        if self.log:
            self.log.close()
        self.bpy.data.scenes.remove(self.scene)
        for folder in self.workspaces:
            path = Path(folder).resolve()
            if path.name.startswith('Silkroad_PK2_'):
                shutil.rmtree(path, ignore_errors=True)
                if folder in self.addon._last_workspaces:
                    self.addon._last_workspaces.remove(folder)
        self.closed = True
