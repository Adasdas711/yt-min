"""Build a reproducible unpacked-extension ZIP without third-party packages."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'manifest.json').read_text())
files = [ROOT / name for name in ('manifest.json', 'license', 'readme.md')]
files += sorted((ROOT / 'src').rglob('*'))
files += [ROOT / path for path in manifest['icons'].values()]
files = sorted({path for path in files if path.is_file()})
for content_script in manifest['content_scripts']:
    for path in content_script['js'] + content_script['css']:
        assert ROOT / path in files, f'Missing content script: {path}'
assert ROOT / manifest['action']['default_popup'] in files, 'Missing popup'
assert ROOT / manifest['background']['service_worker'] in files, 'Missing background worker'
for required in ['src/optimization.js', 'src/content/data-pruning.js', 'src/home/index.html', 'src/home/home.js', 'src/home/home.css']:
    assert ROOT / required in files, f'Missing memory-optimization resource: {required}'

output = ROOT / 'articafts' / f'minimal-youtube-{manifest["version"]}.zip'
output.parent.mkdir(exist_ok=True)
with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
    for path in files:
        entry = ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
        entry.compress_type = ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, path.read_bytes())
with ZipFile(output) as archive:
    assert archive.testzip() is None, 'Invalid output archive'
    assert not any(name.startswith(('_metadata/', 'tests/', 'scripts/')) for name in archive.namelist())
print(output)
