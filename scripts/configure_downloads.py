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
parser.add_argument('--release-metadata', type=Path, help='GitHub release API JSON; verify server SHA-256 instead of downloading archives again')
args = parser.parse_args()
base = args.repository.rstrip('/')
if not base.startswith('https://github.com/') or len(base.split('/')) != 5:
    parser.error('Expected https://github.com/OWNER/REPOSITORY')
path=args.root/'release_manifest.json'
manifest=json.loads(path.read_text(encoding='utf8'))
remote=json.loads(args.release_metadata.read_text(encoding='utf-8-sig')) if args.release_metadata else None
if remote and (remote.get('draft') or remote.get('tag_name') != args.tag or remote.get('html_url') != f'{base}/releases/tag/{args.tag}'):
    raise ValueError('Release API metadata does not match the public target')
for item in manifest['assets']:
    url=f"{base}/releases/download/{args.tag}/{item['filename']}"
    if remote:
        record=next((r for r in remote['assets'] if r['name']==item['filename']),None)
        if not record or record['size']!=item['bytes'] or record.get('digest')!='sha256:'+item['sha256'] or record['browser_download_url']!=url:
            raise ValueError('Remote asset metadata mismatch: '+item['filename'])
    else:
        digest=hashlib.sha256()
        with urllib.request.urlopen(url,timeout=60) as response:
            for chunk in iter(lambda: response.read(8<<20), b''):digest.update(chunk)
        if digest.hexdigest()!=item['sha256']:raise ValueError('Remote asset checksum mismatch: '+item['filename'])
    item['download_url']=url
    print('Verified: '+item['filename'],flush=True)
manifest['publication_state']='published_assets_verified'
manifest['repository_available']=True
manifest['release_url']=f'{base}/releases/tag/{args.tag}'
manifest['asset_verification']='github_server_sha256_and_size' if remote else 'downloaded_content_sha256'
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
site=args.root/'website/dist/data/release.json'
release=json.loads(site.read_text(encoding='utf8'));release['repository_available']=True
release['assets']=manifest['assets'];release['publication_state']=manifest['publication_state']
release['release_url']=manifest['release_url']
site.write_text(json.dumps(release,ensure_ascii=False,separators=(',',':')),encoding='utf8')
(site.parent/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Public release asset URLs and website download state verified')
