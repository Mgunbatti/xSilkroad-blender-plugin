# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json
from .ue_landscape import export_landscape, SCOPES

class LandscapeExportJob:
    def __init__(self, addon, filepath, scope):
        if addon._session is None:raise ValueError('Open the game PK2 archive first')
        if scope not in SCOPES:raise ValueError('Jangan Landscape scope required')
        self.session=addon._session;self.scope=scope;self.root=Path(filepath).resolve().with_suffix('');self.process=None;self.done=False
        if self.root.exists():raise FileExistsError('Choose a new Landscape output folder')
    def step(self, context):
        if not self.done:
            self.manifest=export_landscape(self.session,self.root,self.scope);self.done=True
        return True,'Jangan Landscape exported: '+str(self.root)
    def close(self,cancel=False):pass
    def fail(self,error):
        if self.root.exists():(self.root/'ExportFailure.json').write_text(json.dumps({'status':'failed','error':str(error)},indent=2))
