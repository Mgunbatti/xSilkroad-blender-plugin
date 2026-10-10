# SPDX-License-Identifier: GPL-3.0-or-later
"""Silkroad PK2 Editor - native archive browsing and selective editing in Blender."""
bl_info = {
    'name': 'Silkroad PK2 Editor',
    'author': 'Silkroad PK2 Editor contributors',
    'version': (2, 4, 2),
    'blender': (4, 2, 0),
    'location': 'View3D > Sidebar > Silkroad',
    'description': 'Open PK2 in Blender, import models, export blend/fbx and safely update BMS',
    'category': 'Import-Export',
}

import importlib
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import traceback

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty,
                       StringProperty)
from bpy.types import Operator, OperatorFileListElement, Panel, PropertyGroup, UIList
from bpy_extras.io_utils import ImportHelper, ExportHelper

from . import JellyBMS, JellyBSK, JellyBAN, JellyBSR, JellyDOF, JellyNVM
from .i18n import translate, translate_error
from .fbx_texture_export import export_fbx_with_textures
from .bridge_core import InvalidAsset
from .pk2_core import (ArchiveSession, normalize_path, prepare_asset, replace_pk2_entry_safely,
                       safe_local_path, SUPPORTED_EXTS)

_OWNED_IMPORTERS = []
_IMPORTERS = (
    (JellyBMS, ('jmxvbms_0110',), ('jmxvbms_0110',)),
    (JellyBSK, ('jmxvbsk_0110',), ('jmxvbsk_0101',)),
    (JellyBAN, ('jmxvban_0102',), ('jmxvban_0102',)),
    (JellyBSR, ('jmxvres_0109',), ()),
    (JellyDOF, ('jmxvdof_0101',), ()),
    (JellyNVM, ('jmxvnvm_1000',), ()),
)
_session = None
_load_job = None
_last_workspaces = []
_ue_active_operator = None
_progress_previews = None


def _t(message, props=None, **format_values):
    if props is None:
        # Operators may run outside the panel. Fall back safely to English.
        try:
            props = bpy.context.scene.silkroad_editor
        except (AttributeError, RuntimeError):
            pass
    language = getattr(props, 'language', 'EN')
    return translate(message, language, **format_values)


def _on_language_change(props, context):
    """Update visible status immediately; archive/selection remain untouched."""
    source = getattr(props, 'status_source', '') or 'Ready to open a PK2 archive'
    try:
        import json
        values = json.loads(getattr(props, 'status_values', '') or '{}')
    except (TypeError, ValueError):
        values = {}
    if source == 'Error: {error}':
        values['error'] = translate_error(values.get('error', ''), props.language)
    props.message = _t(source, props, **values)
    _redraw_pk2_panels()



def _setup_progress_previews():
    """Load true-green icon previews (native UILayout.progress has no color prop)."""
    global _progress_previews
    try:
        import bpy.utils.previews as previews
        atlas = previews.new()
        root = Path(__file__).resolve().parent / 'assets'
        atlas.load('green', str(root / 'progress_green.png'), 'IMAGE')
        atlas.load('dim', str(root / 'progress_dark.png'), 'IMAGE')
        _progress_previews = atlas
    except Exception as exc:
        print('[Silkroad PK2 Editor] Green progress icons unavailable:', exc)
        _progress_previews = None


def _teardown_progress_previews():
    global _progress_previews
    if _progress_previews is not None:
        try:
            import bpy.utils.previews as previews
            previews.remove(_progress_previews)
        finally:
            _progress_previews = None


def _draw_green_progress(layout, state, fraction, text):
    """Ten image-backed green segments. Unknown PK2 scan total => pulse."""
    atlas = _progress_previews
    if atlas is None:
        # Preserve native UI if Blender fails to load our optional art assets.
        layout.progress(factor=fraction, type='BAR', text=text)
        return
    bar = layout.row(align=True)
    head = int(max(0.0, min(0.999, fraction)) * 10)
    for i in range(10):
        is_lit = state == 'READY' or (state == 'LOADING' and abs(i - head) <= 1)
        bar.label(text='', icon_value=atlas['green' if is_lit else 'dim'].icon_id)
    layout.label(text=text)


def _module_path():
    base = bpy.utils.user_resource('SCRIPTS', path='modules', create=True)
    return str(Path(base) / 'silkroad_pk2_editor_deps')


def _activate_engine():
    base = _module_path()
    if base not in sys.path:
        sys.path.insert(0, base)
    importlib.invalidate_caches()
    try:
        from pk2api import Pk2Stream
        return True
    except ImportError:
        return False


def _op_available(space, name):
    try:
        getattr(getattr(bpy.ops, space), name).get_rna_type()
        return True
    except (KeyError, AttributeError, ValueError, RuntimeError):
        return False


@contextmanager
def _viewport_operator_context(context):
    """Run import operators in a VIEW_3D window region."""
    window = context.window
    if window is None:
        raise RuntimeError(_t('No Blender window found. Run this tool in a 3D Viewport.'))
    screen = window.screen
    area = context.area if context.area is not None and context.area.type == 'VIEW_3D' else None
    if area is None:
        area = next((candidate for candidate in screen.areas if candidate.type == 'VIEW_3D'), None)
    if area is None:
        raise RuntimeError(_t('No 3D Viewport found. Open one and try again.'))
    region = next((candidate for candidate in area.regions if candidate.type == 'WINDOW'), None)
    if region is None:
        raise RuntimeError(_t('No 3D Viewport window region found.'))
    with bpy.context.temp_override(window=window, area=area, region=region):
        yield


def _ensure_object_mode():
    """Enter Object mode before import."""
    obj = bpy.context.object
    if obj is not None and obj.mode != 'OBJECT':
        if not bpy.ops.object.mode_set.poll():
            raise RuntimeError(_t('Cannot switch to Object Mode. Select Object Mode and try again.'))
        bpy.ops.object.mode_set(mode='OBJECT')


def _report_error(op, context, exc):
    props = context.scene.silkroad_editor
    raw = str(exc)
    message = translate_error(raw, props.language)
    _status(props, 'Error: {error}', error=raw)
    op.report({'ERROR'}, message[:230])
    print('[Silkroad PK2 Editor]', traceback.format_exc())
    if hasattr(getattr(bpy, 'data', None), 'texts'):
        block = bpy.data.texts.get('Silkroad PK2 errors') or bpy.data.texts.new('Silkroad PK2 errors')
        block.write(traceback.format_exc() + '\n')
    return {'CANCELLED'}


def _status(props, message, **format_values):
    """Keep the English status template so a language switch can re-render it."""
    import json
    props.status_source = message
    props.status_values = json.dumps(format_values, ensure_ascii=False)
    localized_values = dict(format_values)
    if message == 'Error: {error}':
        localized_values['error'] = translate_error(localized_values.get('error', ''), props.language)
    props.message = _t(message, props, **localized_values)[:1024]
    print('[Silkroad PK2 Editor]', props.message)


def _status_silent(props, message, **format_values):
    """Update progress without logging hundreds of lines per minute."""
    import json
    props.status_source = message
    props.status_values = json.dumps(format_values, ensure_ascii=False)
    props.message = _t(message, props, **format_values)[:1024]


def _close_session():
    global _session
    if _session is not None:
        _session.close()
        _session = None


def _stop_archive_load():
    """Cancel a pending scan. The worker owns & closes its temporary session."""
    global _load_job
    if _load_job is not None:
        _load_job['cancel'].set()
        _load_job = None


def _start_archive_load(props):
    """Index PK2 on a worker. Never call bpy operators/property API on that thread."""
    global _load_job
    path = Path(bpy.path.abspath(props.archive)).resolve()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if not _activate_engine():
        raise RuntimeError(_t('PK2 engine is missing. Select Install PK2 Engine first.', props))
    if _session is not None and _session.primary == path and _session.key == props.key and _session.streams:
        props.loading = False
        props.scan_state = 'READY'
        props.scan_visual = 1.0
        props.scan_archive = path.name
        _browse(props, '')  # Reuse existing in-memory index; no 30-second rescan.
        return
    _stop_archive_load()
    _close_session()
    props.entries.clear()
    props.selected_index = -1
    props.loading = True
    props.scan_state = 'LOADING'
    props.scan_visual = 0.1
    props.scan_archive = path.name
    props.scan_blocks = 0
    props.scan_has_counter = True
    props.current_folder = ''
    props.search_mode = False
    _status(props, '{archive} is scanning in the background; Blender remains responsive...', archive=path.name)
    job = dict(cancel=threading.Event(), done=False, session=None,
               error=None, blocks=0, archive=path.name, progress_supported=True, tick=0)
    _load_job = job
    key = props.key

    def worker():
        candidate = None
        try:
            def on_progress(pk2_path, count, total):
                if job['cancel'].is_set():
                    raise InterruptedError('PK2 scan cancelled')
                if count is None:
                    # Legacy pk2api cannot report per-block scan progress.
                    job['progress_supported'] = False
                    job['archive'] = Path(pk2_path).name
                    return
                if count == total or count % 64 == 0:
                    job['blocks'] = count
                    job['archive'] = Path(pk2_path).name
            candidate = ArchiveSession(path, key, progress=on_progress)
            if job['cancel'].is_set():
                candidate.close()
            else:
                job['session'] = candidate
                candidate = None
        except Exception as exc:
            job['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if candidate is not None:
                candidate.close()
            job['done'] = True

    job['thread'] = threading.Thread(target=worker, name='SilkroadPK2Scan', daemon=True)
    job['thread'].start()
    if not bpy.app.timers.is_registered(_poll_archive_load):
        bpy.app.timers.register(_poll_archive_load, first_interval=0.20)


def _redraw_pk2_panels():
    """Force UI region redraw on the main thread so progress animates live."""
    data = getattr(bpy, 'data', None)
    for manager in getattr(data, 'window_managers', ()):
        for window in manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def _scan_visual_tick(tick):
    """Indeterminate pulsing indicator; not an estimated completion fraction."""
    phase = tick % 20
    return 0.14 + 0.66 * (1.0 - abs(phase - 10) / 10.0)


def _poll_archive_load():
    """This callback runs on Blender's main thread, so UI updates are safe."""
    global _session, _load_job
    job = _load_job
    if job is None:
        return None
    try:
        props = bpy.context.scene.silkroad_editor
        if not job['done']:
            job['tick'] += 1
            props.scan_visual = _scan_visual_tick(job['tick'])
            props.scan_archive = str(job['archive'])
            props.scan_blocks = int(job['blocks'])
            props.scan_has_counter = bool(job['progress_supported'])
            if job['progress_supported']:
                _status_silent(props, '{archive}: {blocks} blocks scanned. Loading in the background...',
                               archive=job['archive'], blocks=job['blocks'])
            else:
                _status_silent(props, '{archive}: scanning in the background. This PK2 engine has no block counter...',
                               archive=job['archive'])
            _redraw_pk2_panels()
            return 0.25
        _load_job = None
        props.loading = False
        props.scan_visual = 1.0 if job['session'] is not None and not job['error'] else 0.0
        props.scan_state = 'ERROR' if job['error'] else ('READY' if job['session'] is not None else 'CANCELLED')
        props.scan_archive = str(job['archive'])
        props.scan_blocks = int(job['blocks'])
        props.scan_has_counter = bool(job['progress_supported'])
        if job['error']:
            _status(props, 'Could not open PK2: {error}', error=job['error'])
        elif job['session'] is not None:
            _session = job['session']
            _browse(props, '')
            if _session.errors:
                _status(props, 'PK2 opened (some linked archives failed): {error}', error=_session.errors[0])
        else:
            _status(props, 'PK2 loading was cancelled')
        _redraw_pk2_panels()
    except Exception as exc:
        if job.get('session') is not None and job['session'] is not _session:
            job['session'].close()
        print('[Silkroad PK2 Editor] Scan completion error:', exc)
        _load_job = None
    return None


def _open_session(props):
    global _session
    _close_session()
    if not _activate_engine():
        raise RuntimeError(_t('PK2 engine is missing. Click Install PK2 Engine first.', props))
    _session = ArchiveSession(bpy.path.abspath(props.archive), props.key)
    return _session


def _session_or_reopen(props):
    global _session
    if props.loading:
        raise RuntimeError(_t('PK2 is loading in the background. Wait for the scan to finish.', props))
    path = Path(bpy.path.abspath(props.archive)).resolve()
    if (_session is None or _session.primary != path or _session.key != props.key
            or not _session.streams):
        raise RuntimeError(_t('PK2 is not ready. Use Open PK2.', props))
    return _session


def _show_rows(props, rows):
    props.entries.clear()
    for record in rows:
        item = props.entries.add()
        item.name = record['name']
        item.path = record['path']
        item.is_folder = bool(record['folder'])
        item.size = record['size']
    props.selected_index = 0 if len(props.entries) else -1


def _browse(props, folder=''):
    folder = folder.strip('/')
    rows = _session_or_reopen(props).list_folder(folder)
    _show_rows(props, rows)
    props.current_folder = folder
    props.search_mode = False
    _status(props, '{archive} | /{folder} | {count} items', archive=Path(props.archive).name, folder=folder, count=len(rows))


def _selected(props):
    if not (0 <= props.selected_index < len(props.entries)):
        raise ValueError(_t('Select a PK2 entry first.', props))
    return props.entries[props.selected_index]


def _object_source_map(prepared, objects):
    """Only map unique exact intrinsic BMS names, never guess PK2 save targets."""
    by_name = {}
    for obj in objects:
        if obj.type != 'MESH' or obj.name.endswith(('.BoundingBox', '.NavMesh', '.CollisionBox')):
            continue
        name = obj.name.casefold()
        # Blender appends .001 for name collisions; only unique source names are safe.
        by_name.setdefault(name, []).append(obj)
    for original_name, inner in prepared.meshes.items():
        if inner is None:  # Duplicated BMS internal names; never guess which PK2 entry to overwrite.
            continue
        candidates = by_name.get(original_name.casefold(), [])
        if len(candidates) != 1:
            continue
        obj = candidates[0]
        origin = prepared.sources[inner]
        obj['silkroad_pk2_archive'] = str(origin)
        obj['silkroad_pk2_entry'] = inner
        obj['silkroad_pk2_original_name'] = original_name


class SilkroadEntry(PropertyGroup):
    path: StringProperty(name='PK2 internal path')
    is_folder: BoolProperty(name='Is folder')
    size: IntProperty(name='Bytes', min=0, max=2147483647)


class SilkroadEditorSettings(PropertyGroup):
    language: EnumProperty(name='Language', description='Choose the add-on interface language',
                           items=[('EN', 'English', 'English interface'),
                                  ('TR', 'Türkçe', 'Türkçe arayüz')],
                           default='EN', update=_on_language_change)
    status_source: StringProperty(default='Ready to open a PK2 archive', options={'SKIP_SAVE'})
    status_values: StringProperty(default='{}', options={'SKIP_SAVE'})
    archive: StringProperty(name='PK2', description='Data.pk2 / Media.pk2 / Map.pk2', subtype='FILE_PATH')
    key: StringProperty(name='Encryption key', default='169841', description='PK2 archive encryption key')
    current_folder: StringProperty(name='Folder', default='')
    search_query: StringProperty(name='Search', default='', description='Search filenames and paths throughout the archive')
    search_mode: BoolProperty(default=False)
    entries: CollectionProperty(type=SilkroadEntry)
    selected_index: IntProperty(default=-1)
    load_animations: BoolProperty(name='Include animations', default=False)
    load_map_objects: BoolProperty(name='Include map objects', default=False)
    loading: BoolProperty(name='Scanning PK2', default=False, options={'SKIP_SAVE'})
    ue_transfer_running: BoolProperty(default=False, options={'SKIP_SAVE'})
    scan_state: StringProperty(name='Scan state', default='IDLE', options={'SKIP_SAVE'})
    scan_archive: StringProperty(name='Current archive', default='', options={'SKIP_SAVE'})
    scan_visual: FloatProperty(name='Loading indicator', min=0.0, max=1.0, default=0.0, options={'SKIP_SAVE'})
    scan_blocks: IntProperty(name='Scanned blocks', min=0, default=0, options={'SKIP_SAVE'})
    scan_has_counter: BoolProperty(name='Block counter available', default=True, options={'SKIP_SAVE'})
    message: StringProperty(name='Status', default='Ready to open a PK2 archive')


class SILKROAD_UL_ArchiveRows(UIList):
    bl_idname = 'SILKROAD_UL_pk2_rows'

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            if not item.is_folder and Path(item.path).suffix.lower() in SUPPORTED_EXTS:
                button = row.operator('silkroad_editor.import_selected', text=item.name, icon='IMPORT', emboss=False)
                button.entry_index = index
            else:
                row.label(text=item.name, icon='FILE_FOLDER' if item.is_folder else 'FILE')
            if not item.is_folder:
                row.label(text=f'{item.size / 1024:.0f} KB' if item.size < 1048576 else f'{item.size / 1048576:.1f} MB')
        else:
            layout.label(text='', icon='FILE_FOLDER' if item.is_folder else 'FILE')


class SILKROAD_OT_InstallPk2Engine(Operator):
    bl_idname = 'silkroad_editor.install_engine'
    bl_label = 'Install PK2 Engine'
    bl_description = 'Install the pure-Python pk2api==1.5.0 package for Blender (internet required)'

    def execute(self, context):
        target = _module_path()
        try:
            if _activate_engine():
                _status(context.scene.silkroad_editor, 'PK2 engine is already installed')
                return {'FINISHED'}
            Path(target).mkdir(parents=True, exist_ok=True)
            python_exec = getattr(bpy.app, 'binary_path_python', None) or sys.executable
            command = [python_exec, '-m', 'pip', 'install', '--disable-pip-version-check',
                       '--no-input', '--target', target, 'pk2api==1.5.0']
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=180, creationflags=0)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout)[-500:])
            if not _activate_engine():
                raise RuntimeError('PK2API was installed but cannot be imported. Restart Blender.')
            _status(context.scene.silkroad_editor, 'PK2 engine installed. Use Open PK2 to continue.')
            self.report({'INFO'}, _t('PK2 engine installed', context.scene.silkroad_editor))
            return {'FINISHED'}
        except Exception as exc:
            return _report_error(self, context, exc)


class SILKROAD_OT_OpenArchive(Operator, ImportHelper):
    bl_idname = 'silkroad_editor.open_archive'
    bl_label = 'Open PK2'
    bl_description = 'Open a PK2 file and browse its contents inside Blender'
    filename_ext = '.pk2'
    filter_glob: StringProperty(default='*.pk2', options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.silkroad_editor
        try:
            props.archive = self.filepath
            _start_archive_load(props)
            return {'FINISHED'}
        except Exception as exc:
            props.loading = False
            props.scan_state = 'ERROR'
            props.scan_visual = 0.0
            return _report_error(self, context, exc)


class SILKROAD_OT_Navigate(Operator):
    bl_idname = 'silkroad_editor.navigate'
    bl_label = 'Open Folder / Back'
    action: StringProperty(default='ENTER')

    def execute(self, context):
        props = context.scene.silkroad_editor
        try:
            if self.action == 'BACK':
                parent = props.current_folder.rsplit('/', 1)[0] if '/' in props.current_folder else ''
                _browse(props, parent)
            elif self.action == 'REFRESH':
                _browse(props, props.current_folder)
            else:
                row = _selected(props)
                if row.is_folder:
                    _browse(props, row.path)
                else:
                    return bpy.ops.silkroad_editor.import_selected()
            return {'FINISHED'}
        except Exception as exc:
            return _report_error(self, context, exc)


class SILKROAD_OT_Search(Operator):
    bl_idname = 'silkroad_editor.search'
    bl_label = 'Search All PK2 Files'

    def execute(self, context):
        props = context.scene.silkroad_editor
        try:
            results = _session_or_reopen(props).search(props.search_query)
            _show_rows(props, results)
            props.search_mode = True
            _status(props, '{count} search results shown (max 250)', count=len(results))
            return {'FINISHED'}
        except Exception as exc:
            return _report_error(self, context, exc)


class SILKROAD_OT_ImportFromPk2(Operator):
    bl_idname = 'silkroad_editor.import_selected'
    bl_label = 'Import Selected Model'
    bl_description = 'Import selected PK2 assets into Blender'
    entry_index: IntProperty(default=-1, options={'SKIP_SAVE'})

    def execute(self, context):
        props = context.scene.silkroad_editor
        try:
            if self.entry_index >= 0:
                props.selected_index = self.entry_index
            row = _selected(props)
            if row.is_folder:
                raise InvalidAsset(_t('Select a BSR/BMS model first.', props))
            ext = Path(row.path).suffix.lower()
            if ext not in SUPPORTED_EXTS:
                raise InvalidAsset(_t('{extension} is not a supported 3D asset', props, extension=ext))
            if not _op_available('silkroad_import', {
                '.bsr':'jmxvres_0109','.bms':'jmxvbms_0110','.bsk':'jmxvbsk_0110',
                '.ban':'jmxvban_0102','.dof':'jmxvdof_0101','.nvm':'jmxvnvm_1000'}[ext]):
                raise RuntimeError(_t('Missing Silkroad importer for {extension}', props, extension=ext))
            prepared = prepare_asset(_session_or_reopen(props), row.path,
                                     include_animations=props.load_animations,
                                     include_objects=props.load_map_objects)
            _last_workspaces.append(prepared.workspace)
            before = {obj.as_pointer() for obj in bpy.data.objects}
            bsc = dict(directory=str(prepared.source_path.parent), files=[{'name':prepared.source_path.name}])
            if ext == '.bsr':
                operation = bpy.ops.silkroad_import.jmxvres_0109
                bsc.update(setting_data_pk2_path=str(prepared.data_root),
                           setting_armature=True, setting_armature_animations=props.load_animations,
                           setting_navmesh=False)
            elif ext == '.bms':
                operation = bpy.ops.silkroad_import.jmxvbms_0110
                bsc.update(setting_navmesh=False, setting_bounding_box=False)
            elif ext == '.bsk':
                operation = bpy.ops.silkroad_import.jmxvbsk_0110
            elif ext == '.ban':
                operation = bpy.ops.silkroad_import.jmxvban_0102
                armature = context.view_layer.objects.active
                if not armature or armature.type != 'ARMATURE':
                    raise InvalidAsset(_t('Select a BSK/BSR armature before importing BAN.', props))
            elif ext == '.dof':
                operation = bpy.ops.silkroad_import.jmxvdof_0101
                bsc.update(setting_data_pk2_path=str(prepared.data_root), setting_load_objects=props.load_map_objects)
            else:
                operation = bpy.ops.silkroad_import.jmxvnvm_1000
                bsc.update(setting_data_pk2_path=str(prepared.data_root), setting_map_pk2_path=str(prepared.map_root),
                           setting_load_objects=props.load_map_objects)
            with _viewport_operator_context(context):
                _ensure_object_mode()
                result = operation(**bsc)
            if 'FINISHED' not in result:
                raise RuntimeError(_t('Import did not finish: {result}', props, result=result))
            added = [o for o in bpy.data.objects if o.as_pointer() not in before]
            if not added and ext != '.ban':
                raise RuntimeError(_t('Import created no objects. Check the BSR and its dependencies.', props))
            if prepared.meshes:
                _object_source_map(prepared, added)
            if prepared.missing_optional:
                print('[Silkroad PK2 Editor] Missing/invalid optional dependencies:', prepared.missing_optional)
                block = bpy.data.texts.get('Silkroad dependency log') or bpy.data.texts.new('Silkroad dependency log')
                block.write(row.path + '\n' + '\n'.join(prepared.missing_optional) + '\n')
                _status(props, 'Imported into Blender: {path} | {count} objects | {missing} optional files missing',
                        path=row.path, count=len(added), missing=len(prepared.missing_optional))
            else:
                _status(props, 'Imported into Blender: {path} | {count} objects',
                        path=row.path, count=len(added))
            return {'FINISHED'}
        except Exception as exc:
            return _report_error(self, context, exc)


def _export_bms(obj):
    """Serialize and verify a BMS output file."""
    if obj.type != 'MESH':
        raise InvalidAsset('Only a selected mesh can be saved back to PK2.')
    if len(obj.data.uv_layers) < 1:
        raise InvalidAsset('A UV map is required to save BMS.')
    if not obj.data.polygons or any(len(face.vertices) != 3 for face in obj.data.polygons):
        raise InvalidAsset('Triangulate all mesh faces (3 vertices) before saving BMS.')
    if len(obj.data.vertices) > 65535:
        raise InvalidAsset('BMS supports at most 65535 vertices.')
    if any(abs(float(v) - 1) > 1e-4 for v in obj.scale):
        raise InvalidAsset('Apply mesh scale first: Ctrl+A > Scale.')
    if not _op_available('silkroad_export', 'jmxvbms_0110'):
        raise RuntimeError('BMS export operator is not registered.')
    old_active = bpy.context.view_layer.objects.active
    old_selected = list(bpy.context.selected_objects)
    old_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        with tempfile.TemporaryDirectory(prefix='silkroad_bms_') as tmp:
            result = bpy.ops.silkroad_export.jmxvbms_0110(directory=tmp, setting_overwrite=True,
                                                           setting_navmesh=False)
            if 'FINISHED' not in result:
                raise RuntimeError(_t('BMS export failed: {result}', result=result))
            expected = Path(tmp) / (obj.name + '.bms')
            if not expected.is_file():
                raise RuntimeError('BMS output file was not created. Check Blender console.')
            data = expected.read_bytes()
            if not data.startswith(b'JMXVBMS 0110'):
                raise RuntimeError('The saved BMS file has an invalid signature.')
            return data
    finally:
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for item in old_selected:
                item.select_set(True)
            if old_active:
                bpy.context.view_layer.objects.active = old_active
            if old_mode != 'OBJECT' and old_active:
                bpy.ops.object.mode_set(mode=old_mode)
        except Exception:
            print('[Silkroad PK2 Editor] Selection restoration warning:', traceback.format_exc())


class SILKROAD_OT_SaveBmsToPk2(Operator):
    bl_idname = 'silkroad_editor.save_bms_to_pk2'
    bl_label = 'Save Selected Mesh to PK2 (with backup)'
    bl_description = 'Write BMS with a full PK2 backup and validation'
    bl_options = {'REGISTER'}
    approved: BoolProperty(name='I approve backing up and modifying the PK2 archive', default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and bool(obj.get('silkroad_pk2_entry')) and bool(obj.get('silkroad_pk2_archive')))

    def invoke(self, context, event):
        self.approved = False
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.label(text=_t('WARNING: The original PK2 will be modified!', context.scene.silkroad_editor), icon='ERROR')
        layout.label(text=_t('Mesh: {name}', context.scene.silkroad_editor, name=obj.name))
        layout.label(text=_t('PK2: {name}', context.scene.silkroad_editor, name=Path(obj.get('silkroad_pk2_archive', '')).name))
        layout.label(text=_t('File: {path}', context.scene.silkroad_editor, path=obj.get('silkroad_pk2_entry', '')))
        layout.label(text=_t('Full backup requires about twice the PK2 archive size in free space.', context.scene.silkroad_editor))
        layout.prop(self, 'approved', text=_t('I approve backing up and modifying the PK2 archive', context.scene.silkroad_editor))

    def execute(self, context):
        props = context.scene.silkroad_editor
        if not self.approved:
            self.report({'WARNING'}, _t('Confirmation not given. PK2 was not modified.', props))
            return {'CANCELLED'}
        obj = context.active_object
        archive = Path(obj['silkroad_pk2_archive'])
        inner = normalize_path(obj['silkroad_pk2_entry'])
        try:
            if archive.suffix.lower() != '.pk2' or Path(inner).suffix.lower() != '.bms':
                raise InvalidAsset(_t('Only a BMS entry originating from a PK2 can be saved.', props))
            with _viewport_operator_context(context):
                _ensure_object_mode()
                data = _export_bms(obj)
            _close_session()  # Windows PK2 open file handles must close before os.replace
            backup = replace_pk2_entry_safely(archive, inner, data, key=props.key)
            _status(props, 'Saved to PK2. Original backup: {backup}', backup=str(backup))
            self.report({'INFO'}, _t('BMS saved to PK2; full backup: {backup}', props, backup=backup.name))
            return {'FINISHED'}
        except Exception as exc:
            return _report_error(self, context, exc)
        finally:
            try:
                if props.archive and Path(bpy.path.abspath(props.archive)).is_file():
                    _start_archive_load(props)
            except Exception as ex:
                _status(props, 'Could not reopen PK2: {error}', error=str(ex))


class SILKROAD_OT_SaveBlend(Operator):
    bl_idname = 'silkroad_editor.save_blend'
    bl_label = 'Save .blend'

    def execute(self, context):
        # Pack external textures so the saved .blend does not depend on a temp workspace.
        try:
            bpy.ops.file.pack_all()
        except Exception as exc:
            self.report({'WARNING'}, _t('Could not pack textures: {error}', context.scene.silkroad_editor, error=exc))
        return bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')


class SILKROAD_OT_ExportFBX(Operator, ExportHelper):
    bl_idname = 'silkroad_editor.export_fbx'
    bl_label = 'Export UE5 FBX + PNG'
    bl_description = 'Export FBX with DDS/DDJ images converted to PNG; original materials stay unchanged'
    filename_ext = '.fbx'
    filter_glob: StringProperty(default='*.fbx', options={'HIDDEN'})
    export_png_textures: BoolProperty(
        name='Package PNG textures',
        description='Save Blender image textures as external PNG files beside the FBX', default=True)
    export_animation: BoolProperty(
        name='Export active animation',
        description='Export the active Action for the selected armature (All Actions off)',
        default=True)

    def draw(self, context):
        props = context.scene.silkroad_editor
        col = self.layout.column()
        col.prop(self, 'export_png_textures', text=_t('Package PNG textures', props))
        col.prop(self, 'export_animation', text=_t('Export active animation', props))

    def invoke(self, context, event):
        active = context.active_object
        stem = active.name if active else 'Silkroad_Model'
        if not self.filepath:
            self.filepath = str(Path(bpy.path.abspath('//')).resolve() / (stem + '.fbx'))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        try:
            with _viewport_operator_context(context):
                _ensure_object_mode()
                result = export_fbx_with_textures(
                    bpy, self.filepath, list(context.selected_objects),
                    textures=self.export_png_textures, animation=self.export_animation)
            msg = _t('FBX exported: {name}, PNG: {converted}, missing: {missing}. Check TextureReport.txt.',
                     context.scene.silkroad_editor, name=result.fbx.name,
                     converted=result.converted, missing=len(result.missing))
            _status(context.scene.silkroad_editor, 'FBX exported: {name}, PNG: {converted}, missing: {missing}. Check TextureReport.txt.',
                    name=result.fbx.name, converted=result.converted, missing=len(result.missing))
            if result.missing:
                self.report({'WARNING'}, msg[:230])
            else:
                self.report({'INFO'}, msg[:230])
            return {'FINISHED'}
        except Exception as ex:
            return _report_error(self, context, ex)


class SILKROAD_OT_ExportUEProject(Operator, ExportHelper):
    bl_idname = 'silkroad_editor.export_ue_project'
    bl_label = 'Create Jangan UE Project'
    bl_description = 'Export the original Jangan map and build a separate Unreal project'
    filename_ext = '.uproject'
    filter_glob: StringProperty(default='*.uproject', options={'HIDDEN'})
    unreal_editor: StringProperty(name='Unreal editor', subtype='FILE_PATH')
    run_unreal: BoolProperty(name='Import into Unreal automatically', default=True)

    @classmethod
    def poll(cls, context):
        return _session is not None and _ue_active_operator is None and not context.scene.silkroad_editor.loading

    def invoke(self, context, event):
        from .ue_blender import find_unreal_editor
        self.unreal_editor = self.unreal_editor or find_unreal_editor()
        self.filepath = self.filepath or str(Path(bpy.path.abspath('//')).resolve() / 'xSilkroadJangan.uproject')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        props = context.scene.silkroad_editor
        self.layout.prop(self, 'run_unreal', text=_t('Import into Unreal automatically', props))
        self.layout.prop(self, 'unreal_editor', text=_t('Unreal editor', props))
        self.layout.label(text=_t('Creates a new folder beside the chosen project filename.', props))

    def execute(self, context):
        global _ue_active_operator
        from .ue_blender import UEProjectJob
        self._job = None
        self._timer = None
        self._cancel_requested = False
        self._props = context.scene.silkroad_editor
        try:
            self._job = UEProjectJob(bpy, sys.modules[__name__], self.filepath,
                                     self.unreal_editor, self.run_unreal)
            _ue_active_operator = self
            self._props.ue_transfer_running = True
            if bpy.app.background:
                import time
                previous_message = None
                while True:
                    done, message = self._job.step(context)
                    self._props.message = message
                    if message != previous_message:
                        print('[Silkroad UE]', message, flush=True)
                        previous_message = message
                    if done:
                        break
                    if self._job.process:
                        time.sleep(.2)
                self._finish(context)
                return {'FINISHED'}
            self._timer = context.window_manager.event_timer_add(.1, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        except Exception as exc:
            return self._failed(context, exc)

    def modal(self, context, event):
        if event.type == 'ESC' or self._cancel_requested:
            self._job.fail('Transfer cancelled')
            self._finish(context, cancel=True)
            self._props.message = _t('UE transfer cancelled; partial output is kept.', self._props)
            return {'CANCELLED'}
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}
        try:
            done, message = self._job.step(context)
            self._props.message = message
            _redraw_pk2_panels()
            if done:
                self.report({'INFO'}, message[:230])
                self._finish(context)
                return {'FINISHED'}
            return {'RUNNING_MODAL'}
        except Exception as exc:
            return self._failed(context, exc)

    def _failed(self, context, error):
        if self._job:
            self._job.fail(error)
        self._finish(context, cancel=True)
        return _report_error(self, context, error)

    def _finish(self, context, cancel=False):
        global _ue_active_operator
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if self._job:
            self._job.close(cancel=cancel)
        self._props.ue_transfer_running = False
        _ue_active_operator = None


class SILKROAD_OT_CancelUETransfer(Operator):
    bl_idname = 'silkroad_editor.cancel_ue_transfer'
    bl_label = 'Cancel UE Transfer'

    def execute(self, context):
        if _ue_active_operator:
            _ue_active_operator._cancel_requested = True
        return {'FINISHED'}


class SILKROAD_PT_Editor(Panel):
    bl_label = 'PK2 Editor'
    bl_idname = 'SILKROAD_PT_pk2_editor'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Silkroad'

    def draw(self, context):
        props = context.scene.silkroad_editor
        layout = self.layout
        layout.enabled = not props.ue_transfer_running
        lang = layout.row(align=True)
        lang.label(text=_t('Language', props), icon='WORLD')
        lang.prop(props, 'language', text='', expand=True)

        progress_box = layout.box()
        progress_box.label(text=_t('PK2 Loading Status', props), icon='INFO')
        if props.loading:
            _draw_green_progress(progress_box, 'LOADING', props.scan_visual, _t('Scanning PK2...', props))
            progress_box.label(text=props.scan_archive[:42], icon='FILE_ARCHIVE')
            if props.scan_has_counter:
                progress_box.label(text=_t('{count} PK2 blocks scanned (total unknown)', props,
                                           count=props.scan_blocks))
            else:
                progress_box.label(text=_t('Reading archive (engine has no block counter)', props))
            progress_box.operator('silkroad_editor.cancel_scan', text=_t('Cancel Scan', props), icon='CANCEL')
        elif props.scan_state == 'READY':
            _draw_green_progress(progress_box, 'READY', 1.0, _t('Loading complete', props))
            progress_box.label(text=props.scan_archive[:42], icon='CHECKMARK')
        elif props.scan_state in {'ERROR', 'CANCELLED'}:
            _draw_green_progress(progress_box, props.scan_state, 0.0,
                                 _t('Loading cancelled' if props.scan_state == 'CANCELLED'
                                    else 'Could not open PK2', props))
            progress_box.label(text=_t('Error or cancellation details below', props))
        else:
            progress_box.label(text=_t('Choose a PK2 to see loading progress', props), icon='FILE_FOLDER')
        if props.scan_state in {'ERROR', 'CANCELLED'}:
            for offset in range(0, min(len(props.message), 210), 60):
                progress_box.label(text=props.message[offset:offset+60])
        box = layout.box()
        box.label(text=_t('1. Open PK2 Archive', props), icon='FILE_FOLDER')
        if _activate_engine():
            box.label(text=_t('PK2 engine ready', props), icon='CHECKMARK')
        else:
            box.operator('silkroad_editor.install_engine', text=_t('Install PK2 Engine', props), icon='IMPORT')
        box.operator('silkroad_editor.open_archive', text=_t('Open PK2...', props), icon='FILE_FOLDER')
        box.prop(props, 'archive', text='')
        box.prop(props, 'key', text=_t('Encryption key', props))
        if _session is not None:
            box.label(text=_t('{count} PK2 archives available (main + linked)', props, count=len(_session.streams)))
        box = layout.box()
        box.label(text=_t('2. Archive Contents', props), icon='OUTLINER_COLLECTION')
        row = box.row(align=True)
        row.enabled = not props.loading and _session is not None
        row.operator('silkroad_editor.navigate', text=_t('Back', props), icon='BACK').action = 'BACK'
        row.operator('silkroad_editor.navigate', text=_t('Refresh', props), icon='FILE_REFRESH').action = 'REFRESH'
        box.label(text='/' + props.current_folder, icon='FILE_FOLDER')
        row = box.row(align=True)
        row.enabled = not props.loading and _session is not None
        row.prop(props, 'search_query', text='', icon='VIEWZOOM')
        row.operator('silkroad_editor.search', text='', icon='VIEWZOOM')
        contents = box.column()
        contents.enabled = not props.loading and _session is not None
        contents.template_list('SILKROAD_UL_pk2_rows', '', props, 'entries', props, 'selected_index', rows=9)
        if props.search_mode:
            box.label(text=_t('Search results (max 250)', props))
        row = box.row(align=True)
        row.enabled = not props.loading and _session is not None
        row.operator('silkroad_editor.navigate', text=_t('Open Folder', props), icon='FILE_FOLDER').action = 'ENTER'
        box.prop(props, 'load_animations', text=_t('Include animations', props))
        box.prop(props, 'load_map_objects', text=_t('Include map objects', props))
        import_col = box.column()
        import_col.enabled = not props.loading and _session is not None
        import_col.operator('silkroad_editor.import_selected', text=_t('Import Selected Model', props), icon='IMPORT')
        box = layout.box()
        box.label(text=_t('3. Edit / Save', props), icon='EDITMODE_HLT')
        row = box.row(align=True)
        row.operator('silkroad_editor.save_blend', icon='FILE_BLEND', text=_t('Save .blend', props))
        row.operator('silkroad_editor.export_fbx', icon='EXPORT', text=_t('Export .fbx + PNG', props))
        if context.active_object and context.active_object.get('silkroad_pk2_entry'):
            box.label(text=_t('Source: {path}', props,
                              path=context.active_object.get('silkroad_pk2_entry', '')[:49]))
        box.operator('silkroad_editor.save_bms_to_pk2',
                     text=_t('Save Selected Mesh to PK2', props), icon='FILE_TICK')
        box.label(text=_t('PK2 write-back currently supports BMS meshes only.', props))
        layout.enabled = True
        box = layout.box()
        box.label(text=_t('4. Unreal Project', props), icon='WORLD')
        if props.ue_transfer_running:
            box.label(text=props.message[:65])
            box.operator('silkroad_editor.cancel_ue_transfer', text=_t('Cancel UE Transfer', props), icon='CANCEL')
        else:
            box.operator('silkroad_editor.export_ue_project', text=_t('Create Jangan UE Project', props), icon='EXPORT')


class SILKROAD_OT_CancelScan(Operator):
    bl_idname = 'silkroad_editor.cancel_scan'
    bl_label = 'Cancel PK2 Scan'

    def execute(self, context):
        _stop_archive_load()
        context.scene.silkroad_editor.loading = False
        context.scene.silkroad_editor.scan_state = 'CANCELLED'
        context.scene.silkroad_editor.scan_visual = 0.0
        _status(context.scene.silkroad_editor, 'Scan cancelled. Existing PK2 was not modified.')
        _redraw_pk2_panels()
        return {'FINISHED'}


_CLASSES = (SilkroadEntry, SilkroadEditorSettings, SILKROAD_UL_ArchiveRows,
            SILKROAD_OT_InstallPk2Engine, SILKROAD_OT_OpenArchive, SILKROAD_OT_CancelScan,
            SILKROAD_OT_Navigate, SILKROAD_OT_Search, SILKROAD_OT_ImportFromPk2,
            SILKROAD_OT_SaveBmsToPk2, SILKROAD_OT_SaveBlend,
            SILKROAD_OT_ExportFBX, SILKROAD_OT_ExportUEProject, SILKROAD_OT_CancelUETransfer,
            SILKROAD_PT_Editor)


def register():
    _activate_engine()
    _setup_progress_previews()
    for module, imports, exports in _IMPORTERS:
        if not all(_op_available('silkroad_import', item) for item in imports):
            module.register()
            _OWNED_IMPORTERS.append(module)
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.silkroad_editor = PointerProperty(type=SilkroadEditorSettings)


def unregister():
    if _ue_active_operator:
        _ue_active_operator._finish(bpy.context, cancel=True)
    _stop_archive_load()
    _teardown_progress_previews()
    if bpy.app.timers.is_registered(_poll_archive_load):
        bpy.app.timers.unregister(_poll_archive_load)
    _close_session()
    if hasattr(bpy.types.Scene, 'silkroad_editor'):
        del bpy.types.Scene.silkroad_editor
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    for module in reversed(_OWNED_IMPORTERS):
        module.unregister()
    _OWNED_IMPORTERS.clear()
    # Workspaces are intentionally kept: Blender texture paths can reference them.


if __name__ == '__main__':
    register()
