from pathlib import Path
import csv,json,hashlib,math
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score,confusion_matrix,matthews_corrcoef

# Public adaptation: run/cache locations are explicit environment inputs.
import os
HERE=Path(__file__).resolve().parent
OUT=Path(os.environ['BACROOTFIT_RUN_DIR']).resolve()
FEATURES=Path(os.environ['BACROOTFIT_FEATURES_DIR']).resolve()
DATA=OUT/'database'
ENCODERS=['prott5','ankh','esm','protbert','esmc']
DIMS=dict(prott5=1024,ankh=768,esm=1280,protbert=1024,esmc=1152)
METRICS=['ROC_AUC','AP','MCC','precision','recall','specificity','F1','accuracy','balanced_accuracy','TP','FP','FN','TN']
STUDIES=['Cole2017','Ghaly2025','Ji2023','Knights2024','Minhas2026','Torres2025','Torres2026_YX36']

def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def write(p,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);assert rows,p
    with p.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)),delimiter='\t');w.writeheader();w.writerows(rows)
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.partial')
    q.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8');q.replace(p)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def verify_manifest(folder):
    name='manifest_sha256.tsv' if (folder/'manifest_sha256.tsv').exists() else 'artifacts_sha256.tsv'
    rows=read(folder/name)
    for r in rows:
        p=folder/r['path'];assert p.stat().st_size==int(r['bytes']) and sha(p)==r['sha256'],p
    return len(rows)
def fasta(p):
    from Bio import SeqIO
    return {r.id:str(r.seq) for r in SeqIO.parse(p,'fasta')}

def metrics(y,s,t):
    y=np.asarray(y,int);s=np.asarray(s,np.float64);z=s>=t
    assert set(y)=={0,1} and np.isfinite(s).all()
    tn,fp,fn,tp=confusion_matrix(y,z,labels=[0,1]).ravel();re=tp/(tp+fn);sp=tn/(tn+fp);pr=tp/(tp+fp) if tp+fp else 0.
    return dict(n=len(y),positive=int(y.sum()),negative=int((1-y).sum()),ROC_AUC=float(roc_auc_score(y,s)),AP=float(average_precision_score(y,s)),MCC=float(matthews_corrcoef(y,z)),
        precision=float(pr),recall=float(re),specificity=float(sp),F1=float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else 0.,accuracy=float(np.mean(y==z)),balanced_accuracy=float((re+sp)/2),TP=int(tp),FP=int(fp),FN=int(fn),TN=int(tn))

def optimize_threshold(y,s):
    y=np.asarray(y,int);s=np.asarray(s,np.float64);assert np.isfinite(s).all()
    order=np.argsort(-s,kind='stable');ss=s[order];yy=y[order];ends=np.r_[np.flatnonzero(ss[:-1]!=ss[1:]),len(ss)-1]
    tp=np.r_[0,np.cumsum(yy)[ends]].astype(float);fp=np.r_[0,np.cumsum(1-yy)[ends]].astype(float);fn=y.sum()-tp;tn=(1-y).sum()-fp
    den=np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn));m=np.divide(tp*tn-fp*fn,den,out=np.zeros_like(den),where=den>0)
    boundaries=np.r_[np.nextafter(ss[0],np.inf),ss[ends]];t=float(boundaries[int(np.argmax(m))]);record=metrics(y,s,t)
    assert math.isclose(record['MCC'],m.max(),abs_tol=1e-12)
    return t,record

def registry():
    rows=[]
    for enc in ENCODERS:
        for rep in ['mean','mean_std','residue_attention','dual_attention']:
            if rep in ['mean','mean_std']:
                for c in [.1,1.,10.]:
                    for w in ['none','balanced']:rows.append(dict(id=f'{enc}_{rep}_lr_C{c:g}_{w}',encoder=enc,representation=rep,learner='lr',C=c,weight=w,solver='lbfgs',tol=1e-5,max_iter_attempts=[5000,10000,20000]))
                for c in [.1,1.,10.]:
                    for gamma in [.1,1.]:
                        for w in ['none','balanced']:rows.append(dict(id=f'{enc}_{rep}_svm_C{c:g}_G{gamma:g}_{w}',encoder=enc,representation=rep,learner='svm',C=c,gamma_multiplier=gamma,weight=w,kernel='rbf',tol=.001,max_iter=-1,cache_size=512))
            for h in [64,128]:
                for wd in [.0001,.01]:
                    for w in ['none','balanced']:rows.append(dict(id=f'{enc}_{rep}_mlp_H{h}_WD{wd:g}_{w}',encoder=enc,representation=rep,learner='mlp',widths=[h,32],weight_decay=wd,weight=w,learning_rate=.001,batch_size=128,max_epochs=100,patience=10,dropout=.3,gradient_clip=1.,seed=37))
    assert len(rows)==340 and len({r['id'] for r in rows})==340
    return rows
