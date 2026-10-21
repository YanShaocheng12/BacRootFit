"""Regenerate one complete native residue/mean/std bank in frozen feature-index order.

Run separately for each encoder. This is an explicit large-data operation; use
--dry-run first. Checkpoint files and sequences are verified before inference.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from bacrootfit.io import fasta, table, sha256, save_json

DIMS = dict(prott5=1024, ankh=768, esm=1280, protbert=1024, esmc=1152)
STORAGE = dict(prott5='float16', ankh='bfloat16_bits', esm='float32', protbert='float16', esmc='bfloat16_bits')


def pack(hidden, name):
    if STORAGE[name] == 'bfloat16_bits':
        packed = (hidden.view(np.uint32) >> 16).astype(np.uint16)
        restored = (packed.astype(np.uint32) << 16).view(np.float32)
    else:
        packed = hidden.astype(STORAGE[name])
        restored = packed.astype(np.float32)
    if not np.array_equal(hidden, restored):
        raise ValueError('Native hidden values cannot be stored losslessly')
    return packed


def load_encoder(name, path):
    import torch
    from transformers import AutoTokenizer, BertModel, BertTokenizer, EsmModel, EsmcModel, PreTrainedTokenizerFast, T5EncoderModel, T5Tokenizer
    if not torch.cuda.is_available():
        raise ValueError('CUDA is required for the registered encoder recipe')
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cuda.enable_cudnn_sdp(name == 'protbert')
    if name != 'protbert':
        torch.backends.cuda.preferred_blas_library('cublas')
        torch.backends.cuda.cublas_workspace_size(32 << 20)
        torch.backends.cuda.cublaslt_workspace_size(32 << 20)
    dtype = dict(prott5=torch.float16, ankh=torch.bfloat16, esm=torch.float32, protbert=torch.float16, esmc=torch.bfloat16)[name]
    if name == 'prott5':
        tokenizer = T5Tokenizer.from_pretrained(path, local_files_only=True, do_lower_case=False, legacy=True)
    elif name == 'protbert':
        tokenizer = BertTokenizer.from_pretrained(path, local_files_only=True, do_lower_case=False)
    elif name == 'ankh':
        tokenizer = PreTrainedTokenizerFast(tokenizer_file=str(path/'tokenizer.json'), unk_token='<unk>', pad_token='<pad>', eos_token='</s>')
    else:
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    cls = dict(prott5=T5EncoderModel, ankh=T5EncoderModel, esm=EsmModel, protbert=BertModel, esmc=EsmcModel)[name]
    kwargs = dict(local_files_only=True, dtype=dtype, output_loading_info=True, attn_implementation='sdpa')
    if name in ['esm', 'protbert']:
        kwargs['add_pooling_layer'] = False
    if name == 'esm':
        kwargs['use_safetensors'] = True
    model, info = cls.from_pretrained(path, **kwargs)
    if any(info.get(k) for k in ['missing_keys', 'mismatched_keys', 'error_msgs']):
        raise ValueError('Incomplete encoder checkpoint loading: '+str(info))
    model = model.to(device='cuda', dtype=dtype).eval()
    model.requires_grad_(False)

    def embed(sequences):
        if name == 'ankh':
            values = [list(s) for s in sequences]
            extra = dict(is_split_into_words=True)
        else:
            values = [' '.join(s) for s in sequences] if name in ['prott5', 'protbert'] else sequences
            extra = {}
        tokens = tokenizer(values, padding=True, return_special_tokens_mask=True, return_tensors='pt', **extra)
        mask = tokens['attention_mask'].bool() & ~tokens.pop('special_tokens_mask').bool()
        if mask.sum(1).tolist() != [len(s) for s in sequences]:
            raise ValueError('Tokenizer is not one token per residue')
        if any(int(tokens['input_ids'][i][mask[i]].eq(tokenizer.unk_token_id).sum()) for i in range(len(sequences))):
            raise ValueError('Unknown residue token')
        with torch.inference_mode():
            hidden = model(**{k: v.cuda() for k, v in tokens.items()}).last_hidden_state.float()
        if not torch.isfinite(hidden).all():
            raise ValueError('Nonfinite encoder features')
        return [hidden[i][mask[i].cuda()].cpu().numpy() for i in range(len(sequences))]
    return model, embed


def extract(name, folder, index, sequences, encoder_dir, lock, root, smoke=False):
    folder.mkdir(parents=True, exist_ok=False)
    model, embed = load_encoder(name, encoder_dir)
    n, dim = len(index), DIMS[name]
    lengths = np.array([int(r['length']) for r in index])
    offsets = np.r_[0, np.cumsum(lengths[:-1])]
    total = int(lengths.sum())
    dtype = np.uint16 if STORAGE[name] == 'bfloat16_bits' else np.dtype(STORAGE[name])
    def mapped(filename, dtype, shape):
        return np.lib.format.open_memmap(folder/filename, mode='w+', dtype=dtype, shape=shape)
    residues = mapped('residues.npy', dtype, (total, dim))
    means = mapped('mean.npy', np.float32, (n, dim))
    stds = mapped('std.npy', np.float32, (n, dim))
    done = mapped('done.npy', np.uint8, (n,))
    segments = [(i, start, sequences[r['sample_id']][start:start+1022]) for i, r in enumerate(index) for start in range(0, int(r['length']), 1022)]
    segments.sort(key=lambda v: (len(v[2]), v[0], v[1]))
    budget = 1000000 if name == 'esm' else 3000000
    acc, at, last = {}, 0, 0
    started = time.monotonic()
    while at < len(segments):
        batch, maxlen = [], 0
        while at+len(batch) < len(segments) and len(batch) < 24:
            candidate = segments[at+len(batch)]
            newlen = max(maxlen, len(candidate[2])+2)
            if batch and (len(batch)+1)*newlen*newlen > budget:
                break
            batch.append(candidate)
            maxlen = newlen
        arrays = embed([s for _, _, s in batch])
        for (i, position, sequence), hidden in zip(batch, arrays):
            if hidden.shape != (len(sequence), dim):
                raise ValueError('Unexpected hidden shape')
            residues[offsets[i]+position:offsets[i]+position+len(sequence)] = pack(hidden, name)
            if i not in acc:
                acc[i] = dict(sum=np.zeros(dim, np.float64), sq=np.zeros(dim, np.float64), count=0)
            a = acc[i]
            a['sum'] += hidden.sum(0, dtype=np.float64)
            a['sq'] += np.square(hidden.astype(np.float64)).sum(0)
            a['count'] += len(sequence)
            if a['count'] == lengths[i]:
                mean = a['sum']/lengths[i]
                means[i] = mean
                stds[i] = np.sqrt(np.maximum(a['sq']/lengths[i]-mean**2, 0))
                done[i] = 1
                del acc[i]
        at += len(batch)
        if time.monotonic()-last > 20 or at == len(segments):
            for array in [residues, means, stds, done]:
                array.flush()
            save_json(folder/'progress.json', dict(complete=int(done.sum()), total=n, seconds=time.monotonic()-started))
            print(f'{name}: {int(done.sum())}/{n} proteins', flush=True)
            last = time.monotonic()
        import torch
        if torch.cuda.memory_reserved() > 5*(1 << 30):
            torch.cuda.empty_cache()
    if acc or not done.all() or not np.isfinite(means).all() or not np.isfinite(stds).all():
        raise ValueError('Incomplete or nonfinite bank')
    files = {name: sha256(folder/name) for name in ['residues.npy', 'mean.npy', 'std.npy', 'done.npy']}
    original = json.loads((root/'config/feature_banks'/f'{name}.json').read_text(encoding='utf8'))
    save_json(folder/'complete.json', dict(status='smoke_test_only' if smoke else 'complete_verified',
              encoder=name, proteins=n, dimension=dim, total_residues=total, storage=STORAGE[name],
              window=1022, ddof=0, labels_used=False, files=files, seconds=time.monotonic()-started,
              checkpoint=lock, feature_index_sha256=sha256(root/'config/feature_index.tsv'),
              historical_bank_hash_match={k: v == original['files'][k] for k, v in files.items()},
              code_sha256=sha256(Path(__file__)), smoke_test=smoke))
    del model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoder', choices=list(DIMS), required=True)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--encoder-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New directory for this encoder bank')
    parser.add_argument('--download', action='store_true', help='Download the pinned checkpoint before verifying it')
    parser.add_argument('--dry-run', action='store_true', help='Check input identities and report storage; do not download or infer')
    parser.add_argument('--smoke-test', action='store_true', help='Extract only the three checked software examples; not a search bank')
    args = parser.parse_args()
    root, path = args.root.resolve(), args.encoder_dir.resolve()
    lock = json.loads((root/'config/encoder_checkpoints.json').read_text(encoding='utf8'))[args.encoder]
    index = table(root/'config/feature_index.tsv')
    if args.smoke_test:
        sequences = dict(fasta(root/'examples/example.faa'))
        index = [r for r in index if r['sample_id'] in sequences]
    else:
        seqs = fasta(root/'data/proteins.faa')+fasta(root/'external/H3/proteins.faa')
        sequences = dict(seqs)
        if len(sequences) != len(seqs) or set(sequences) != {r['sample_id'] for r in index}:
            raise ValueError('FASTA and frozen feature index do not match exactly')
    for row in index:
        sequence = sequences[row['sample_id']]
        if hashlib.sha256(sequence.encode()).hexdigest() != row['sequence_sha256'] or len(sequence) != int(row['length']):
            raise ValueError('Sequence differs from frozen feature index')
    residue_bytes = 4 if args.encoder == 'esm' else 2
    estimated = sum(int(r['length']) for r in index)*DIMS[args.encoder]*residue_bytes + len(index)*DIMS[args.encoder]*8
    print(json.dumps(dict(encoder=args.encoder, checkpoint=lock['repo'], revision=lock['revision'],
                         proteins=len(index), estimated_array_bytes=estimated, smoke_test=args.smoke_test)), flush=True)
    if args.dry_run:
        return
    if args.out.exists():
        parser.error('Use a new output directory; existing banks are never overwritten')
    if args.download:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=lock['repo'], revision=lock['revision'], local_dir=path,
                          allow_patterns=[f.get('file', f.get('path')) for f in lock['files']])
    for record in lock['files']:
        name = record.get('file', record.get('path'))
        if sha256(path/name) != record['sha256']:
            raise ValueError('Pinned checkpoint checksum mismatch: '+name)
    extract(args.encoder, args.out, index, sequences, path, lock, root, args.smoke_test)


if __name__ == '__main__':
    main()
