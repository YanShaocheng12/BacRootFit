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
