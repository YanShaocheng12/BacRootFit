"""Enable public download URLs only after their exact contents are verified."""
import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repository', required=True)
parser.add_argument('--tag', default='v1.0.0')
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
base = args.repository.rstrip('/')
if not base.startswith('https://github.com/') or len(base.split('/')) != 5:
    parser.error('Expected https://github.com/OWNER/REPOSITORY')
path=args.root/'release_manifest.json'
manifest=json.loads(path.read_text(encoding='utf8'))
for item in manifest['assets']:
    url=f"{base}/releases/download/{args.tag}/{item['filename']}"
    digest=hashlib.sha256()
    with urllib.request.urlopen(url) as response:
        for chunk in iter(lambda: response.read(8<<20), b''):digest.update(chunk)
    if digest.hexdigest()!=item['sha256']:raise ValueError('Remote asset checksum mismatch: '+item['filename'])
    item['download_url']=url
manifest['publication_state']='remote_assets_verified'
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
site=args.root/'website/dist/data/release.json'
release=json.loads(site.read_text(encoding='utf8'));release['repository_available']=True
release['assets']=manifest['assets'];release['publication_state']=manifest['publication_state']
site.write_text(json.dumps(release,ensure_ascii=False,separators=(',',':')),encoding='utf8')
print('Public release asset URLs and website download state verified')
