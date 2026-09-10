"""Build browser data from the original catalog and class model; no network."""
import csv
import json
from pathlib import Path
import runpy
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def build():
    runpy.run_path(str(ROOT / 'scripts/check_html.py'))
    model = runpy.run_path(str(ROOT / 'helpers.py'))
    with (ROOT / 'items.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    items = []
    for i, row in enumerate(rows):
        item = {'id': i, 'name': row['Item'], 'class_group': row['Class']}
        allowed = set()
        for group in row['Class'].split(':'):
            if group.strip() not in model['ITEM_CLASS_MAP']:
                raise ValueError('Unknown class group: ' + group)
            allowed.update(model['ITEM_CLASS_MAP'][group.strip()])
        item['classes'] = sorted(allowed)
        item['stats'] = {k: float(v or 0) for k, v in row.items() if k not in {'Item', 'Class'}}
        items.append(item)
    with (ROOT / 'class_weights.csv').open(encoding='utf-8-sig', newline='') as f:
        weights = {r['Class']: {k: float(v or 0) for k, v in r.items() if k != 'Class'} for r in csv.DictReader(f)}
    if set(weights) != set(model['CLASSES']):
        raise ValueError('Class weights must match the class catalogue exactly.')
    primary = {name: stat for stat, names in model['CLASS_PRIMARY_ATTR'].items() for name in names}
    data = {'items': items, 'weights': weights, 'primary': primary, 'classes': model['CLASSES'], 'source_revision': 'a6b3d0f'}
    (ROOT / 'web/data.json').write_text(json.dumps(data, separators=(',', ':'), allow_nan=False) + '\n')
    out = ROOT / 'dist'
    if out.exists(): shutil.rmtree(out)
    shutil.copytree(ROOT / 'web', out)
    shutil.copy2(ROOT / 'LICENSE', out / 'LICENSE')
    shutil.copy2(ROOT / 'items.csv', out / 'items.csv')
    shutil.copy2(ROOT / 'class_weights.csv', out / 'class_weights.csv')
    # Explicit allowlist; never package arbitrary checkout contents or local state.
    with zipfile.ZipFile(out / 'teet-local.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['companion.py', 'requirements-local.txt', 'fishing.py', 'LICENSE', 'README.md', 'start-local.bat']:
            z.write(ROOT / name, 'teet-local/' + name)
        z.write(ROOT / 'LICENSE', 'teet-local/web/LICENSE')
        z.write(ROOT / 'items.csv', 'teet-local/web/items.csv')
        for p in sorted((ROOT / 'web').iterdir()):
            if p.is_file(): z.write(p, 'teet-local/web/' + p.name)
    print(f'Built {len(items)} items / {len(weights)} class profiles → dist/')

if __name__ == '__main__': build()
