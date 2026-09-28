"""First-run settings migration. Existing new settings always take precedence."""
from pathlib import Path
import json, os

def migrate_settings(local_appdata):
    root=Path(local_appdata)
    target=root/'Oasis Attend'/'settings.json'
    legacy=root/'ZKDesk'/'settings.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists() and legacy.is_file():
        data=json.loads(legacy.read_text('utf-8-sig'))
        if not isinstance(data,dict):raise ValueError('Legacy settings must contain a JSON object.')
        pending=target.with_suffix('.migration.tmp')
        pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(pending,target)
    return target
