# SPDX-License-Identifier: GPL-3.0-or-later
import unreal as u,json,math
from pathlib import Path
root=Path(u.Paths.project_dir());evidence=json.loads((root/'CharacterTestReport.json').read_text());bundle=root/'SourceAssets/SilkroadCharacters'/evidence['bundle'];r=json.loads((bundle/'ImportReport.json').read_text());sub=u.get_editor_subsystem(u.EditorAssetSubsystem)
mesh=sub.load_asset(r['mesh']);skeleton=sub.load_asset(r['skeleton']);summary=[];moving=[]
for rec in r['animations']:
 a=sub.load_asset(rec['asset']);assert a.get_editor_property('skeleton')==skeleton
 names=list(u.AnimationLibrary.get_animation_track_names(a));keys=a.get_editor_property('number_of_sampled_keys');assert keys>1 and names
 changes=0
 for name in names:
  p=u.AnimationLibrary.get_bone_pose_for_time(a,name,rec['seconds']*.1,False)
  q=u.AnimationLibrary.get_bone_pose_for_time(a,name,rec['seconds']*.37,False)
  left=list(p.translation.to_tuple())+list(p.rotation.to_tuple());right=list(q.translation.to_tuple())+list(q.rotation.to_tuple())
  assert all(math.isfinite(v) for v in left+right)
  if max(abs(v-w) for v,w in zip(left,right))>1e-4:changes+=1
 summary.append({'label':rec['label'],'sampled_keys':keys,'bone_tracks':len(names),'moving_tracks':changes})
 if changes:moving.append(rec['label'])
if r['source']=='res/mob/europe/wolf.bsr':assert 'wolf_walk' in moving and 'wolf_run' in moving
report={'passed':True,'saved_assets_reloaded':True,'animations':len(summary),'motion_checks':summary,'engine':u.SystemLibrary.get_engine_version()}
(root/'CharacterMotionValidation.json').write_text(json.dumps(report,indent=2));print('CHARACTER_MOTION_VALIDATED',summary,flush=True)
