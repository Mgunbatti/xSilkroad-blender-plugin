# SPDX-License-Identifier: GPL-3.0-or-later
"""Check registered Blender operator availability without exporting assets."""
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import silkroad_pk2_bridge as addon

addon.register()
props = bpy.context.scene.silkroad_editor
row = props.entries.add()
props.selected_index = 0

def check(project, character):
    assert bpy.ops.silkroad_editor.export_ue_project.poll() == project
    assert bpy.ops.silkroad_editor.export_ue_character.poll() == character

check(False, False)
addon._session = object()
row.path, row.is_folder = 'res', True
check(True, False)
row.path, row.is_folder = 'res/mob/europe/wolf.bsr', False
check(True, True)
row.path = 'res/mob/europe/wolf.bms'
check(True, False)
row.path = 'res/mob/europe/WOLF.BSR'
check(True, True)
props.loading = True
check(False, False)
props.loading = False
addon._ue_active_operator = object()
check(False, False)
addon._ue_active_operator = None
props.entries.clear()
check(True, False)
addon._session = None
check(False, False)
addon.unregister()
print('UE_OPERATOR_POLL_MATRIX_PASSED: 9 states, 18 registered operator checks')
