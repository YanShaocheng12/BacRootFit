from pathlib import Path
from zipfile import ZipFile
import pytest
from bacrootfit.assets import unpack_checked
from bacrootfit.io import fasta


def test_duplicate_fasta_identifiers_and_noncanonical_sequences_rejected(tmp_path):
    p = tmp_path/'bad.faa'
    p.write_text('>one\nACD\n>one\nACD\n')
    with pytest.raises(ValueError):
        fasta(p)
    p.write_text('>one\nACX\n')
    with pytest.raises(ValueError):
        fasta(p)


def test_asset_install_stays_inside_root_and_preserves_changed_files(tmp_path):
    p = tmp_path/'asset.zip'
    with ZipFile(p, 'w') as z:
        z.writestr('../escape.txt', 'x')
    with pytest.raises(ValueError):
        unpack_checked(p, tmp_path/'target')
    with ZipFile(p, 'w') as z:
        z.writestr('data/a.txt', 'versioned')
    unpack_checked(p, tmp_path/'target')
    unpack_checked(p, tmp_path/'target')
    (tmp_path/'target/data/a.txt').write_text('edited')
    with pytest.raises(FileExistsError):
        unpack_checked(p, tmp_path/'target')


def test_new_software_citation_is_retained_only_when_manifest_pinned(tmp_path):
    import hashlib
    archive = tmp_path/'old_data.zip'
    with ZipFile(archive, 'w') as z:
        z.writestr('CITATION.cff', 'older data citation')
        z.writestr('data/a.tsv', 'data')
    root = tmp_path/'source'
    root.mkdir()
    citation = root/'CITATION.cff'
    citation.write_text('current software citation')
    lock = {'CITATION.cff': hashlib.sha256(citation.read_bytes()).hexdigest()}
    unpack_checked(archive, root, lock)
    assert citation.read_text() == 'current software citation'
    assert (root/'data/a.tsv').read_text() == 'data'
    citation.write_text('locally modified citation')
    with pytest.raises(FileExistsError):
        unpack_checked(archive, root, lock)


def test_online_asset_is_extracted_before_temporary_download_is_removed(tmp_path, monkeypatch):
    import hashlib, json, shutil
    from bacrootfit.assets import main
    archive = tmp_path/'archive.zip'
    with ZipFile(archive, 'w') as z:
        z.writestr('data/a.tsv', 'checked data')
    root = tmp_path/'source'
    root.mkdir()
    manifest = dict(assets=[dict(kind='data', filename='data.zip',
                    sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), download_url='https://example.org/data.zip')])
    (root/'release_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr('urllib.request.urlretrieve', lambda url, target: shutil.copyfile(archive, target))
    main(['--root', str(root), '--only', 'data'])
    assert (root/'data/a.tsv').read_text() == 'checked data'
