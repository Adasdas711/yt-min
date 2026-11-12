"""Two store builds from one source: Chrome Web Store and Firefox Add-ons (AMO).

scripts/package.py writes articafts/minimal-youtube-<version>.zip (Chrome,
the repository manifest unchanged) and ...-<version>-firefox.zip (the same
files; only manifest.json differs: an event-page background instead of a
service worker, a Gecko ID, Firefox 128+ and the data collection
declaration AMO requires).
"""
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def manifest_files(manifest):
    names = [manifest['action']['default_popup'], *manifest['icons'].values()]
    background = manifest['background']
    names += [background['service_worker']] if 'service_worker' in background else background['scripts']
    for script in manifest['content_scripts']:
        names += script.get('js', []) + script.get('css', [])
    for entry in manifest.get('web_accessible_resources', []):
        names += [name for name in entry['resources'] if '*' not in name]
    return names


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/package.py')], check=True, capture_output=True)
    source = json.loads((ROOT / 'manifest.json').read_text())
    version = source['version']
    chrome_zip, firefox_zip = ROOT / f'articafts/minimal-youtube-{version}.zip', ROOT / f'articafts/minimal-youtube-{version}-firefox.zip'
    with ZipFile(chrome_zip) as chrome, ZipFile(firefox_zip) as firefox:
        assert chrome.testzip() is None and firefox.testzip() is None
        # The same files; only the manifest differs.
        assert chrome.namelist() == firefox.namelist()
        for name in chrome.namelist():
            if name != 'manifest.json':
                assert chrome.read(name) == firefox.read(name), name
        assert not any(name.startswith(('tests/', 'scripts/', '_metadata/', 'articafts/', '.git')) for name in chrome.namelist())
        chrome_manifest = json.loads(chrome.read('manifest.json'))
        firefox_manifest = json.loads(firefox.read('manifest.json'))
    # Chrome: the repository manifest as it is.
    assert chrome_manifest == source
    assert chrome_manifest['background'] == {'service_worker': 'src/background.js'}
    # Firefox: event-page background, Gecko settings, nothing Chrome-only.
    assert firefox_manifest['background'] == {'scripts': ['src/optimization.js', 'src/background.js']}
    gecko = firefox_manifest['browser_specific_settings']['gecko']
    assert gecko['id'] and gecko['strict_min_version'] == '128.0', gecko
    assert gecko['data_collection_permissions'] == {'required': ['none']}, gecko
    assert 'minimum_chrome_version' not in firefox_manifest
    assert firefox_manifest['version'] == version and firefox_manifest['manifest_version'] == 3
    for key in ['content_scripts', 'permissions', 'host_permissions', 'web_accessible_resources', 'action', 'icons', 'name', 'description']:
        assert firefox_manifest[key] == source[key], key
    # Every file either manifest names is in the archive.
    for manifest in (chrome_manifest, firefox_manifest):
        for name in manifest_files(manifest):
            assert name in chrome.namelist(), name
    print(f'PASS two store builds: {chrome_zip.name} (Chrome) and {firefox_zip.name} (Firefox), same files, only the manifest differs', flush=True)


if __name__ == '__main__':
    main()
