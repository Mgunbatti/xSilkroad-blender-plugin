"""Exercise the final file-row operator and viewport override on a prepared NVM.

Pass the extracted workspace root after -- (with Data/navmesh and Map/).
This supplements the full archive E2E, without rescanning multi-GB archives.
"""
from pathlib import Path
import sys,json
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base))
import bpy
import silkroad_pk2_bridge as addon
from silkroad_pk2_bridge.pk2_core import PreparedAsset
root=Path(sys.argv[sys.argv.index('--')+1])
source=next((root/'Data/navmesh').glob('*.nvm'))
addon.register()
props=bpy.context.scene.silkroad_editor
props.entries.clear()
first=props.entries.add();first.name='wrong';first.path='wrong.txt'
row=props.entries.add();row.name=source.name;row.path='navmesh/'+source.name
props.selected_index=0
prepared=PreparedAsset(source,root/'Data',root,row.path,map_root=root/'Map')
addon._session_or_reopen=lambda p:None
addon.prepare_asset=lambda *a,**kw:prepared
area=next(a for a in bpy.context.window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='UI')
with bpy.context.temp_override(area=area,region=region):
    result=bpy.ops.silkroad_editor.import_selected(entry_index=1)
assert result=={'FINISHED'} and props.selected_index==1
terrain=next(o for o in bpy.data.objects if o.name.endswith('.NavMesh'))
assert len(terrain.data.vertices)==9409
assert any(any(uv.uv) for uv in terrain.data.uv_layers.active.data)
class RowLayout:
    def row(self,**kw):return self
    def operator(self,name,**kw):
        self.called=name;self.button=type('Button',(),{})();return self.button
    def label(self,**kw):pass
layout=RowLayout()
addon.SILKROAD_UL_ArchiveRows.draw_item(type('List',(),{'layout_type':'DEFAULT'})(),bpy.context,layout,props,row,None,props,'selected_index',1)
assert layout.called=='silkroad_editor.import_selected' and layout.button.entry_index==1
output=base/'real_test_output';output.mkdir(exist_ok=True)
(output/'dispatch_results.json').write_text(json.dumps(dict(passed=True,selected_index=1,vertices=9409,from_region='UI',file_row_click=True),indent=2))
addon.unregister()
print('FINAL_DISPATCH_SMOKE_OK')
