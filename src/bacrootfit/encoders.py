"""Pinned encoder extraction: non-overlapping 1022-residue windows and residue mean."""
import gc, os
import numpy as np
import torch
from .models import DIMS

SPECS = {
    'prott5': ('Rostlab/prot_t5_xl_half_uniref50-enc', '94a6abc029ae13029317b140b7424e012bf8dfbf'),
    'protbert': ('Rostlab/prot_bert', '7a894481acdc12202f0a415dd567f6cfdb698908'),
    'esm2': ('facebook/esm2_t33_650M_UR50D', '08e4846e537177426273712802403f7ba8261b6c'),
}

def extract(sequences, name):
    if not torch.cuda.is_available():
        raise RuntimeError('FASTA encoding requires an NVIDIA CUDA GPU. See README for the feature-based CPU interface.')
    from transformers import T5EncoderModel, T5Tokenizer, BertModel, BertTokenizer, EsmModel, AutoTokenizer
    repo, revision = SPECS[name]
    repo = os.environ.get('BACROOTFIT_' + name.upper() + '_PATH', repo)
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    if name == 'prott5':
        tok = T5Tokenizer.from_pretrained(repo, revision=revision, do_lower_case=False, legacy=True)
        model = T5EncoderModel.from_pretrained(repo, revision=revision, dtype=torch.float16, attn_implementation='sdpa')
    elif name == 'protbert':
        tok = BertTokenizer.from_pretrained(repo, revision=revision, do_lower_case=False)
        model = BertModel.from_pretrained(repo, revision=revision, dtype=torch.float16, add_pooling_layer=False, attn_implementation='sdpa')
    else:
        torch.backends.cuda.enable_cudnn_sdp(False)
        tok = AutoTokenizer.from_pretrained(repo, revision=revision)
        model = EsmModel.from_pretrained(repo, revision=revision, use_safetensors=True, add_pooling_layer=False, attn_implementation='sdpa').float()
    model = model.cuda().eval()
    outputs = []
    for sequence in sequences:
        total = np.zeros(DIMS[name], dtype=np.float64)
        for start in range(0, len(sequence), 1022):
            block = sequence[start:start+1022]
            text = block if name == 'esm2' else ' '.join(block)
            tokens = tok([text], padding=True, return_special_tokens_mask=True, return_tensors='pt')
            mask = tokens['attention_mask'].bool() & ~tokens.pop('special_tokens_mask').bool()
            if int(mask.sum()) != len(block) or tokens['input_ids'][mask].eq(tok.unk_token_id).any():
                raise ValueError('Tokenizer could not map each amino acid to exactly one residue token.')
            with torch.inference_mode():
                hidden = model(**{k: v.cuda() for k, v in tokens.items()}).last_hidden_state.float()
            total += hidden[0][mask[0].cuda()].cpu().numpy().sum(axis=0, dtype=np.float64)
        outputs.append((total / len(sequence)).astype(np.float32))
    del model, tok
    gc.collect()
    torch.cuda.empty_cache()
    return np.stack(outputs)
