"""Install extension ZIP in an isolated Blender profile, never user's prefs."""
from pathlib import Path
import sys,os,subprocess,json
base=Path(__file__).resolve().parents[1]
blender=sys.argv[1];package=Path(sys.argv[2]).resolve()
profile=base/'install_test_profile';profile.mkdir(exist_ok=True)
env=os.environ.copy()
for part,variable in [('config','BLENDER_USER_CONFIG'),('scripts','BLENDER_USER_SCRIPTS'),
                      ('datafiles','BLENDER_USER_DATAFILES'),('extensions','BLENDER_USER_EXTENSIONS')]:
    path=profile/part;path.mkdir(exist_ok=True);env[variable]=str(path)
def run(args):
    result=subprocess.run([blender,*args],env=env,capture_output=True,text=True)
    print(result.stdout);print(result.stderr)
    if result.returncode:raise RuntimeError(f'Blender exited {result.returncode}')
    return result.stdout
expected=str(profile/'config')
run(['--background','--factory-startup','--python-expr',
     f"import bpy; from pathlib import Path; assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path({expected!r}).resolve(); print('ISOLATED_CONFIG_OK')"])
run(['--command','extension','repo-add','silkroad_test','--name','Silkroad Test','--directory',str(profile/'extensions/silkroad_test')])
run(['--command','extension','install-file','-r','silkroad_test','-e',str(package)])
output=run(['--background','--python-expr',
            "import bpy; print(bpy.ops.silkroad_editor.import_selected.get_rna_type().identifier); print('INSTALLED_EXTENSION_REGISTERED_OK')"])
assert 'INSTALLED_EXTENSION_REGISTERED_OK' in output
out=base/'real_test_output';out.mkdir(exist_ok=True)
(out/'install_results.json').write_text(json.dumps(dict(passed=True,isolated_profile=True,zip=package.name),indent=2))
