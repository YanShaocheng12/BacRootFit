"""Portable inference for the locked ProtT5-mean RBF-SVM packages.

FASTA -> full frozen ProtT5 mean -> L2 -> saved scaler -> saved SVM -> raw threshold.
No labels, fitting, calibration, or feature-bank lookup occurs in this entry point.
"""
from pathlib import Path
import argparse,csv,json,hashlib,time
import numpy as np
import joblib
from sklearn.preprocessing import normalize

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def fasta(path):
    records=[];name=None;seq=[];seen=set()
    for line in Path(path).read_text(encoding='utf8').splitlines():
        if not line.strip():continue
        if line.startswith('>'):
            if name is not None:records.append((name,''.join(seq)))
            parts=line[1:].split();assert parts,'Empty FASTA identifier';name=parts[0];assert name not in seen,'Duplicate FASTA identifier';seen.add(name);seq=[]
        else:assert name is not None;seq.append(line.strip())
    if name is not None:records.append((name,''.join(seq)))
    assert records and all(s and set(s)<=set('ACDEFGHIKLMNPQRSTVWY') for _,s in records),'Complete canonical proteins required'
    return records

def encode(records,folder,lock):
    import torch
    from transformers import T5Tokenizer,T5EncoderModel
    assert torch.cuda.is_available(),'This registered FP16 recipe requires CUDA; CPU precision is not silently substituted.'
    folder=Path(folder)
    for name,h in lock['encoder_files'].items():assert sha(folder/name)==h,name
    torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.enable_cudnn_sdp(False);torch.backends.cuda.preferred_blas_library('cublas');torch.backends.cuda.cublas_workspace_size(32<<20);torch.backends.cuda.cublaslt_workspace_size(32<<20)
    tok=T5Tokenizer.from_pretrained(folder,local_files_only=True,do_lower_case=False,legacy=True)
    model,info=T5EncoderModel.from_pretrained(folder,local_files_only=True,dtype=torch.float16,output_loading_info=True,attn_implementation='sdpa')
    assert not info.get('missing_keys') and not info.get('mismatched_keys') and not info.get('error_msgs')
    model=model.cuda().half().eval();model.requires_grad_(False);means=[]
    for _,sequence in records:
        hidden=[]
        for start in range(0,len(sequence),1022):
            segment=sequence[start:start+1022];tokens=tok([' '.join(segment)],padding=True,return_special_tokens_mask=True,return_tensors='pt');special=tokens.pop('special_tokens_mask');mask=tokens['attention_mask'].bool()&~special.bool();assert int(mask.sum())==len(segment)
            with torch.inference_mode():value=model(**{k:v.cuda() for k,v in tokens.items()}).last_hidden_state.float()
            hidden.append(value[0][mask[0].cuda()].cpu().numpy())
        means.append(np.concatenate(hidden).mean(0,dtype=np.float64).astype(np.float32))
    return np.stack(means)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fasta',required=True);p.add_argument('--model-dir',required=True);p.add_argument('--out',required=True);p.add_argument('--encoder-dir');p.add_argument('--features',help='Optional NPZ with raw mean rows and matching sequence_sha256, no scaler fitting');p.add_argument('--save-features');a=p.parse_args(argv)
    start=time.perf_counter();folder=Path(a.model_dir);lock=json.loads((folder/'bundle.json').read_text(encoding='utf8'));target=Path(a.out);assert not target.exists(),'Output exists'
    for name,h in lock['files'].items():assert sha(folder/name)==h,name
    records=fasta(a.fasta);hashes=[hashlib.sha256(s.encode()).hexdigest() for _,s in records]
    if a.features:
        z=np.load(a.features,allow_pickle=False);assert z['sequence_sha256'].tolist()==hashes;means=z['mean'];assert means.shape==(len(records),1024) and np.isfinite(means).all()
    else:
        assert a.encoder_dir,'--encoder-dir is required when --features is absent';means=encode(records,a.encoder_dir,lock)
    if a.save_features:
        assert not Path(a.save_features).exists();np.savez_compressed(a.save_features,mean=means,sequence_sha256=np.array(hashes))
    scaler=joblib.load(folder/'scaler.joblib');model=joblib.load(folder/'model.joblib');x=scaler.transform(normalize(means).astype(np.float32)).astype(np.float32);score=model.decision_function(x);threshold=lock['threshold']
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['protein_id','sequence_sha256','decision_score','threshold','predicted_label'],delimiter='\t');w.writeheader();w.writerows(dict(protein_id=n,sequence_sha256=h,decision_score=float(s),threshold=threshold,predicted_label=int(s>=threshold)) for (n,_),h,s in zip(records,hashes,score))
    print(json.dumps(dict(n=len(records),seconds=time.perf_counter()-start,model_role=lock['role'],threshold=threshold,encoder_forward=not bool(a.features),scores_are_probabilities=False)))
if __name__=='__main__':main()
