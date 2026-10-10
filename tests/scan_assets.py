import sys, json
from pathlib import Path
base=Path(__file__).resolve().parent
if base.name=='tests': base=base.parent
sys.path.insert(0,str(base/'engine'))
from pk2api import Pk2Stream
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('C:/Users/slyva/Downloads/Silkroad/Holigan')
selected={}
counts={}
for name in ('Data.pk2','Map.pk2'):
    print('SCAN',name,flush=True)
    with Pk2Stream(str(root/name),'169841',read_only=True) as s:
        for f in s.iter_files():
            p=f.get_full_path().replace('\\','/')
            ext=Path(p).suffix.lower()
            if ext in ('.bsr','.bms','.bsk','.ban','.nvm','.dof'):
                counts[ext]=counts.get(ext,0)+1
                if len(selected.setdefault(ext,[]))<8:
                    selected[ext].append(p)
        print(name,counts,flush=True)
(base/'real_assets.json').write_text(json.dumps(selected,indent=2))
print(json.dumps(selected,indent=2),flush=True)
