"""Build a reproducible unpacked-extension ZIP without third-party packages."""
import json
from fnmatch import fnmatchcase
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'manifest.json').read_text())
files = [ROOT / name for name in ('manifest.json', 'license', 'readme.md')]
files += sorted((ROOT / 'src').rglob('*'))
files += [ROOT / path for path in manifest['icons'].values()]
files = sorted({path for path in files if path.is_file()})
for content_script in manifest['content_scripts']:
    for path in content_script.get('js', []) + content_script.get('css', []):
        assert ROOT / path in files, f'Missing content script: {path}'
assert ROOT / manifest['action']['default_popup'] in files, 'Missing popup'
assert ROOT / manifest['background']['service_worker'] in files, 'Missing background worker'
for required in ['src/content/search.js', 'src/content/playlist.js', 'src/optimization.js', 'src/content/data-pruning.js', 'src/home/index.html', 'src/home/youtube.svg', 'src/home/home.js', 'src/home/home.css']:
    assert ROOT / required in files, f'Missing required resource: {required}'
for font in ['BarlowCondensed-BlackItalic', 'MinimalCondensed-BlackItalic']:
    path = f'src/assets/fonts/{font}.ttf'
    assert ROOT / path in files, f'Missing title font: {path}'
    assert any(fnmatchcase(path, pattern) and 'https://*.youtube.com/*' in entry.get('matches', [])
               for entry in manifest.get('web_accessible_resources', []) for pattern in entry.get('resources', [])), f'Title font is not accessible: {path}'
for license_file in ['BarlowCondensed-OFL.txt', 'RobotoCondensed-OFL.txt', 'MinimalCondensed-NOTES.txt']:
    assert ROOT / 'src/assets/fonts' / license_file in files, f'Missing font license: {license_file}'
assert any('src/home/index.html' in entry.get('resources', []) and '<all_urls>' in entry.get('matches', [])
           for entry in manifest.get('web_accessible_resources', [])), 'Homepage must be accessible to browser redirects'


# Firefox reads the same sources. Only its manifest differs: an event-page
# background (no service worker), a Gecko ID and Firefox 128+, where MAIN-world
# content scripts and scripting.registerContentScripts({world}) exist.
GECKO_ID = 'minimal-youtube@yt-min.extension'
FIREFOX_MIN = '128.0'


def firefox_manifest(source):
    value = json.loads(json.dumps(source))
    value.pop('minimum_chrome_version', None)
    worker = value['background'].pop('service_worker')
    # optimization.js is loaded by the Chrome worker with importScripts.
    value['background'] = {'scripts': ['src/optimization.js', worker]}
    # AMO requires a data collection declaration: nothing is collected or sent.
    value['browser_specific_settings'] = {'gecko': {'id': GECKO_ID, 'strict_min_version': FIREFOX_MIN,
                                                    'data_collection_permissions': {'required': ['none']}}}
    return value


def build(output, manifest_text):
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            entry = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, manifest_text.encode() if name == 'manifest.json' else path.read_bytes())
    with ZipFile(output) as archive:
        assert archive.testzip() is None, 'Invalid output archive'
        assert not any(name.startswith(('_metadata/', 'tests/', 'scripts/')) for name in archive.namelist())
    print(output)


version = manifest['version']
build(ROOT / 'articafts' / f'minimal-youtube-{version}.zip', (ROOT / 'manifest.json').read_text())
build(ROOT / 'articafts' / f'minimal-youtube-{version}-firefox.zip', json.dumps(firefox_manifest(manifest), indent=4, ensure_ascii=False) + '\n')
