# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict Jelly execution, shared by panel and File > Import callers."""
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from datetime import datetime, timezone
import io
import traceback
import bpy
from .bridge_core import validate_asset


def execute_import(operator, context, extension):
    log = io.StringIO()
    collection = context.view_layer.active_layer_collection
    old_mode = getattr(context.object, 'mode', 'OBJECT')
    old_active = context.view_layer.objects.active
    failed = False
    try:
        with redirect_stdout(log), redirect_stderr(log):
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            files = list(operator.files)
            if not files:
                raise ValueError('No import files selected')
            if extension == '.nvm':
                operator._objects_ifo_data = {}
                operator._tile2d_ifo_data = {}
            if extension == '.ban':
                if not old_active or old_active.type != 'ARMATURE':
                    raise ValueError('Select an armature before BAN import')
                old_active.select_set(True)
            for item in files:
                path = Path(operator.directory) / item.name
                print('IMPORT', extension, path)
                if extension == '.bms' and not operator.setting_material_filepath:
                    print('Material note: standalone BMS has no BMT reference; import its BSR for textures.')
                if path.suffix.lower() != extension:
                    raise ValueError(f'Expected {extension}, got {path.suffix}: {path}')
                validate_asset(path)
                before = {o.as_pointer() for o in bpy.data.objects}
                actions = {a.as_pointer() for a in bpy.data.actions}
                if extension == '.bms':
                    bpy.ops.object.select_all(action='DESELECT')
                if extension in ('.bms', '.dof'):
                    ok = operator.LoadFile(context, str(path.parent), path.name)
                else:
                    ok = operator.LoadFile(context, str(path))
                if not ok:
                    raise RuntimeError(f'{extension} LoadFile failed: {path}')
                added = [o for o in bpy.data.objects if o.as_pointer() not in before]
                if extension == '.ban':
                    new_actions = [a for a in bpy.data.actions if a.as_pointer() not in actions]
                    if not new_actions:
                        raise RuntimeError('BAN produced no action: empty animation or incompatible bone names')
                    print('RESULT actions:', ', '.join(a.name for a in new_actions))
                elif not added:
                    raise RuntimeError(f'{extension} produced no objects')
                elif extension == '.bsk' and not any(o.type == 'ARMATURE' and len(o.data.bones) for o in added):
                    raise RuntimeError('BSK produced no bones')
                elif extension in ('.bms', '.bsr', '.dof', '.nvm') and not any(o.type == 'MESH' and len(o.data.vertices) for o in added):
                    raise RuntimeError(f'{extension} produced no mesh vertices')
                print('RESULT objects:', ', '.join(o.name for o in added))
    except Exception as exc:
        failed = True
        log.write(traceback.format_exc())
        operator.report({'ERROR'}, f'{extension.upper()} import: {exc} (see Silkroad import log)')
    finally:
        try:
            # Importers may leave Pose/Edit mode after an exception.
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            context.view_layer.active_layer_collection = collection
            if old_active and old_mode != 'OBJECT':
                context.view_layer.objects.active = old_active
                bpy.ops.object.mode_set(mode=old_mode)
        except Exception:
            log.write('Context restore warning:\n' + traceback.format_exc())
        name = 'Silkroad import ' + extension.upper()
        block = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        block.write('\n' + datetime.now(timezone.utc).isoformat() + '\n' + log.getvalue())
        print(log.getvalue())
    return {'CANCELLED'} if failed else {'FINISHED'}
